"""Construit la liste des URLs d'articles Liberation via le sitemap Arc
Publishing pagine /arc/outboundfeeds/sitemap/?from=0..9900 (pas de 100).
ATTENTION : ce sitemap ne couvre que les ~10 000 articles les plus recents
(fenetre verifiee lors de la reco : from=15000 -> erreur serveur). Les
archives profondes (avant ~2025) sont derriere DataDome et seront mappees
plus tard via Selenium -- cf discussion.

    python -m exploration.mapping_liberation

MAPPING_LIMITE=N (env) : ne parcourt que N pages (smoke test).
"""
import csv
import html
import os
import re
import time

import requests
from tqdm import tqdm

BASE = "https://www.liberation.fr/arc/outboundfeeds/sitemap/"
SORTIE = "exploration/liberation_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")

froms = list(range(0, 10000, 100))
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    froms = froms[:limite]
print(f"{len(froms)} pages de sitemap a parcourir")

urls = set()
for n in tqdm(froms):
    try:
        r = requests.get(BASE, params={"outputType": "xml", "from": n}, headers=ENTETES, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"from={n} : echec ({e}), ignore")
        continue
    urls.update(
        html.unescape(u)
        for u in MOTIF_LOC.findall(r.text)
        if "liberation.fr" in u and "/arc/outboundfeeds/" not in u
    )
    time.sleep(0.5)  # politesse envers le serveur

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
