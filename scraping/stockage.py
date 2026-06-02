"""Écriture des résultats : CSV de sortie + mise à jour de l'état en base.

États d'une URL dans la table `urls` :
- 0 : à scraper
- 1 : échec (pas de HTML récupéré)
- 2 : scrapée avec succès
"""

import csv

from bs4 import BeautifulSoup

from scraping.config import CSV_DIR


def ecriture_csv(media, id, url, html):
    """Parse le HTML et écrit une ligne (id, url, contenu) dans le CSV du média."""
    contenu = " ".join(
        p.get_text() for p in BeautifulSoup(html, "html.parser").find_all("p")
    )
    chemin = CSV_DIR / f"{media}.csv"
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([id, url, contenu])


def maj_bdd(conn, id, etat=2):
    """Met à jour l'état d'une URL. Le commit est géré par l'appelant (par batch)."""
    conn.execute("UPDATE urls SET etat = ? WHERE id = ?", (etat, id))
