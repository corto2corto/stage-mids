"""
Constitution d'un batch d'URLs à scraper depuis la base sqlite.
Un batch = une URL par média encore à traiter (etat=0).
"""

import sqlite3

from scraping.stockage import DATA_DIR

def new_batch():
    with sqlite3.connect(DATA_DIR/"urls.db") as conn:
        rows = conn.execute(
            "SELECT media, id, url FROM urls WHERE etat=0 "
            "GROUP BY media"
        ).fetchall()
    return {media: (id, url) for media, id, url in rows}

if __name__ == "__main__":
    print(new_batch())