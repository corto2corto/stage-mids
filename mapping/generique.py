"""Moteur de mapping : construit la liste des URLs d'articles d'un media, a
partir de sa fiche dans mapping.catalogue. Cinq methodes de collecte
(IndexSitemap, SitemapPagine, PaginationHtml, ArchivesParJour, CdxWayback) :
la structure propre a chaque media vit dans le catalogue, la plomberie
commune est ici. Seul mapper_liens (agent pour sites sans sitemap) est a part.

Sortie : CSV en append+dedup — les URLs deja presentes sont chargees au
demarrage et JAMAIS reecrites, les nouvelles sont ajoutees au fil de l'eau
(reprise sans perte apres interruption, jamais d'ecrasement). Deux mappings
peuvent nourrir le meme CSV (laprovence pagination + archives CDX : union
naturelle). Consequence sur les rubriques a arret automatique (marianne,
laprovence) : un re-run s'arrete des qu'il retombe sur du connu — c'est le
comportement de rattrapage voulu, les nouveautes etant en tete de pagination.

    python -m mapping.generique <media>

Env :
- MAPPING_LIMITE=N : mode echantillon (smoke test) — N sitemaps / pages /
  jours, 1 rubrique, 3xN pages CDX reparties. Sert a mapping.verifier.
- MAPPING_SORTIE_DIR=dossier : ecrire les CSV ailleurs que exploration/
  (tests : ne jamais toucher aux CSV de prod).
- MAPPING_ANNEES="2025 2026" : restreint ArchivesParJour a ces annees
  (rattrapage cible).
"""
import atexit
import csv
import html
import os
import re
import sys
import time
from datetime import date, timedelta
from urllib.parse import urlencode

import requests
from tqdm import tqdm

from mapping.catalogue import (CATALOGUE, ArchivesParJour, CdxWayback,
                               IndexSitemap, PaginationHtml, SitemapPagine)
from scripts.collecte import lire_urls, recuperer as recuperer_http

MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
SORTIE_DIR = os.environ.get("MAPPING_SORTIE_DIR", "exploration")


def limite():
    return int(os.environ.get("MAPPING_LIMITE", "0"))


# --- Firefox partage (DataDome ne sert certains sitemaps qu'a un vrai navigateur) ---
_DRIVER = None


def _firefox():
    global _DRIVER
    if _DRIVER is None:
        from scraping.navigateur import ouvrir_firefox  # paresseux : selenium serveur seulement
        _DRIVER = ouvrir_firefox()
        _DRIVER.set_page_load_timeout(120)  # les reponses DataDome sont parfois tres lentes
        atexit.register(_DRIVER.quit)
    return _DRIVER


def recuperer(url, fiche, params=None, attente=2, timeout=60):
    """Texte d'une URL selon le transport de la fiche (requests / curl /
    curl_cffi / Firefox), .gz decompresse ; None si echec."""
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"
    if getattr(fiche, "via_firefox", False):
        from scraping.navigateur import scraper  # paresseux
        try:
            return scraper(_firefox(), url, attente=attente)
        except Exception as e:
            print(f"{url} : echec firefox ({type(e).__name__})")
            return None
    return recuperer_http(url, ua=fiche.ua, via_curl=getattr(fiche, "via_curl", False),
                          via_cffi=getattr(fiche, "via_cffi", False), timeout=timeout)


def garder(urls, fiche):
    """Applique nettoyage / filtre / anti_filtre de la fiche a une liste d'URLs."""
    if getattr(fiche, "unescape", False):
        urls = [html.unescape(u) for u in urls]
    if getattr(fiche, "nettoyer", False):  # liseuse, trackers : ?query et #fragment
        urls = [u.split("?")[0].split("#")[0] for u in urls]
    if fiche.filtre:
        f = re.compile(fiche.filtre)
        urls = [u for u in urls if f.search(u)]
    anti = getattr(fiche, "anti_filtre", None)
    if anti:
        a = re.compile(anti)
        urls = [u for u in urls if not a.search(u)]
    return urls


class Sortie:
    """CSV d'URLs en append+dedup : les URLs deja presentes sont chargees au
    demarrage et jamais reecrites ; les nouvelles sont ajoutees au fil de
    l'eau (flush) — reprise sans perte apres interruption, jamais
    d'ecrasement. ajouter() renvoie le nombre d'URLs reellement nouvelles."""

    def __init__(self, chemin):
        self.chemin = chemin
        self.deja = set()
        existe = os.path.exists(chemin)
        if existe:
            self.deja = lire_urls(chemin)
            print(f"{len(self.deja)} URLs deja presentes dans {chemin}")
            with open(chemin, "rb+") as f:  # clore une derniere ligne sans saut (crash passe)
                f.seek(0, 2)
                if f.tell():
                    f.seek(-1, 2)
                    if f.read(1) != b"\n":
                        f.write(b"\r\n")
        self.f = open(chemin, "a", newline="", encoding="utf-8")
        self.w = csv.writer(self.f)
        if not existe:
            self.w.writerow(["url"])
        self.ajoutees = 0

    def ajouter(self, urls):
        nouvelles = sorted(set(urls) - self.deja)
        for u in nouvelles:
            self.w.writerow([u])
        if nouvelles:
            self.f.flush()
            self.deja.update(nouvelles)
            self.ajoutees += len(nouvelles)
        return len(nouvelles)

    def fermer(self):
        self.f.close()
        print(f"{self.ajoutees} URLs ajoutees ({len(self.deja)} au total) dans {self.chemin}")


# --- collecteur : index -> sous-sitemaps -> <loc> ---
def collecter_index_sitemap(fiche, sortie):
    index = fiche.index if isinstance(fiche.index, list) else [fiche.index]
    motif_sm = re.compile(fiche.motif_sous_sitemap)
    sous = set()
    for idx in index:
        texte = None
        for tentative in range(3):  # un echec ici condamnerait tout le mapping
            texte = recuperer(idx, fiche, attente=3)
            if texte and motif_sm.search(texte):
                break
            print(f"index tentative {tentative + 1} : vide ou inaccessible")
        if not texte or not motif_sm.search(texte):
            raise SystemExit(f"index inaccessible : {idx}")
        if fiche.unescape:
            texte = html.unescape(texte)
        sous.update(fiche.prefixe_sous_sitemap + m for m in motif_sm.findall(texte))
    sous = sorted(sous)
    n = limite()
    if n:
        sous = sous[-n:]
    print(f"{len(sous)} sous-sitemaps a parcourir")

    for sm in tqdm(sous):
        texte = recuperer(sm, fiche)
        if texte is None:
            print(f"{sm} : echec, ignore")
            continue
        sortie.ajouter(garder(MOTIF_LOC.findall(texte), fiche))
        time.sleep(fiche.pause)


# --- collecteur : un sitemap pagine par un parametre numerique ---
def collecter_sitemap_pagine(fiche, sortie):
    n = limite()

    # pagination 1..max avec arret automatique (cnews)
    if fiche.max_pages:
        vides = 0
        for page in tqdm(range(1, (n or fiche.max_pages) + 1)):
            texte = recuperer(fiche.base, fiche, params={**fiche.params_fixes, fiche.param: page})
            locs = MOTIF_LOC.findall(texte) if texte else []
            if not locs:
                vides += 1
                print(f"{fiche.param}={page} : vide ou echec")
                if vides >= fiche.arret_apres:
                    print(f"arret a la page {page} apres {vides} pages vides/echecs consecutifs")
                    break
                time.sleep(fiche.pause)
                continue
            vides = 0
            sortie.ajouter(garder(locs, fiche))
            time.sleep(fiche.pause)
        return

    # plage lue dans le sitemap (francesoir) ou explicite (liberation)
    if fiche.pages is not None:
        pages = list(fiche.pages)
    else:
        texte = recuperer(fiche.base, fiche)
        if texte is None:
            raise SystemExit(f"sitemap inaccessible : {fiche.base}")
        pages = sorted(int(p) for p in set(re.findall(fiche.motif_pages, texte)))
    if n:
        pages = pages[:n]
    print(f"{len(pages)} pages de sitemap a parcourir")

    for page in tqdm(pages):
        texte = recuperer(fiche.base, fiche, params={**fiche.params_fixes, fiche.param: page})
        if texte is None:
            print(f"{fiche.param}={page} : echec, ignore")
            continue
        sortie.ajouter(garder(MOTIF_LOC.findall(texte), fiche))
        time.sleep(fiche.pause)


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
        for d in tqdm(jours):
            url = fiche.url_jour.format(annee=d.year, jjmmaaaa=d.strftime("%d-%m-%Y"))
            texte = recuperer(url, fiche)
            if texte is None:
                print(f"{url} : echec, ignore")
                continue
            sortie.ajouter(liens(texte, motif))
            time.sleep(fiche.pause)
        return

    # pagination unique (blast)
    if fiche.total_pages:
        motif = re.compile(fiche.motif)
        for page in tqdm(range(1, (n or fiche.total_pages) + 1)):
            texte = recuperer(fiche.base, fiche, params={fiche.param: page})
            if texte is None:
                print(f"page {page} : echec, ignore")
                continue
            sortie.ajouter(liens(texte, motif))
            time.sleep(fiche.pause)
        return

    # par rubrique : liste fixe, nb de pages connu (mediapart), ou lue dans un
    # sitemap (laprovence) ; arret auto apres 2 pages sans nouveaute
    sections = fiche.sections
    if fiche.sections_depuis:
        texte = recuperer(fiche.sections_depuis, fiche)
        if texte is None:
            raise SystemExit(f"liste des rubriques inaccessible : {fiche.sections_depuis}")
        sections = sorted(set(re.findall(fiche.motif_sections, texte)))
    if n and isinstance(sections, list):
        sections = sections[:1]  # smoke : 1 rubrique
    for section in sections:
        base = fiche.base.format(section=section)
        # .format seulement si le motif attend la section (marianne) : les
        # quantificateurs regex {6} {25,} seraient pris pour des placeholders
        motif = re.compile(fiche.motif.format(section=section)
                           if "{section}" in fiche.motif else fiche.motif)
        if isinstance(sections, dict):  # nb de pages fixe
            plage = range(1, (n or sections[section]) + 1)
        else:  # arret auto
            plage = range(1, (n or fiche.max_pages) + 1)
        print(f"\n=== {section} ===")
        sans_nouveaute = 0
        echecs = 0
        for page in tqdm(plage):
            if fiche.route_page:  # pagination par route ; page 1 = base nue
                cible = base + (fiche.route_page.format(page=page) if page > 1 else "")
                texte = recuperer(cible, fiche)
            else:
                texte = recuperer(base, fiche, params={fiche.param: page})
            if texte is None:
                print(f"{section} p={page} : echec, ignore")
                echecs += 1
                if echecs >= fiche.arret_echecs:
                    # sections_depuis liste aussi des rubriques disparues (404
                    # systematique) : inutile d'epuiser le garde-fou dessus
                    print(f"{section} : abandon apres {echecs} echecs consecutifs (rubrique morte ?)")
                    break
                time.sleep(fiche.pause)
                continue
            echecs = 0
            nouvelles = sortie.ajouter(liens(texte, motif))
            if isinstance(sections, list):  # arret auto
                if nouvelles == 0:
                    sans_nouveaute += 1
                    if sans_nouveaute >= 2:
                        print(f"{section} : fin de pagination a p={page}")
                        break
                else:
                    sans_nouveaute = 0
            time.sleep(fiche.pause)
        print(f"{section} termine, {sortie.ajoutees} URLs ajoutees cumulees")


# --- collecteur : pages d'archives datees, une par jour (20minutes, leprogres) ---
def collecter_archives_par_jour(fiche, sortie):
    annees_env = os.environ.get("MAPPING_ANNEES", "").split()
    annees = [int(a) for a in annees_env] or list(range(fiche.annee_debut, date.today().year + 1))
    n = limite()
    if n:
        annees = annees[-1:]  # smoke : derniere annee, n jours
    motif_jour = re.compile(fiche.motif_jour)
    motif_article = re.compile(fiche.motif_article)

    for annee in annees:
        texte = recuperer(fiche.url_annee.format(annee=annee), fiche)
        if texte is None:
            print(f"annee {annee} : page annuelle inaccessible, ignoree")
            continue
        jours = sorted(set(t for t in motif_jour.findall(texte) if t[0] == str(annee)))
        if n:
            jours = jours[:n]
        print(f"{annee} : {len(jours)} jours a parcourir")
        time.sleep(fiche.pause)
        for a, g2, g3 in tqdm(jours, desc=str(annee)):
            texte = recuperer(fiche.url_jour.format(annee=a, g2=g2, g3=g3), fiche)
            if texte is None:  # jour depublie (404/410) ou echec : tant pis pour ce jour
                time.sleep(fiche.pause)
                continue
            if fiche.filtre_date_slug:  # motif a 2 groupes : (url, date compacte du slug)
                trouves = [u for u, d in motif_article.findall(texte) if d == a + g2 + g3]
            else:
                trouves = motif_article.findall(texte)
            sortie.ajouter(fiche.prefixe + t for t in trouves)
            time.sleep(fiche.pause)


# --- collecteur : captures archivees du domaine via l'API CDX de la Wayback Machine ---
def collecter_cdx_wayback(fiche, sortie):
    cdx = "http://web.archive.org/cdx/search/cdx"
    entetes = {"User-Agent": fiche.ua}
    commun = {"url": fiche.domaine, "matchType": "host", "pageSize": "5"}
    r = requests.get(cdx, params={**commun, "showNumPages": "true"}, headers=entetes, timeout=60)
    r.raise_for_status()
    nb_pages = int(r.text.strip())
    pages = list(range(nb_pages))
    n = limite()
    if n:
        # 3x limite sondes reparties : l'index est clairseme apres filtres (zones creuses)
        pages = pages[::max(1, nb_pages // (3 * n))][:3 * n]
    print(f"{nb_pages} pages d'index CDX a parcourir")

    motif = re.compile(fiche.motif_article)
    for page in tqdm(pages):
        texte = ""
        for tentative in range(3):
            try:
                r = requests.get(cdx, params={**commun, "page": page, "fl": "original",
                                              "filter": ["statuscode:200", "mimetype:text/html"],
                                              "collapse": "urlkey", **fiche.periode},
                                 headers=entetes, timeout=180)
                r.raise_for_status()
                texte = r.text
                if texte.strip() or tentative == 2:
                    break  # page reellement vide apres 3 essais : zone creuse de l'index
                print(f"page {page} tentative {tentative + 1} : reponse vide, on reessaie")
            except requests.RequestException as e:
                print(f"page {page} tentative {tentative + 1} : echec ({e})")
            time.sleep(10 * (tentative + 1))  # l'API CDX throttle par moments
        urls = []
        for brute in texte.splitlines():
            u = brute.split("?")[0].split("#")[0].replace("http://", "https://").replace(":80/", "/")
            if motif.match(u):
                urls.append(u)
        sortie.ajouter(urls)
        time.sleep(fiche.pause)


COLLECTEURS = {
    IndexSitemap: collecter_index_sitemap,
    SitemapPagine: collecter_sitemap_pagine,
    PaginationHtml: collecter_pagination_html,
    ArchivesParJour: collecter_archives_par_jour,
    CdxWayback: collecter_cdx_wayback,
}


if __name__ == "__main__":  # module aussi importe par mapping.verifier
    if len(sys.argv) != 2 or sys.argv[1] not in CATALOGUE:
        print(f"usage : python -m mapping.generique <media>\nmedias : {', '.join(sorted(CATALOGUE))}")
        sys.exit(2)

    media = sys.argv[1]
    fiche = CATALOGUE[media]
    os.makedirs(SORTIE_DIR, exist_ok=True)
    sortie = Sortie(os.path.join(SORTIE_DIR, getattr(fiche, "sortie", None) or f"{media}_url.csv"))
    try:
        COLLECTEURS[type(fiche)](fiche, sortie)
    finally:
        sortie.fermer()
