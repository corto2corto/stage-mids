import csv

from scraping.stockage import COLONNES, DATA_DIR

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

(DATA_DIR/"csv").mkdir(parents=True, exist_ok=True)

for media in MEDIAS:
    chemin = DATA_DIR/"csv"/f"{media}.csv"
    if chemin.exists():
        continue
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(COLONNES)