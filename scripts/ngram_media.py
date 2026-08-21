# Comptes uni/bi/trigrammes d'un média, par jour, dans <media>_ngram.db.
# Fusion des anciens ngram_lemonde/lesechos/lefigaro/mediapart.py : même
# mécanisme partout (staging puis tables finales, filtre > 10), seuls changent
# le CSV source et la façon d'en tirer la date et le texte.
# Usage : python -m scripts.ngram_media lemonde|lesechos|lefigaro|mediapart

import os
os.environ["SQLITE_TMPDIR"] = "/data/elias/stage-mids/data"  # gros temp, pas /tmp

import sqlite3
import sys
from collections import Counter

import pandas as pd

from scripts.tokenisation import phrases

MEDIAS = {
    # csv (sous data/), colonnes lues, chunksize, cache SQLite (ko)
    "lemonde":   ("corpus/lemonde.csv",  ["text", "year", "month", "day"],       50_000, 8_000_000),
    "lesechos":  ("corpus/lesechos.csv", ["headline", "text", "date_published"], 50_000, 8_000_000),
    "lefigaro":  ("corpus/lefigaro.csv", ["headline", "text", "date_published"], 50_000, 8_000_000),
    "mediapart": ("csv/mediapart.csv",   ["date", "contenu"],                    20_000, 4_000_000),
}

media = sys.argv[1]
csv, usecols, chunksize, cache_ko = MEDIAS[media]


def preparer(chunk):
    # Normalise un chunk en deux colonnes : date (int YYYYMMDD) et txt.
    if media == "lemonde":  # date en trois colonnes year/month/day
        chunk = chunk.dropna(subset=["text", "year", "month", "day"]).astype(
            {"year": int, "month": int, "day": int})
        return chunk.assign(date=chunk["year"] * 10000 + chunk["month"] * 100 + chunk["day"],
                            txt=chunk["text"])
    if media == "mediapart":  # date ISO, texte dans contenu
        chunk = chunk.dropna(subset=["date", "contenu"])
        chunk = chunk[chunk["date"].str.len() >= 10]
        return chunk.assign(date=chunk["date"].str[:10].str.replace("-", "").astype(int),
                            txt=chunk["contenu"])
    # lesechos, lefigaro : date_published ISO, texte = titre + corps
    d = pd.to_datetime(chunk["date_published"].str[:10], format="%Y-%m-%d", errors="coerce")
    chunk = chunk.assign(date=d.dt.strftime("%Y%m%d"),
                         txt=chunk["headline"].fillna("") + "\n" + chunk["text"].fillna(""))
    return chunk.dropna(subset=["date"]).astype({"date": int})


conn = sqlite3.connect(f"/data/elias/stage-mids/data/corpus/{media}_ngram.db")
conn.executescript(f"""
    PRAGMA page_size = 65536;       -- 64 ko/page : ~16x moins d'operations sur disque lent
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA cache_size = -{cache_ko};   -- cache en RAM (negatif = ko)
    CREATE TABLE IF NOT EXISTS token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS unigram_staging (w1, date, n);
    CREATE TABLE IF NOT EXISTS bigram_staging  (w1, w2, date, n);
    CREATE TABLE IF NOT EXISTS trigram_staging (w1, w2, w3, date, n);
""")

reader = pd.read_csv(f"/data/elias/stage-mids/data/{csv}", usecols=usecols, chunksize=chunksize)

for chunk in reader:
    chunk = preparer(chunk)

    for date, group in chunk.groupby("date"):
        date = int(date)
        uni, bi, tri = Counter(), Counter(), Counter()
        for text in group["txt"]:
            for tokens in phrases(text):
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

        conn.executemany("INSERT INTO unigram_staging VALUES (?,?,?)",
                         [(ids[w], date, c) for w, c in uni.items()])
        conn.executemany("INSERT INTO bigram_staging VALUES (?,?,?,?)",
                         [(ids[a], ids[b], date, c) for (a, b), c in bi.items()])
        conn.executemany("INSERT INTO trigram_staging VALUES (?,?,?,?,?)",
                         [(ids[a], ids[b], ids[c2], date, c) for (a, b, c2), c in tri.items()])
    conn.commit()

# staging -> final : SUM(n) agrège les jours répartis sur plusieurs chunks
conn.executescript("""
    -- totaux journaliers AVANT filtrage (denominateur N_t des frequences relatives)
    CREATE TABLE IF NOT EXISTS total_unigram (date INTEGER, total INTEGER, PRIMARY KEY (date)) WITHOUT ROWID;
    INSERT INTO total_unigram SELECT date, SUM(n) FROM unigram_staging GROUP BY date;
    CREATE TABLE IF NOT EXISTS total_bigram (date INTEGER, total INTEGER, PRIMARY KEY (date)) WITHOUT ROWID;
    INSERT INTO total_bigram SELECT date, SUM(n) FROM bigram_staging GROUP BY date;
    CREATE TABLE IF NOT EXISTS total_trigram (date INTEGER, total INTEGER, PRIMARY KEY (date)) WITHOUT ROWID;
    INSERT INTO total_trigram SELECT date, SUM(n) FROM trigram_staging GROUP BY date;

    -- tables finales : agregees par jour, typees INTEGER, filtrees sur le total GLOBAL du ngram (> 10)
    CREATE TABLE IF NOT EXISTS unigram (w1 INTEGER, date INTEGER, n INTEGER,
        PRIMARY KEY (w1, date)) WITHOUT ROWID;
    INSERT INTO unigram SELECT w1, date, n FROM (
        SELECT w1, date, SUM(n) AS n, SUM(SUM(n)) OVER (PARTITION BY w1) AS tot
        FROM unigram_staging GROUP BY w1, date
    ) WHERE tot > 10;
    DROP TABLE unigram_staging;
    CREATE TABLE IF NOT EXISTS bigram (w1 INTEGER, w2 INTEGER, date INTEGER, n INTEGER,
        PRIMARY KEY (w1, w2, date)) WITHOUT ROWID;
    INSERT INTO bigram SELECT w1, w2, date, n FROM (
        SELECT w1, w2, date, SUM(n) AS n, SUM(SUM(n)) OVER (PARTITION BY w1, w2) AS tot
        FROM bigram_staging GROUP BY w1, w2, date
    ) WHERE tot > 10;
    DROP TABLE bigram_staging;
    CREATE TABLE IF NOT EXISTS trigram (w1 INTEGER, w2 INTEGER, w3 INTEGER, date INTEGER, n INTEGER,
        PRIMARY KEY (w1, w2, w3, date)) WITHOUT ROWID;
    INSERT INTO trigram SELECT w1, w2, w3, date, n FROM (
        SELECT w1, w2, w3, date, SUM(n) AS n, SUM(SUM(n)) OVER (PARTITION BY w1, w2, w3) AS tot
        FROM trigram_staging GROUP BY w1, w2, w3, date
    ) WHERE tot > 10;
    DROP TABLE trigram_staging;
    -- token : retire les mots devenus orphelins apres filtrage
    DELETE FROM token WHERE id NOT IN (
        SELECT w1 FROM unigram
        UNION SELECT w1 FROM bigram  UNION SELECT w2 FROM bigram
        UNION SELECT w1 FROM trigram UNION SELECT w2 FROM trigram UNION SELECT w3 FROM trigram
    );
""")
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("VACUUM")
conn.close()
print(f"FINI : {media}_ngram.db construite")
