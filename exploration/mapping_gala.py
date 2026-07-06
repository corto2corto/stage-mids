"""Construit la liste des URLs d'articles Gala via l'index de sitemaps
mensuels sitemaps/articles.xml (couvre 2007 -> aujourd'hui, ~230 fichiers,
structure reperee lors de la reco -- cf discussion).

    python -m exploration.mapping_gala

MAPPING_LIMITE=N (env) : ne parcourt que N sitemaps (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

INDEX = "https://www.gala.fr/sitemaps/articles.xml"
SORTIE = "exploration/gala_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}
MOTIF_SOUS_SITEMAP = re.compile(r"<loc>(https://www\.gala\.fr/sitemaps/articles/\d{4}-\d{2}\.xml)</loc>")
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")

r = requests.get(INDEX, headers=ENTETES, timeout=30)
r.raise_for_status()
sous_sitemaps = sorted(set(MOTIF_SOUS_SITEMAP.findall(r.text)))
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    sous_sitemaps = sous_sitemaps[-limite:]
print(f"{len(sous_sitemaps)} sitemaps mensuels a parcourir")

urls = set()
for i, sm in enumerate(tqdm(sous_sitemaps), 1):
    try:
        r = requests.get(sm, headers=ENTETES, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"{sm} : echec ({e}), ignore")
        continue
    urls.update(MOTIF_LOC.findall(r.text))
    if i % 50 == 0:  # checkpoint
        with open(SORTIE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["url"])
            for u in sorted(urls):
                w.writerow([u])
    time.sleep(0.5)  # politesse envers le serveur

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
