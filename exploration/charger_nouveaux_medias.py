"""Charge dans urls.db les corpus d'URLs des médias du registre qui n'y sont
pas encore (les 13 nouveaux basic + mediapart). Garde-fous :

- ne touche qu'aux médias ABSENTS de la base (sondage indexé EXISTS) — un média
  déjà présent est ignoré avec un message, jamais réinséré ;
- les médias en pause (liberation) sont ignorés ;
- déduplication des URLs à l'intérieur de chaque CSV ;
- une transaction par média, comptages affichés à chaque étape ;
- uniquement des INSERT : jamais d'UPDATE ni de DELETE, les lignes et états
  existants ne sont pas touchés ;
- sauvegarde automatique de urls.db (VACUUM INTO urls.db.bak-<horodatage>,
  instantané cohérent même pipeline en cours) avant la première écriture —
  sautée s'il n'y a rien à charger.

À lancer depuis la racine du dépôt de PROD : python -m exploration.charger_nouveaux_medias
"""

import csv
import sqlite3
import time
from pathlib import Path

from scraping.medias import MEDIAS
from scraping.stockage import DATA_DIR

SOURCES = [Path("/data/elias/stage-mids-v2/exploration"),
           Path("/data/elias/stage-mids/data/urls"),
           Path("/data/elias/stage-mids/exploration")]

conn = sqlite3.connect(DATA_DIR / "urls.db", timeout=60)
total = 0
sauvegarde_faite = False
for media in sorted(MEDIAS):
    if MEDIAS[media].get("pause"):
        print(f"{media:<24} en pause : ignoré")
        continue
    if conn.execute("SELECT 1 FROM urls WHERE media=? LIMIT 1", (media,)).fetchone():
        print(f"{media:<24} déjà en base : ignoré")
        continue
    chemin = next((d / f"{media}_url.csv" for d in SOURCES
                   if (d / f"{media}_url.csv").exists()), None)
    if not chemin:
        print(f"{media:<24} AUCUN CSV TROUVÉ — à traiter à la main")
        continue
    with open(chemin, newline="", encoding="utf-8") as f:
        urls = list(dict.fromkeys(ligne["url"] for ligne in csv.DictReader(f)))
    if not sauvegarde_faite:   # VACUUM INTO refuse d'écraser : nom horodaté
        cible = DATA_DIR / f"urls.db.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        print(f"sauvegarde de urls.db vers {cible} (quelques minutes)...")
        conn.execute(f"VACUUM INTO '{cible}'")
        sauvegarde_faite = True
    with conn:   # une transaction par média : tout ou rien
        conn.executemany("INSERT INTO urls (media, url, etat) VALUES (?, ?, 0)",
                         [(media, u) for u in urls])
    print(f"{media:<24} {len(urls)} URLs insérées (source : {chemin})")
    total += len(urls)

print(f"\nTerminé : {total} URLs ajoutées.")
conn.close()
