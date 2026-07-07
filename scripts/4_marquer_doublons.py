# Marque dans urls.db les articles déjà présents dans regicid/press_metadata (etat = 3),
# pour ne pas les re-scraper. À relancer après chaque chargement de nouveau média.
# Seule écriture sur les URLs : UPDATE etat 0 -> 3 ; jamais de DELETE, les états
# 1/2/4 ne sont pas touchés. Sauvegarde automatique de urls.db avant l'écriture.
#   uv pip install datasets   # si pas déjà installé

import os
os.environ["HF_HOME"] = "/data/elias/hf_cache"          # cache HF du projet (serveur partagé)
os.environ["SQLITE_TMPDIR"] = "/data/elias/stage-mids/data"  # temp SQLite sur /data, pas /tmp

import sqlite3
import time
import pandas as pd
from datasets import get_dataset_config_names, load_dataset

REPO = "regicid/press_metadata"
BASE = "/data/elias/stage-mids/data/urls.db"

# 1) Télécharger media + url de tous les sous-ensembles de regicid
externe = pd.concat(
    [
        load_dataset(REPO, config, split="train").select_columns(["url"]).to_pandas().assign(media=config)
        for config in get_dataset_config_names(REPO)
    ],
    ignore_index=True,
)[["media", "url"]]
print(f"{len(externe)} URLs externes")

# 2) Marquer les doublons (etat = 3) parmi les URLs encore à scraper (etat = 0)
with sqlite3.connect(BASE) as conn:
    sauvegarde = f"{BASE}.bak-{time.strftime('%Y%m%d-%H%M%S')}"   # VACUUM INTO refuse d'écraser : nom horodaté
    print(f"sauvegarde de urls.db vers {sauvegarde} (quelques minutes)...")
    conn.execute(f"VACUUM INTO '{sauvegarde}'")
    externe.to_sql("urls_externes", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_externes_url ON urls_externes(url)")
    cur = conn.execute(
        "UPDATE urls SET etat = 3 "
        "WHERE etat = 0 AND EXISTS (SELECT 1 FROM urls_externes e WHERE e.url = urls.url)"
    )
    conn.commit()
    print(f"{cur.rowcount} doublons marqués (etat = 3)")
    # Table de travail : ne pas laisser des millions d'URLs externes gonfler urls.db.
    conn.execute("DROP TABLE urls_externes")
    conn.commit()
