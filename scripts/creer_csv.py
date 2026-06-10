import csv

from scraping.medias import MEDIAS
from scraping.stockage import COLONNES, DATA_DIR

(DATA_DIR/"csv").mkdir(parents=True, exist_ok=True)

for media in MEDIAS:
    chemin = DATA_DIR/"csv"/f"{media}.csv"
    if chemin.exists():
        continue
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(COLONNES)