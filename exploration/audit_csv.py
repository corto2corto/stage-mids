"""Audit de cohérence des CSV médias (lecture seule) : pour chaque data/csv/<media>.csv,
- doublons d'ids (même ligne écrite plusieurs fois, à corriger avec dedup_csv.py) ;
- croisement avec urls.db : état des ids présents dans le CSV (attendu : tous etat=2 ;
  un etat=5 est un non-article resté dans le CSV, un « absent » un id hors base) ;
- contenus vides et dates vides.

Constat d'origine (francesoir, 19/07/2026) : 15 lignes en doublon et 2 371 non-articles
passés etat=5 mais restés dans le CSV. Ce script fait le même contrôle partout.
Les médias en cours de scrapping peuvent afficher un léger écart (lignes en vol).

    python -m exploration.audit_csv
"""

import csv
import sqlite3
from collections import Counter

from scraping.stockage import DATA_DIR

csv.field_size_limit(10**8)

conn = sqlite3.connect(f"file:{DATA_DIR/'urls.db'}?mode=ro", uri=True)

for chemin in sorted((DATA_DIR/"csv").glob("*.csv")):
    media = chemin.stem
    etats = dict(conn.execute("SELECT id, etat FROM urls WHERE media = ?", (media,)))

    total = doublons = contenus_vides = dates_vides = 0
    vus = set()
    par_etat = Counter()
    with open(chemin, newline="", encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            total += 1
            id_ = int(ligne["id"])
            if id_ in vus:
                doublons += 1
            vus.add(id_)
            par_etat[etats.get(id_, "absent")] += 1
            if not ligne["contenu"].strip():
                contenus_vides += 1
            if not ligne["date"].strip():
                dates_vides += 1

    hors_2 = {e: n for e, n in sorted(par_etat.items(), key=str) if e != 2}
    print(f"{media:24} lignes={total:>8}  doublons={doublons:>5}  "
          f"contenus_vides={contenus_vides:>6}  dates_vides={dates_vides:>7}  "
          f"etats_hors_2={hors_2 or 'aucun'}", flush=True)
