# Marque dans urls.db les articles déjà présents dans regicid/press_metadata (etat = 3),
# pour ne pas les re-scraper. À lancer une fois sur le serveur.
#   uv pip install datasets   # si pas déjà installé

import os
os.environ["HF_HOME"] = "/data/elias/hf_cache"          # cache HF du projet (serveur partagé)
os.environ["SQLITE_TMPDIR"] = "/data/elias/stage-mids/data"  # temp SQLite sur /data, pas /tmp

import sqlite3
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
    externe.to_sql("urls_externes", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_externes_url ON urls_externes(url)")
    cur = conn.execute(
        "UPDATE urls SET etat = 3 "
        "WHERE etat = 0 AND EXISTS (SELECT 1 FROM urls_externes e WHERE e.url = urls.url)"
    )
    conn.commit()
    print(f"{cur.rowcount} doublons marqués (etat = 3)")
