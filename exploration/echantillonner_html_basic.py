"""Sauve le HTML de 5 articles (moteur basic) pour chaque media juge "basic sur"
par la sonde du 06/07, dans exploration/html_v2/ (<media>_<n>_basic.html).
Objectif : choisir la strategie et le selecteur "corps" de leurs futures
entrees dans scraping/medias.py.

A lancer sur le serveur :  python -m exploration.echantillonner_html_basic
"""
import csv
import time
from pathlib import Path

from scraping import basic

MEDIAS_BASIC = ["gala", "voici", "bfmtv", "francesoir", "ouest_france",
                "leparisien", "la_croix", "laprovence"]
N_PAR_MEDIA = 5
SORTIE = Path("exploration/html_v2")
SORTIE.mkdir(exist_ok=True)

session = basic.ouvrir_session()
for media in MEDIAS_BASIC:
    chemin = Path("exploration") / f"{media}_url.csv"
    with open(chemin, newline="", encoding="utf-8") as f:
        total = sum(1 for _ in f) - 1
    positions = {int(total * (i + 0.5) / N_PAR_MEDIA) for i in range(N_PAR_MEDIA)}
    echantillon = []
    with open(chemin, newline="", encoding="utf-8") as f:
        for i, ligne in enumerate(csv.DictReader(f)):
            if i in positions:
                echantillon.append(ligne["url"])

    print(f"=== {media} ===", flush=True)
    for num, url in enumerate(echantillon, 1):
        try:
            html = basic.scraper(session, url)
        except Exception as e:
            print(f"  ECHEC {type(e).__name__:<18} {url[:90]}", flush=True)
            continue
        (SORTIE / f"{media}_{num:02d}_basic.html").write_text(html, encoding="utf-8")
        print(f"  {len(html):>8} chars  {url[:90]}", flush=True)
        time.sleep(1)

print("=== ECHANTILLONNAGE TERMINE ===", flush=True)
