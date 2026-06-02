"""Constitution d'un batch d'URLs à scraper depuis la base sqlite.

Un batch = une URL par média encore à traiter (etat=0).
"""

import sqlite3

from scraping.config import BASE


def new_batch():
    """Retourne {media: (id, url)} : une URL non encore scrapée par média."""
    batch = {}
    with sqlite3.connect(BASE) as conn:
        rows = conn.execute(
            "SELECT media, id, url FROM urls WHERE etat=0 GROUP BY media"
        ).fetchall()
        for media, id, url in rows:
            batch[media] = (id, url)
    return batch
