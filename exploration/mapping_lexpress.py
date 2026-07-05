"""Construit la liste des URLs d'articles L'Express via les deux index de
sitemaps hebdomadaires declares dans robots.txt : sitemap-by-week-2010-2020.xml
et sitemap-by-week-2020-now.xml (~850 semaines au total, couvre 2010 ->
aujourd'hui). Structure reperee lors de la reco -- cf discussion.

    python -m exploration.mapping_lexpress

MAPPING_LIMITE=N (env) : ne parcourt que N sitemaps (smoke test).
"""
import csv
import html
import os
import re
import time

import requests
from tqdm import tqdm

INDEX = [
    "https://www.lexpress.fr/arc/outboundfeeds/sitemap-by-week-2010-2020.xml",
    "https://www.lexpress.fr/arc/outboundfeeds/sitemap-by-week-2020-now.xml",
]
SORTIE = "exploration/lexpress_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}
MOTIF_SOUS_SITEMAP = re.compile(r"<loc>(https://www\.lexpress\.fr/arc/outboundfeeds/sitemap-all/weeks/[0-9-]+/\?outputType=xml)</loc>")
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")

sous_sitemaps = set()
for idx in INDEX:
    r = requests.get(idx, headers=ENTETES, timeout=30)
    r.raise_for_status()
    sous_sitemaps.update(MOTIF_SOUS_SITEMAP.findall(html.unescape(r.text)))
sous_sitemaps = sorted(sous_sitemaps)
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    sous_sitemaps = sous_sitemaps[-limite:]
print(f"{len(sous_sitemaps)} sitemaps hebdomadaires a parcourir")

urls = set()
for i, sm in enumerate(tqdm(sous_sitemaps), 1):
    try:
        r = requests.get(sm, headers=ENTETES, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"{sm} : echec ({e}), ignore")
        continue
    urls.update(u for u in MOTIF_LOC.findall(r.text) if "/arc/outboundfeeds/" not in u)
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
