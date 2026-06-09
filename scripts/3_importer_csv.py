import os
import sqlite3
import pandas as pd

DOSSIER = "/data/elias/stage-mids/data"
BASE = "/data/elias/stage-mids/data/urls.db"

with sqlite3.connect(BASE) as conn:
    for fichier in (f for f in os.listdir(DOSSIER) if f.endswith(".csv")):
        df = pd.read_csv(os.path.join(DOSSIER, fichier), usecols=["url"])
        df["media"] = fichier.removesuffix("_articles.csv")
        df = df.drop_duplicates(subset="url")
        df.to_sql("urls", conn, if_exists="append", index=False)
        print(f"{fichier}: {len(df)} lignes")
