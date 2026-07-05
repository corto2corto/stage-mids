"""Construit la liste des URLs d'articles Paris-Normandie via le sitemapindex
Drupal (sitemaparchives-0..3 + monthly/weekly/daily/news, couvre 2019 ->
aujourd'hui, ~150k URLs). Particularite reperee lors de la reco : le CDN
(Akamai) exige des entetes Accept et Accept-Language de navigateur, sinon
Access Denied. Le sitemapmain (pages de sections) est ecarte par le filtre
"/article/".

    python -m exploration.mapping_paris_normandie

MAPPING_LIMITE=N (env) : ne parcourt que N sitemaps (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

INDEX = "https://www.paris-normandie.fr/sites/default/files/sitemaps/www_paris_normandie_fr/sitemapindex.xml"
SORTIE = "exploration/paris_normandie_url.csv"
ENTETES = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9",
}
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")

r = requests.get(INDEX, headers=ENTETES, timeout=30)
r.raise_for_status()
sous_sitemaps = sorted(u for u in set(MOTIF_LOC.findall(r.text)) if u.endswith(".xml"))
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    sous_sitemaps = sous_sitemaps[:limite]
print(f"{len(sous_sitemaps)} sitemaps a parcourir")

urls = set()
for sm in tqdm(sous_sitemaps):
    try:
        r = requests.get(sm, headers=ENTETES, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"{sm} : echec ({e}), ignore")
        continue
    urls.update(u for u in MOTIF_LOC.findall(r.text) if "/article/" in u)
    time.sleep(0.5)  # politesse envers le serveur

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
