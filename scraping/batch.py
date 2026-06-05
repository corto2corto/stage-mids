"""
Constitution d'un batch d'URLs à scraper depuis la base sqlite.
Un batch = une URL par média encore à traiter (etat=0).
"""

import sqlite3

from scraping.config import BASE

def new_batch():
    batch = {}
    with sqlite3.connect(BASE) as conn:
        rows = conn.execute(
            "SELECT media, id, url FROM urls WHERE etat=0 GROUP BY media"
        ).fetchall()
        for media, id, url in rows:
            batch[media] = (id, url)
    return batch

if __name__ == "__main__":
    print(new_batch())