import csv
import os

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

CSV_DIR = "/data/elias/stage-mids/data/csv"
COLONNES = ["id", "url", "contenu"]

os.makedirs(CSV_DIR, exist_ok=True)

for media in MEDIAS:
    chemin = os.path.join(CSV_DIR, f"{media}.csv")
    if os.path.exists(chemin):
        continue
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(COLONNES)