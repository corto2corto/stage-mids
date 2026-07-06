"""Construit la liste des URLs d'articles France-Soir via le sitemap Drupal
pagine sitemap.xml?page=1..N (N lu dans l'index, ~33 pages). Le sitemap
melange articles et pages statiques : on ne garde que les URLs a deux
segments (/rubrique/slug). Structure reperee lors de la reco -- cf discussion.

    python -m exploration.mapping_francesoir

MAPPING_LIMITE=N (env) : ne parcourt que N pages (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

BASE = "https://www.francesoir.fr/sitemap.xml"
SORTIE = "exploration/francesoir_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
MOTIF_ARTICLE = re.compile(r"https://www\.francesoir\.fr/[a-z0-9_-]+/[^/<\s]+$")

r = requests.get(BASE, headers=ENTETES, timeout=30)
r.raise_for_status()
pages = sorted(int(p) for p in set(re.findall(r"sitemap\.xml\?page=(\d+)", r.text)))
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    pages = pages[:limite]
print(f"{len(pages)} pages de sitemap a parcourir")

urls = set()
for page in tqdm(pages):
    try:
        r = requests.get(BASE, params={"page": page}, headers=ENTETES, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"page {page} : echec ({e}), ignoree")
        continue
    urls.update(u for u in MOTIF_LOC.findall(r.text) if MOTIF_ARTICLE.match(u))
    time.sleep(0.5)  # politesse envers le serveur

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
