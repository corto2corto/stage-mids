"""Prépare la base du test : URLs tirées au hasard dans les CSV d'URLs de
chaque média (exploration/ pour les nouveaux, data/urls de la prod pour les
anciens), volumes calibrés par moteur pour tenir une session de 2 h. Crée
aussi les CSV de sortie avec leur en-tête. mediapart n'a pas de CSV d'URLs :
ses URLs sont reprises de la base du test xl.

À lancer depuis la racine du clone v2 : python -m exploration.preparer_test_grp
"""

import csv
import random
import sqlite3
from pathlib import Path

from scraping.medias import MEDIAS
from scraping.stockage import COLONNES

DOSSIER = Path("/data/elias/stage-mids-v2/exploration/test_run_grp")
SOURCES = [Path("/data/elias/stage-mids-v2/exploration"),
           Path("/data/elias/stage-mids/data/urls"),
           Path("/data/elias/stage-mids/exploration")]   # mediapart_url.csv vit là
BASE_XL = Path("/data/elias/stage-mids-v2/exploration/test_run_xl/urls.db")
N_PAR_MOTEUR = {"basic": 2200, "firefox": 800, "log": 600}   # ~2 h à débit nominal

random.seed(77)   # tirage reproductible, distinct des tests précédents
DOSSIER.mkdir(exist_ok=True)
(DOSSIER / "csv").mkdir(exist_ok=True)

conn = sqlite3.connect(DOSSIER / "urls.db")
conn.execute("CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, "
             "media TEXT NOT NULL, url TEXT NOT NULL, etat INTEGER NOT NULL DEFAULT 0)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_media_etat ON urls(media, etat)")
conn.execute("DELETE FROM urls")

for media in sorted(MEDIAS):
    n = N_PAR_MOTEUR[MEDIAS[media]["moteur"]]
    chemin = next((d / f"{media}_url.csv" for d in SOURCES
                   if (d / f"{media}_url.csv").exists()), None)
    if chemin:
        with open(chemin, newline="", encoding="utf-8") as f:
            urls = [ligne["url"] for ligne in csv.DictReader(f)]
        tirage = random.sample(urls, min(n, len(urls)))
    elif BASE_XL.exists():   # mediapart : pas de CSV, on reprend la base xl
        xl = sqlite3.connect(BASE_XL)
        tirage = [u for (u,) in xl.execute(
            "SELECT url FROM urls WHERE media=? ORDER BY RANDOM() LIMIT ?", (media, n))]
        xl.close()
    else:
        print(f"{media:<24} AUCUNE SOURCE D'URLS")
        continue
    conn.executemany("INSERT INTO urls (media, url) VALUES (?, ?)",
                     [(media, u) for u in tirage])
    with open(DOSSIER / "csv" / f"{media}.csv", "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=COLONNES).writeheader()
    print(f"{media:<24} {len(tirage)} URLs")

conn.commit()
total = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
print(f"\nBase prête : {total} URLs dans {DOSSIER/'urls.db'}")
conn.close()
