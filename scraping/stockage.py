"""Écriture des résultats : CSV de sortie + mise à jour de l'état en base.

États d'une URL dans la table `urls` :
- 0 : à scraper
- 1 : échec (pas de HTML récupéré)
- 2 : scrapée avec succès
"""

import csv

from scraping import extraction
from scraping.config import CSV_DIR

COLONNES = ["id", "url", "titre", "auteur", "date", "section", "free", "contenu"]


def ecriture_csv(media, id, url, html):
    """Extrait les métadonnées et écrit une ligne dans le CSV du média."""
    meta = extraction.extraire(media, html)
    chemin = CSV_DIR / f"{media}.csv"
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([id, url, meta["titre"], meta["auteur"], meta["date"], meta["section"], meta["free"], meta["contenu"]])


def maj_bdd(conn, id, etat=2):
    """Met à jour l'état d'une URL. Le commit est géré par l'appelant (par batch)."""
    conn.execute("UPDATE urls SET etat = ? WHERE id = ?", (etat, id))
