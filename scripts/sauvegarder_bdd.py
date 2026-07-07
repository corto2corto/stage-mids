# Sauvegarde urls.db vers urls.db.bak-<horodatage>. VACUUM INTO lit un
# instantané cohérent (WAL inclus) même si le pipeline tourne, et compacte
# au passage. Les vieux .bak sont à supprimer à la main quand ils ne servent plus.
# À lancer sur le serveur : python -m scripts.sauvegarder_bdd

import sqlite3
import time

BASE = "/data/elias/stage-mids/data/urls.db"

cible = f"{BASE}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
print(f"sauvegarde vers {cible} (quelques minutes pour ~8 Go)...")
with sqlite3.connect(BASE) as conn:
    conn.execute(f"VACUUM INTO '{cible}'")
print("fait.")
