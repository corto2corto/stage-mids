import sqlite3

BASE = "/data/elias/stage-mids/data/urls.db"

batch = {}
with sqlite3.connect(BASE) as conn:
    rows = conn.execute("SELECT media, id, url FROM urls WHERE etat=0 GROUP BY media").fetchall()
    for media, id, url in rows:
        batch[media] = (id, url)

# Enlever le print ensuite, plutôt faire un return
print(batch)
