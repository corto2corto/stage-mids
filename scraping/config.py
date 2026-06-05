"""
Configuration centrale : tous les chemins et la liste des médias.
"""

from pathlib import Path

# Racine du dépôt (calculée à partir de l'emplacement de ce fichier).
# Sert à retrouver les ressources versionnées comme le dossier extensions/.
RACINE = Path(__file__).resolve().parent.parent

DATA_DIR = Path("/data/elias/stage-mids/data")

# --- Médias scrapés et leur moteur de scraping ---
SCRAPERS = {
    "le_monde":               "firefox",
    "le_figaro":              "firefox",
    "le_journal_du_dimanche": "firefox",
    "paris_match":            "firefox",
    "le_capital":             "firefox",
    "les_echos":              "firefox",
    "valeurs_actuelles":      "firefox",
    "le_nouvel_observateur":  "firefox",
    "nice_matin":             "firefox",
    "telerama":               "firefox",
}


if __name__ == "__main__":
    print(f"RACINE   : {RACINE}")
    print(f"DATA_DIR : {DATA_DIR}")
    print(f"\nSCRAPERS ({len(SCRAPERS)} médias) :")
    for media, moteur in SCRAPERS.items():
        print(f"  - {media:24} {moteur}")
