"""Construit la liste des URLs d'articles Blast par pagination deterministe --
pas besoin d'agent LLM : /articles?page=1..320, 6 articles par page, structure
decouverte manuellement (cf. discussion).

    python -m exploration.mapping_blast
"""
import csv
import re
import time

import requests
from tqdm import tqdm

BASE = "https://www.blast-info.fr/articles"
SORTIE = "exploration/blast_url.csv"
TOTAL_PAGES = 320
MOTIF = re.compile(r'href="(/articles/\d{4}/[^"]+)"')

urls = set()

for page in tqdm(range(1, TOTAL_PAGES + 1)):
    try:
        r = requests.get(
            BASE, params={"page": page},
            headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"},
            timeout=10,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"page {page} : echec ({e}), ignoree")
        continue
    urls.update("https://www.blast-info.fr" + m for m in MOTIF.findall(r.text))
    time.sleep(0.5)  # politesse envers le serveur

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])

print(f"{len(urls)} URLs ecrites dans {SORTIE}")
