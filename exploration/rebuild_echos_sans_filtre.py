# Rebuild TEST des Échos SANS le filtre « total > 10 », dans un fichier à part —
# lesechos_ngram.db (prod) n'est pas touché. But : mesurer l'inflation réelle
# (taille, lignes, durées) avant de décider pour les autres médias.
# Différences avec scripts/ngram_lesechos.py :
# - staging dans un fichier séparé (supprimé à la fin) : la base finale sort
#   compacte sans VACUUM, sa taille sur disque = la mesure directe
# - pas de filtre → plus besoin des fonctions de fenêtre ni du nettoyage de token
# - chrono, lignes insérées et tailles imprimés à chaque phase

import os

TMP = "/data/elias/stage-mids/data/sqlite_tmp"
os.makedirs(TMP, exist_ok=True)
os.environ["SQLITE_TMPDIR"] = TMP
os.environ["TMPDIR"] = TMP

import re
import sqlite3
import time
from collections import Counter
import pandas as pd

DOSSIER = "/data/elias/stage-mids/data/corpus"
FINAL = f"{DOSSIER}/lesechos_ngram_sans_filtre.db"
STAGING = f"{DOSSIER}/lesechos_staging_sans_filtre.db"
for f in (FINAL, STAGING):
    if os.path.exists(f):
        os.remove(f)

debut = time.time()
conn = sqlite3.connect(FINAL)
conn.executescript(f"""
    PRAGMA page_size = 65536;       -- 64 ko/page : ~16x moins d'operations sur disque lent
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA cache_size = -8000000;   -- ~8 Go de cache en RAM (negatif = ko)
    ATTACH DATABASE '{STAGING}' AS stg;
    PRAGMA stg.page_size = 65536;
    PRAGMA stg.journal_mode = OFF;
    PRAGMA stg.synchronous = OFF;
    CREATE TABLE token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
    CREATE TABLE stg.unigram_staging (w1, date, n);
    CREATE TABLE stg.bigram_staging  (w1, w2, date, n);
    CREATE TABLE stg.trigram_staging (w1, w2, w3, date, n);
""")

reader = pd.read_csv(f"{DOSSIER}/lesechos.csv",
                     usecols=["headline", "text", "date_published"], chunksize=50_000)

n_chunks = 0
n_articles = 0
for chunk in reader:
    n_chunks += 1
    n_articles += len(chunk)
    d = pd.to_datetime(chunk["date_published"].str[:10], format="%Y-%m-%d", errors="coerce")
    chunk = chunk.assign(date=d.dt.strftime("%Y%m%d"),
                         txt=chunk["headline"].fillna("") + "\n" + chunk["text"].fillna(""))
    chunk = chunk.dropna(subset=["date"]).astype({"date": int})

    for date, group in chunk.groupby("date"):
        date = int(date)
        uni, bi, tri = Counter(), Counter(), Counter()
        for text in group["txt"]:
            text = re.sub(r"(?<=[A-Z])\.", "", text).lower().replace("’", "'")
            for sentence in re.split(r"""[!"#$%&\()*+,./:;<=>?@\[\\\]^_`{|}~\n]""", text):
                tokens = re.findall(r"[a-zà-ÿ0-9']+", sentence)
                uni.update(tokens)
                bi.update(zip(tokens, tokens[1:]))
                tri.update(zip(tokens, tokens[1:], tokens[2:]))
        if not uni:
            continue

        words = set(uni) | {w for g in bi for w in g} | {w for g in tri for w in g}
        conn.executemany("INSERT OR IGNORE INTO token(word) VALUES (?)", [(w,) for w in words])
        ids = dict(conn.execute(
            f"SELECT word, id FROM token WHERE word IN ({','.join('?' * len(words))})",
            list(words)))

        conn.executemany("INSERT INTO stg.unigram_staging VALUES (?,?,?)",
                         [(ids[w], date, c) for w, c in uni.items()])
        conn.executemany("INSERT INTO stg.bigram_staging VALUES (?,?,?,?)",
                         [(ids[a], ids[b], date, c) for (a, b), c in bi.items()])
        conn.executemany("INSERT INTO stg.trigram_staging VALUES (?,?,?,?,?)",
                         [(ids[a], ids[b], ids[c2], date, c) for (a, b, c2), c in tri.items()])
    conn.commit()
    if n_chunks % 10 == 0:
        print(f"chunk {n_chunks} : {n_articles:,} articles lus, "
              f"staging {os.path.getsize(STAGING)/2**30:.1f} Gio, "
              f"{time.time() - debut:.0f} s", flush=True)

print(f"--- lecture CSV finie : {n_articles:,} articles, {n_chunks} chunks, "
      f"staging {os.path.getsize(STAGING)/2**30:.1f} Gio, "
      f"{(time.time() - debut)/60:.0f} min ---", flush=True)

# staging -> final : SUM(n) agrège les jours répartis sur plusieurs chunks ; PAS de filtre
PHASES = [
    ("total_unigram",
     "CREATE TABLE total_unigram (date INTEGER, total INTEGER, PRIMARY KEY (date)) WITHOUT ROWID",
     "INSERT INTO total_unigram SELECT date, SUM(n) FROM stg.unigram_staging GROUP BY date"),
    ("total_bigram",
     "CREATE TABLE total_bigram (date INTEGER, total INTEGER, PRIMARY KEY (date)) WITHOUT ROWID",
     "INSERT INTO total_bigram SELECT date, SUM(n) FROM stg.bigram_staging GROUP BY date"),
    ("total_trigram",
     "CREATE TABLE total_trigram (date INTEGER, total INTEGER, PRIMARY KEY (date)) WITHOUT ROWID",
     "INSERT INTO total_trigram SELECT date, SUM(n) FROM stg.trigram_staging GROUP BY date"),
    ("unigram",
     "CREATE TABLE unigram (w1 INTEGER, date INTEGER, n INTEGER, PRIMARY KEY (w1, date)) WITHOUT ROWID",
     "INSERT INTO unigram SELECT w1, date, SUM(n) FROM stg.unigram_staging GROUP BY w1, date"),
    ("bigram",
     "CREATE TABLE bigram (w1 INTEGER, w2 INTEGER, date INTEGER, n INTEGER, PRIMARY KEY (w1, w2, date)) WITHOUT ROWID",
     "INSERT INTO bigram SELECT w1, w2, date, SUM(n) FROM stg.bigram_staging GROUP BY w1, w2, date"),
    ("trigram",
     "CREATE TABLE trigram (w1 INTEGER, w2 INTEGER, w3 INTEGER, date INTEGER, n INTEGER, PRIMARY KEY (w1, w2, w3, date)) WITHOUT ROWID",
     "INSERT INTO trigram SELECT w1, w2, w3, date, SUM(n) FROM stg.trigram_staging GROUP BY w1, w2, w3, date"),
]
for nom, create, insert in PHASES:
    t0 = time.time()
    conn.execute(create)
    conn.execute(insert)
    conn.commit()
    lignes = conn.execute("SELECT changes()").fetchone()[0]
    print(f"{nom} : {lignes:,} lignes, {time.time() - t0:.0f} s, "
          f"base {os.path.getsize(FINAL)/2**30:.2f} Gio", flush=True)

conn.execute("DETACH DATABASE stg")
conn.execute("PRAGMA journal_mode = WAL")
conn.close()
os.remove(STAGING)
print(f"--- FINI en {(time.time() - debut)/60:.0f} min ; base finale "
      f"{os.path.getsize(FINAL)/2**30:.2f} Gio "
      f"(référence avec filtre : lesechos_ngram.db ~8,3 Gio) ---", flush=True)
