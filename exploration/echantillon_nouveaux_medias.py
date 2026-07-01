"""Télécharge le HTML d'articles des nouveaux médias (pas encore dans MEDIAS),
pour inspecter leur structure et écrire leurs méthodes d'extraction.

Pour chaque <media>_url.csv sans entrée dans le registre MEDIAS, prend
3 URLs réparties dans le fichier (25 %, 50 %, 75 %) — les sitemaps étant
grossièrement chronologiques, ça varie les époques et augmente la chance
d'avoir du payant ET du gratuit. Le HTML est sauvé dans exploration/.

Lecture seule sur les CSV : pas besoin d'arrêter le pipeline.

À lancer SUR LE SERVEUR :

    python -m exploration.echantillon_nouveaux_medias
"""

import csv

from scraping.medias import MEDIAS
from scraping.navigateur import RACINE, configurer_ublock, ouvrir_firefox, scraper
from scraping.stockage import DATA_DIR

SORTIE = RACINE / "exploration"

# Sélection : pour chaque CSV d'un média absent du registre, 3 URLs réparties.
cibles = {}
for chemin in sorted((DATA_DIR/"urls").glob("*_url.csv")):
    media = chemin.stem.removesuffix("_url")
    if media in MEDIAS:
        continue
    with open(chemin, newline="", encoding="utf-8") as f:
        urls = [ligne["url"] for ligne in csv.DictReader(f)]
    if not urls:
        print(f"{media} : CSV vide, ignoré")
        continue
    for i, position in enumerate((0.25, 0.50, 0.75), start=1):
        cibles[f"{media}_{i}"] = urls[int(len(urls) * position)]

print(f"{len(cibles)} pages à récupérer\n")

configurer_ublock()
driver = ouvrir_firefox()
try:
    for nom, url in cibles.items():
        try:
            html = scraper(driver, url)
        except Exception as e:
            print(f"{nom:30} ECHEC  {e.__class__.__name__}: {e}")
            continue
        chemin = SORTIE / f"{nom}.html"
        chemin.write_text(html, encoding="utf-8")
        print(f"{nom:30} {len(html):>8} chars  {url}")
finally:
    driver.quit()
