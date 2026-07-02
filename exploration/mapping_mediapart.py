"""Construit la liste des URLs d'articles Mediapart, sur toutes les rubriques
qui contiennent des articles individuels (hors "dossiers", qui ne sont que des
pages de collections -- cf discussion). Pagination deterministe, motif d'URL
deja valide -- pas besoin d'agent LLM.

    python -m exploration.mapping_mediapart

Le nombre total de pages par rubrique a ete releve manuellement au prealable
(cf discussion) -- pas de detection automatique ici, pour rester simple.
Ecrit un checkpoint apres chaque rubrique (~4400 pages au total, plusieurs
heures), pour ne rien perdre en cas d'interruption.
"""
import csv
import re
import time

import requests
from tqdm import tqdm

RUBRIQUES = {
    "international": 625,
    "france": 625,
    "politique": 356,
    "economie": 580,
    "ecologie": 224,
    "culture-idees": 457,
    "enquetes": 472,
    "series": 40,
    "fil-dactualites": 1000,
}
SORTIE = "exploration/mediapart_url.csv"
MOTIF = re.compile(r'href="(/journal/[a-z-]+/\d{6}/[a-z0-9-]+)"')

urls = set()


def sauvegarder():
    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(urls):
            w.writerow([u])


for rubrique, total_pages in RUBRIQUES.items():
    print(f"\n=== {rubrique} : {total_pages} pages ===")
    for page in tqdm(range(1, total_pages + 1)):
        try:
            r = requests.get(
                f"https://www.mediapart.fr/journal/{rubrique}",
                params={"page": page},
                headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"},
                timeout=10,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"{rubrique} page {page} : echec ({e}), ignoree")
            continue
        urls.update("https://www.mediapart.fr" + m for m in MOTIF.findall(r.text))
        time.sleep(0.5)  # politesse envers le serveur
    sauvegarder()  # checkpoint apres chaque rubrique
    print(f"{rubrique} termine, {len(urls)} URLs uniques cumulees")

print(f"\nTermine : {len(urls)} URLs uniques ecrites dans {SORTIE}")
