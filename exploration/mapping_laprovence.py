"""Construit la liste des URLs d'articles La Provence par pagination des
rubriques (listees dans sitemap_categories.xml) avec les routes /page-N,
rendues cote serveur (repere lors de la reco : ?page= et /page/N sont
ignores, /page-N pagine vraiment ; ~48 liens /article/ par page). Arret
d'une rubrique apres 2 pages consecutives sans nouvelle URL, garde-fou a
3000 pages (france-monde annonce ~84k articles soit ~2100 pages).

    python -m exploration.mapping_laprovence

MAPPING_LIMITE=N (env) : 1 rubrique et N pages max (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

CATEGORIES_XML = "https://www.laprovence.com/sitemap_categories.xml"
SORTIE = "exploration/laprovence_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
MAX_PAGES = 3000  # garde-fou anti-boucle infinie
MOTIF_CATEGORIE = re.compile(r"<loc>https://www\.laprovence\.com(/[a-z0-9-]+)</loc>")
MOTIF_ARTICLE = re.compile(r'href="(?:https://www\.laprovence\.com)?(/article/[^"#?]+)"')

r = requests.get(CATEGORIES_XML, headers=ENTETES, timeout=30)
r.raise_for_status()
categories = sorted(set(MOTIF_CATEGORIE.findall(r.text)))
max_pages = MAX_PAGES
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    categories = categories[:1]
    max_pages = limite
print(f"{len(categories)} rubriques a paginer")

urls = set()
for categorie in categories:
    pages_sans_nouveaute = 0
    print(f"\n=== {categorie} ===")
    for page in tqdm(range(1, max_pages + 1)):
        cible = f"https://www.laprovence.com{categorie}" + (f"/page-{page}" if page > 1 else "")
        try:
            r = requests.get(cible, headers=ENTETES, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"{cible} : echec ({e}), ignoree")
            continue
        avant = len(urls)
        urls.update("https://www.laprovence.com" + m for m in MOTIF_ARTICLE.findall(r.text))
        if len(urls) == avant:
            pages_sans_nouveaute += 1
            if pages_sans_nouveaute >= 2:
                print(f"{categorie} : fin de pagination a page-{page}")
                break
        else:
            pages_sans_nouveaute = 0
        time.sleep(0.4)  # politesse envers le serveur
    # checkpoint apres chaque rubrique
    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(urls):
            w.writerow([u])
    print(f"{categorie} termine, {len(urls)} URLs uniques cumulees")

print(f"\nTermine : {len(urls)} URLs ecrites dans {SORTIE}")
