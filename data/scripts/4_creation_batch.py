import sqlite3

BASE = "/data/elias/stage-mids/data/urls.db"


def lire_batch(medias):
    """Renvoie une URL non traitée (etat=0) par média : {media: (id, url)}."""
    marques = ",".join("?" * len(medias))
    batch = {}
    with sqlite3.connect(BASE) as conn:
        rows = conn.execute(
            f"SELECT media, id, url FROM urls WHERE etat=0 AND media IN ({marques}) GROUP BY media",
            medias,
        ).fetchall()
    for media, id, url in rows:
        batch[media] = (id, url)
    return batch