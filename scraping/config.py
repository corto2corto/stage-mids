"""Configuration centrale : tous les chemins et la liste des médias.

C'est l'unique endroit où sont définis les chemins serveur et les médias
scrapés. Si un chemin change sur le serveur, on le modifie ici seulement.
"""

from pathlib import Path

# Racine du dépôt (calculée à partir de l'emplacement de ce fichier).
# Sert à retrouver les ressources versionnées comme le dossier extensions/.
RACINE = Path(__file__).resolve().parent.parent

# --- Données sur le serveur (chemins absolus, fixes) ---
DATA_DIR = Path("/data/elias/stage-mids/data")
BASE = DATA_DIR / "urls.db"      # base sqlite des URLs à scraper
CSV_DIR = DATA_DIR / "csv"       # CSV de sortie (un fichier par média)

# --- Ressources navigateur (sur le serveur) ---
EXTENSIONS_DIR = RACINE / "extensions" / "firefox"   # les .xpi (uBlock + bypass)
TMP_DIR = Path("/data/elias/tmp/firefox")            # dossier temporaire de Firefox

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
