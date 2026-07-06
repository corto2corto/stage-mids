"""Prépare la base du test des groupes de vagues : 300 URLs par média, tirées
au hasard dans les CSV d'URLs (exploration/ pour les nouveaux médias, data/urls
de la prod pour les anciens). Crée aussi les CSV de sortie avec leur en-tête.

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
           Path("/data/elias/stage-mids/data/urls")]
N = 300

random.seed(42)   # tirage reproductible
DOSSIER.mkdir(exist_ok=True)
(DOSSIER / "csv").mkdir(exist_ok=True)

conn = sqlite3.connect(DOSSIER / "urls.db")
conn.execute("CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY, "
             "media TEXT NOT NULL, url TEXT NOT NULL, etat INTEGER NOT NULL DEFAULT 0)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_media_etat ON urls(media, etat)")
conn.execute("DELETE FROM urls")

for media in sorted(MEDIAS):
    chemin = next((d / f"{media}_url.csv" for d in SOURCES
                   if (d / f"{media}_url.csv").exists()), None)
    if not chemin:
        print(f"{media:<24} PAS DE CSV D'URLS TROUVÉ")
        continue
    with open(chemin, newline="", encoding="utf-8") as f:
        urls = [ligne["url"] for ligne in csv.DictReader(f)]
    tirage = random.sample(urls, min(N, len(urls)))
    conn.executemany("INSERT INTO urls (media, url) VALUES (?, ?)",
                     [(media, u) for u in tirage])
    with open(DOSSIER / "csv" / f"{media}.csv", "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=COLONNES).writeheader()
    print(f"{media:<24} {len(tirage)} URLs (source : {chemin.parent})")

conn.commit()
total = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
print(f"\nBase prête : {total} URLs dans {DOSSIER/'urls.db'}")
conn.close()
