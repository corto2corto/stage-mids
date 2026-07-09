"""
Constitution d'un batch d'URLs à scraper depuis la base sqlite.
Un batch = une URL par média encore à traiter (etat 0, ou 1 en seconde chance).
"""

import sqlite3

from scraping.stockage import DATA_DIR

def new_batch():
    with sqlite3.connect(DATA_DIR/"urls.db", timeout=30) as conn:
        # Éligible si le média a des URLs neuves (0) OU des échecs à retenter (1).
        # Sans le 1, un média sans aucun 0 sortirait du batch et ses échecs ne
        # seraient jamais repris (prochaine_url jamais appelée pour lui).
        rows = conn.execute(
            "SELECT media, id, url FROM urls WHERE etat IN (0, 1) "
            "GROUP BY media"
        ).fetchall()
    return {media: (id, url) for media, id, url in rows}


def prochaine_url(conn, media):
    """Prochaine URL d'un média : les nouvelles d'abord (etat=0), puis une
    seconde chance aux échecs (etat=1). Renvoie (id, url, etat) ou None.
    Un échec retenté qui échoue encore passe en etat=4 (échec confirmé,
    cf pipeline.traiter_url) et n'est plus jamais repris."""
    return conn.execute(
        "SELECT id, url, etat FROM urls WHERE media=? AND etat IN (0, 1) "
        "ORDER BY etat LIMIT 1", (media,)
    ).fetchone()

if __name__ == "__main__":
    print(new_batch())