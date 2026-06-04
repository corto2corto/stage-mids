import csv

from scraping.config import CSV_DIR
from scraping.stockage import COLONNES

MEDIAS = [
    "le_monde",
    "le_figaro",
    "le_journal_du_dimanche",
    "paris_match",
    "le_capital",
    "les_echos",
    "valeurs_actuelles",
    "le_nouvel_observateur",
    "nice_matin",
    "telerama",
]

CSV_DIR.mkdir(parents=True, exist_ok=True)

for media in MEDIAS:
    chemin = CSV_DIR / f"{media}.csv"
    if chemin.exists():
        continue
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(COLONNES)