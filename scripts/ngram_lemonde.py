# Comptes uni/bi/trigrammes de Le Monde, par jour, dans lemonde_ngram.db.
# Lecture du CSV par chunks (11 Go) ; tokenisation identique au ngram_light.py de la team.

import os
os.environ["SQLITE_TMPDIR"] = "/data/elias/stage-mids/data"  # gros temp, pas /tmp

import re
import sqlite3
from collections import Counter
import pandas as pd

conn = sqlite3.connect("/data/elias/stage-mids/data/corpus/lemonde_ngram.db")
conn.executescript("""
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    CREATE TABLE IF NOT EXISTS token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
    CREATE TABLE unigram_staging (w1, annee, mois, jour, n);
    CREATE TABLE bigram_staging  (w1, w2, annee, mois, jour, n);
    CREATE TABLE trigram_staging (w1, w2, w3, annee, mois, jour, n);
""")

reader = pd.read_csv("/data/elias/stage-mids/data/corpus/lemonde.csv",
                     usecols=["text", "year", "month", "day"], chunksize=50_000)

for chunk in reader:
    chunk = chunk.dropna(subset=["text", "year", "month", "day"]).astype(
        {"year": int, "month": int, "day": int})

    for (year, month, day), group in chunk.groupby(["year", "month", "day"]):
        year, month, day = int(year), int(month), int(day)  # sinon numpy.int64 -> stocké en BLOB
        uni, bi, tri = Counter(), Counter(), Counter()
        for text in group["text"]:
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

        conn.executemany("INSERT INTO unigram_staging VALUES (?,?,?,?,?)",
                         [(ids[w], year, month, day, c) for w, c in uni.items()])
        conn.executemany("INSERT INTO bigram_staging VALUES (?,?,?,?,?,?)",
                         [(ids[a], ids[b], year, month, day, c) for (a, b), c in bi.items()])
        conn.executemany("INSERT INTO trigram_staging VALUES (?,?,?,?,?,?,?)",
                         [(ids[a], ids[b], ids[c2], year, month, day, c) for (a, b, c2), c in tri.items()])
    conn.commit()

# staging -> final : SUM(n) agrège les jours répartis sur plusieurs chunks
print("finalisation...")
conn.executescript("""
    -- totaux journaliers AVANT filtrage (denominateur N_t des frequences relatives)
    CREATE TABLE total_unigram (annee INTEGER, mois INTEGER, jour INTEGER, total INTEGER,
        PRIMARY KEY (annee, mois, jour)) WITHOUT ROWID;
    INSERT INTO total_unigram SELECT annee, mois, jour, SUM(n) FROM unigram_staging GROUP BY annee, mois, jour;
    CREATE TABLE total_bigram (annee INTEGER, mois INTEGER, jour INTEGER, total INTEGER,
        PRIMARY KEY (annee, mois, jour)) WITHOUT ROWID;
    INSERT INTO total_bigram SELECT annee, mois, jour, SUM(n) FROM bigram_staging GROUP BY annee, mois, jour;
    CREATE TABLE total_trigram (annee INTEGER, mois INTEGER, jour INTEGER, total INTEGER,
        PRIMARY KEY (annee, mois, jour)) WITHOUT ROWID;
    INSERT INTO total_trigram SELECT annee, mois, jour, SUM(n) FROM trigram_staging GROUP BY annee, mois, jour;

    -- tables finales : agregees par jour, typees INTEGER, filtrees sur le total GLOBAL du ngram (> 10)
    CREATE TABLE unigram (w1 INTEGER, annee INTEGER, mois INTEGER, jour INTEGER, n INTEGER,
        PRIMARY KEY (w1, annee, mois, jour)) WITHOUT ROWID;
    INSERT INTO unigram SELECT w1, annee, mois, jour, n FROM (
        SELECT w1, annee, mois, jour, SUM(n) AS n, SUM(SUM(n)) OVER (PARTITION BY w1) AS tot
        FROM unigram_staging GROUP BY w1, annee, mois, jour
    ) WHERE tot > 10;
    DROP TABLE unigram_staging;
    CREATE TABLE bigram (w1 INTEGER, w2 INTEGER, annee INTEGER, mois INTEGER, jour INTEGER, n INTEGER,
        PRIMARY KEY (w1, w2, annee, mois, jour)) WITHOUT ROWID;
    INSERT INTO bigram SELECT w1, w2, annee, mois, jour, n FROM (
        SELECT w1, w2, annee, mois, jour, SUM(n) AS n, SUM(SUM(n)) OVER (PARTITION BY w1, w2) AS tot
        FROM bigram_staging GROUP BY w1, w2, annee, mois, jour
    ) WHERE tot > 10;
    DROP TABLE bigram_staging;
    CREATE TABLE trigram (w1 INTEGER, w2 INTEGER, w3 INTEGER, annee INTEGER, mois INTEGER, jour INTEGER, n INTEGER,
        PRIMARY KEY (w1, w2, w3, annee, mois, jour)) WITHOUT ROWID;
    INSERT INTO trigram SELECT w1, w2, w3, annee, mois, jour, n FROM (
        SELECT w1, w2, w3, annee, mois, jour, SUM(n) AS n, SUM(SUM(n)) OVER (PARTITION BY w1, w2, w3) AS tot
        FROM trigram_staging GROUP BY w1, w2, w3, annee, mois, jour
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
print("terminé")
