"""Construit la liste des URLs d'articles d'un media, a partir de sa fiche
dans exploration.medias. Remplace les anciens scripts mapping_<media>.py :
la structure propre a chaque media vit dans le catalogue, la plomberie commune
(requetes, ecriture CSV, checkpoints, MAPPING_LIMITE) est ici.

    python -m exploration.mapping gala
    python -m exploration.mapping bfmtv

MAPPING_LIMITE=N (env) : mode echantillon (smoke test) -- ne parcourt que N
sitemaps / pages / jours, ou 1 rubrique et N pages pour les medias par
rubrique, ou 3xN sondes reparties sur l'index pour les mappings CDX. Sert
aussi a exploration.verifier_mappings.
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

from exploration.medias import (
    CATALOGUE, ArchivesCDX, IndexSitemap, SitemapPagine, PaginationHtml,
)

MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
PAUSE = 0.5  # politesse envers le serveur
CDX = "http://web.archive.org/cdx/search/cdx"


def limite():
    return int(os.environ.get("MAPPING_LIMITE", "0"))


def ecrire(sortie, urls):
    with open(sortie, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(urls):
            w.writerow([u])


def lire_existant(sortie):
    """URLs deja presentes dans le CSV (mappings d'archives qui completent un
    mapping sitemap deja fait). Set vide si le fichier n'existe pas."""
    if not os.path.exists(sortie):
        return set()
    with open(sortie, newline="", encoding="utf-8") as f:
        urls = {l[0] for l in list(csv.reader(f))[1:] if l}
    print(f"{len(urls)} URLs deja presentes dans {sortie}")
    return urls


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
    vides = 0
    for page in tqdm(pages):
        params = {**fiche.params_fixes, fiche.param: page}
        texte = recuperer(fiche.base, fiche.ua, params=params)
        locs = MOTIF_LOC.findall(texte) if texte is not None else []
        if not locs:
            # plage large en garde-fou (cnews) : on s'arrete des que le sitemap
            # ne rend plus rien, sans epuiser les centaines de pages restantes
            vides += 1
            print(f"{fiche.param}={page} : {'echec' if texte is None else 'vide'}")
            if fiche.arret_pages_vides and vides >= fiche.arret_pages_vides:
                print(f"arret a {fiche.param}={page} apres {vides} pages vides consecutives")
                break
            time.sleep(fiche.pause)
            continue
        vides = 0
        urls.update(garder(locs, fiche))
        time.sleep(fiche.pause)
    return urls


# --- collecteur : index des captures de la Wayback Machine ---
def collecter_archives_cdx(fiche, sortie):
    params_communs = {"url": fiche.domaine, "matchType": "host", "pageSize": "5"}
    entetes = {"User-Agent": fiche.ua}

    r = requests.get(CDX, params={**params_communs, "showNumPages": "true"},
                     headers=entetes, timeout=60)
    r.raise_for_status()
    nb_pages = int(r.text.strip())
    pages = list(range(nb_pages))
    n = limite()
    if n:
        # 3x limite sondes reparties : l'index est clairseme apres filtres
        # (zones creuses sans aucun article conforme)
        pages = pages[::max(1, nb_pages // (3 * n))][:3 * n]
    print(f"{nb_pages} pages d'index CDX a parcourir")

    motif = re.compile(fiche.motif_article)
    urls = lire_existant(sortie) if fiche.fusionner else set()
    for i, page in enumerate(tqdm(pages), 1):
        texte = ""
        for tentative in range(3):
            try:
                r = requests.get(CDX, params={**params_communs, "page": page,
                                              "fl": "original", "collapse": "urlkey",
                                              "filter": ["statuscode:200", "mimetype:text/html"],
                                              **fiche.periode},
                                 headers=entetes, timeout=180)
                r.raise_for_status()
                texte = r.text
                if texte.strip() or tentative == 2:
                    break  # page reellement vide apres 3 essais : zone creuse
                print(f"page {page} tentative {tentative + 1} : reponse vide, on reessaie")
            except requests.RequestException as e:
                print(f"page {page} tentative {tentative + 1} : echec ({e})")
            time.sleep(10 * (tentative + 1))  # l'API CDX throttle par moments
        for brute in texte.splitlines():
            u = brute.split("?")[0].split("#")[0].replace("http://", "https://").replace(":80/", "/")
            if motif.match(u):
                urls.add(u)
        if i % 50 == 0:  # checkpoint
            ecrire(sortie, urls)
        time.sleep(1)  # politesse envers l'API
    return urls


# --- collecteur : pages liste HTML -> liens d'articles ---
def collecter_pagination_html(fiche, sortie):
    n = limite()

    def liens(texte, motif):
        return {fiche.prefixe + m for m in motif.findall(texte)}

    # archives annuelles : page-annee -> pages-jour (20minutes, leprogres)
    if fiche.annees:
        debut, fin = fiche.annees
        annees = range(debut, fin + 1)
        motif_annee = re.compile(fiche.motif_annee)
        motif = re.compile(fiche.motif)
        urls = set()
        for annee in annees:
            texte = recuperer(fiche.url_annee.format(annee=annee), fiche.ua)
            if texte is None:
                print(f"archives/{annee} : echec, annee ignoree")
                continue
            # la page annuelle liste les jours ; l'ordre des 2 derniers groupes
            # depend du media (/MM-DD chez 20minutes, /JJ-MM chez leprogres)
            jours = sorted({t for t in motif_annee.findall(texte) if t[0] == str(annee)})
            if n:
                jours = jours[:n]
            print(f"{annee} : {len(jours)} jours a parcourir")
            time.sleep(fiche.pause)

            for a, x, y in tqdm(jours, desc=str(annee)):
                mm, jj = (x, y) if fiche.ordre_jour == "mj" else (y, x)
                texte = recuperer(fiche.url_jour.format(annee=a, mm=mm, jj=jj), fiche.ua)
                if texte is None:
                    time.sleep(fiche.pause)
                    continue  # page depubliee (410/404) ou echec : tant pis
                if fiche.filtre_jour:
                    # les pages-jour melangent des encarts "plus lus" d'autres
                    # dates : on ne garde que les slugs portant la date du jour
                    urls.update(u for u, d in motif.findall(texte) if d == f"{a}{mm}{jj}")
                else:
                    urls.update(liens(texte, motif))
                time.sleep(fiche.pause)
            ecrire(sortie, urls)  # checkpoint apres chaque annee
            print(f"{annee} termine, {len(urls)} URLs uniques cumulees")
        return urls

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

    # par rubrique : nb de pages connu (mediapart) ou arret auto (marianne),
    # rubriques codees en dur ou lues dans un sitemap (laprovence)
    sections = fiche.sections
    if fiche.sections_sitemap:
        texte = recuperer(fiche.sections_sitemap, fiche.ua)
        if texte is None:
            raise SystemExit(f"sitemap des rubriques inaccessible : {fiche.sections_sitemap}")
        sections = sorted(set(re.findall(fiche.motif_sections, texte)))
        print(f"{len(sections)} rubriques a paginer")
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
        echecs = 0
        for page in tqdm(plage):
            if fiche.gabarit_page:  # pagination par segment d'URL, page 1 = URL nue
                cible, params = base + (fiche.gabarit_page.format(page=page) if page > 1 else ""), None
            else:
                cible, params = base, {fiche.param: page}
            texte = recuperer(cible, fiche.ua, params=params)
            if texte is None:
                print(f"{section} p={page} : echec, ignore")
                echecs += 1
                if echecs >= 3:
                    # un sitemap de rubriques liste aussi des rubriques
                    # disparues (404 systematique) : inutile d'epuiser le
                    # garde-fou dessus
                    print(f"{section} : abandon apres 3 echecs consecutifs (rubrique morte ?)")
                    break
                time.sleep(fiche.pause)
                continue
            echecs = 0
            avant = len(urls)
            urls.update(liens(texte, motif))
            if not isinstance(sections, dict):  # arret auto
                if len(urls) == avant:
                    sans_nouveaute += 1
                    if sans_nouveaute >= 2:
                        print(f"{section} : fin de pagination a p={page}")
                        break
                else:
                    sans_nouveaute = 0
            time.sleep(fiche.pause)
        ecrire(sortie, urls)  # checkpoint apres chaque rubrique
        print(f"{section} termine, {len(urls)} URLs uniques cumulees")
    return urls


COLLECTEURS = {
    IndexSitemap: collecter_index_sitemap,
    SitemapPagine: collecter_sitemap_pagine,
    PaginationHtml: collecter_pagination_html,
    ArchivesCDX: collecter_archives_cdx,
}


if len(sys.argv) != 2 or sys.argv[1] not in CATALOGUE:
    print(f"usage : python -m exploration.mapping <media>\nmedias : {', '.join(CATALOGUE)}")
    sys.exit(2)

media = sys.argv[1]
fiche = CATALOGUE[media]
# les mappings d'archives ecrivent dans le CSV du media qu'ils completent
sortie = getattr(fiche, "sortie", None) or f"exploration/{media}_url.csv"
urls = COLLECTEURS[type(fiche)](fiche, sortie)
ecrire(sortie, urls)
print(f"{len(urls)} URLs ecrites dans {sortie}")
