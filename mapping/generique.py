"""Construit la liste des URLs d'articles d'un media, a partir de sa fiche
dans mapping.catalogue. Couvre les cas standard (sitemaps, pagination) :
la structure propre a chaque media vit dans le catalogue, la plomberie commune
(requetes, ecriture CSV, checkpoints, MAPPING_LIMITE) est ici. Les medias
irreductibles (CDX Wayback, Selenium, archives par jour...) gardent leur
script dedie dans mapping/.

    python -m mapping.generique gala
    python -m mapping.generique bfmtv

MAPPING_LIMITE=N (env) : mode echantillon (smoke test) -- ne parcourt que N
sitemaps / pages / jours, ou 1 rubrique et N pages pour les medias par
rubrique. Sert aussi a mapping.verifier.
"""
import csv
import gzip
import html
import os
import re
import subprocess
import sys
import time
from datetime import date, timedelta

import requests
from tqdm import tqdm

from mapping.catalogue import CATALOGUE, IndexSitemap, SitemapPagine, PaginationHtml

MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
PAUSE = 0.5  # politesse envers le serveur


def limite():
    return int(os.environ.get("MAPPING_LIMITE", "0"))


def ecrire(sortie, urls):
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(urls):
            w.writerow([u])


def recuperer(url, ua, via_curl=False, gzip_attendu=False, params=None):
    """Renvoie le texte d'une URL, via requests ou curl. Repli texte si le
    contenu annonce gzip mais ne l'est pas (certains serveurs le decompressent
    deja). Renvoie None en cas d'echec."""
    if via_curl:
        cmd = [
            "curl", "-s", "-m", "90", "--compressed", "-A", ua,
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: fr-FR,fr;q=0.9",
        ]
        p = subprocess.run(cmd + [url], capture_output=True, text=True, timeout=120)
        if p.returncode != 0 or "Access Denied" in p.stdout[:500]:
            return None
        return p.stdout
    try:
        r = requests.get(url, params=params, headers={"User-Agent": ua}, timeout=60)
        r.raise_for_status()
    except requests.RequestException:
        return None
    if gzip_attendu:
        try:
            return gzip.decompress(r.content).decode("utf-8", errors="replace")
        except (gzip.BadGzipFile, OSError):
            return r.text  # le serveur a deja servi le contenu decompresse
    return r.text


def garder(urls, fiche):
    """Applique filtre / anti_filtre de la fiche a une liste d'URLs."""
    if getattr(fiche, "unescape", False):
        urls = [html.unescape(u) for u in urls]
    if fiche.filtre:
        f = re.compile(fiche.filtre)
        urls = [u for u in urls if f.search(u)]
    anti = getattr(fiche, "anti_filtre", None)
    if anti:
        a = re.compile(anti)
        urls = [u for u in urls if not a.search(u)]
    return urls


# --- collecteur : index -> sous-sitemaps -> <loc> ---
def collecter_index_sitemap(fiche, sortie):
    index = fiche.index if isinstance(fiche.index, list) else [fiche.index]
    motif_sm = re.compile(fiche.motif_sous_sitemap)
    sous = set()
    for idx in index:
        texte = recuperer(idx, fiche.ua, via_curl=fiche.via_curl)
        if texte is None or "<loc>" not in texte:
            raise SystemExit(f"index inaccessible : {idx}")
        if fiche.unescape:
            texte = html.unescape(texte)
        sous.update(motif_sm.findall(texte))
    sous = sorted(sous)
    n = limite()
    if n:
        sous = sous[-n:]
    print(f"{len(sous)} sous-sitemaps a parcourir")

    urls = set()
    for i, sm in enumerate(tqdm(sous), 1):
        texte = recuperer(sm, fiche.ua, via_curl=fiche.via_curl, gzip_attendu=fiche.gzip)
        if texte is None:
            print(f"{sm} : echec, ignore")
            continue
        urls.update(garder(MOTIF_LOC.findall(texte), fiche))
        if i % 50 == 0:  # checkpoint
            ecrire(sortie, urls)
        time.sleep(PAUSE)
    return urls


# --- collecteur : un sitemap pagine par un parametre numerique ---
def collecter_sitemap_pagine(fiche, sortie):
    if fiche.pages is not None:
        pages = list(fiche.pages)
    else:
        texte = recuperer(fiche.base, fiche.ua)
        if texte is None:
            raise SystemExit(f"sitemap inaccessible : {fiche.base}")
        pages = sorted(int(p) for p in set(re.findall(fiche.motif_pages, texte)))
    n = limite()
    if n:
        pages = pages[:n]
    print(f"{len(pages)} pages de sitemap a parcourir")

    urls = set()
    for page in tqdm(pages):
        params = {**fiche.params_fixes, fiche.param: page}
        texte = recuperer(fiche.base, fiche.ua, params=params)
        if texte is None:
            print(f"{fiche.param}={page} : echec, ignore")
            continue
        urls.update(garder(MOTIF_LOC.findall(texte), fiche))
        time.sleep(PAUSE)
    return urls


# --- collecteur : pages liste HTML -> liens d'articles ---
def collecter_pagination_html(fiche, sortie):
    n = limite()

    def liens(texte, motif):
        return {fiche.prefixe + m for m in motif.findall(texte)}

    # archives par jour (leparisien)
    if fiche.date_debut:
        debut = date(*fiche.date_debut)
        jours, d = [], debut
        while d <= date.today():
            jours.append(d)
            d += timedelta(days=1)
        if n:
            jours = jours[-n:]
        print(f"{len(jours)} pages jour a parcourir")
        motif = re.compile(fiche.motif)
        urls = set()
        for i, d in enumerate(tqdm(jours), 1):
            url = fiche.url_jour.format(annee=d.year, jjmmaaaa=d.strftime("%d-%m-%Y"))
            texte = recuperer(url, fiche.ua)
            if texte is None:
                print(f"{url} : echec, ignore")
                continue
            urls.update(liens(texte, motif))
            if i % 200 == 0:  # checkpoint
                ecrire(sortie, urls)
            time.sleep(PAUSE)
        return urls

    # pagination unique (blast)
    if fiche.total_pages:
        pages = range(1, (n or fiche.total_pages) + 1)
        motif = re.compile(fiche.motif)
        urls = set()
        for page in tqdm(pages):
            texte = recuperer(fiche.base, fiche.ua, params={fiche.param: page})
            if texte is None:
                print(f"page {page} : echec, ignore")
                continue
            urls.update(liens(texte, motif))
            time.sleep(PAUSE)
        return urls

    # par rubrique : nb de pages connu (mediapart) ou arret auto (marianne)
    sections = fiche.sections
    if n and isinstance(sections, list):
        sections = sections[:1]  # smoke : 1 rubrique
    urls = set()
    for section in sections:
        base = fiche.base.format(section=section)
        motif = re.compile(fiche.motif.format(section=section))
        if isinstance(sections, dict):  # nb de pages fixe
            total = sections[section]
            plage = range(1, (n or total) + 1)
        else:  # arret auto apres 2 pages sans nouveaute
            plage = range(1, (n or fiche.max_pages) + 1)
        print(f"\n=== {section} ===")
        sans_nouveaute = 0
        for page in tqdm(plage):
            texte = recuperer(base, fiche.ua, params={fiche.param: page})
            if texte is None:
                print(f"{section} p={page} : echec, ignore")
                continue
            avant = len(urls)
            urls.update(liens(texte, motif))
            if isinstance(sections, list):  # arret auto
                if len(urls) == avant:
                    sans_nouveaute += 1
                    if sans_nouveaute >= 2:
                        print(f"{section} : fin de pagination a p={page}")
                        break
                else:
                    sans_nouveaute = 0
            time.sleep(PAUSE)
        ecrire(sortie, urls)  # checkpoint apres chaque rubrique
        print(f"{section} termine, {len(urls)} URLs uniques cumulees")
    return urls


COLLECTEURS = {
    IndexSitemap: collecter_index_sitemap,
    SitemapPagine: collecter_sitemap_pagine,
    PaginationHtml: collecter_pagination_html,
}


if len(sys.argv) != 2 or sys.argv[1] not in CATALOGUE:
    print(f"usage : python -m mapping.generique <media>\nmedias : {', '.join(CATALOGUE)}")
    sys.exit(2)

media = sys.argv[1]
fiche = CATALOGUE[media]
sortie = f"exploration/{media}_url.csv"
urls = COLLECTEURS[type(fiche)](fiche, sortie)
ecrire(sortie, urls)
print(f"{len(urls)} URLs ecrites dans {sortie}")
