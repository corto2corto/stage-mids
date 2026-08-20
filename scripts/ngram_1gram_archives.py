# Comptes UNIGRAMMES des anciens médias depuis leurs ARCHIVES, par jour, dans
# <media>_1gram.db — conformes aux bases du pipeline (ngram_1gram.py) :
# vocabulaire partagé data/corpus/vocabulaire.db, pas de filtre, unigrammes
# seuls, copie locale de token. Les anciennes bases <media>_ngram.db (ids
# locaux, filtre > 10) sont conservées telles quelles.
#
# Sources (formats hérités, différents du CSV pipeline) :
#   le_monde  : data/corpus/lemonde.csv  — text, year/month/day
#   le_figaro : data/corpus/lefigaro.csv — text, date_published (ISO)
#   les_echos : data/corpus/lesechos.csv — text, date_published (ISO)
# (mediapart n'a pas d'archive : sa base 1gram se construit via ngram_1gram.py)
#
# Même contrainte que ngram_1gram.py : constructions SÉQUENTIELLES uniquement,
# le vocabulaire partagé interdit deux écritures simultanées.
# Usage (sur gallica) : python -m scripts.ngram_1gram_archives <media>

import os
os.environ["SQLITE_TMPDIR"] = "/data/elias/stage-mids/data/sqlite_tmp"  # gros temp, pas /tmp

import sqlite3
import sys
import time
from collections import Counter

import pandas as pd

from scripts.tokenisation import phrases

media = sys.argv[1]
DOSSIER = "/data/elias/stage-mids/data/corpus"
ARCHIVES = {"le_monde": "lemonde.csv", "le_figaro": "lefigaro.csv",
            "les_echos": "lesechos.csv"}
if media not in ARCHIVES:
    sys.exit(f"ABANDON : pas d'archive pour {media} (choix : {', '.join(ARCHIVES)}).")
CSV = f"{DOSSIER}/{ARCHIVES[media]}"
DB = f"{DOSSIER}/{media}_1gram.db"

os.makedirs("/data/elias/stage-mids/data/sqlite_tmp", exist_ok=True)
if os.path.exists(DB):
    sys.exit(f"ABANDON : {DB} existe déjà (le supprimer pour reconstruire).")

debut = time.time()
conn = sqlite3.connect(DB)
conn.executescript(f"""
    PRAGMA page_size = 65536;       -- 64 ko/page : ~16x moins d'operations sur disque lent
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA cache_size = -8000000;   -- ~8 Go de cache en RAM (negatif = ko)
    ATTACH DATABASE '{DOSSIER}/vocabulaire.db' AS vocab;
    CREATE TABLE IF NOT EXISTS vocab.token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS unigram_staging (w1, date, n);
""")

# Vocabulaire monté en RAM : la boucle n'interroge plus la base pour un mot déjà
# connu, elle attribue les ids elle-meme et n'ecrit que les mots nouveaux.
ids = dict(conn.execute("SELECT word, id FROM vocab.token"))
prochain = max(ids.values(), default=0) + 1
acquis = len(ids)
print(f"[{media}] vocabulaire partagé au départ : {acquis} mots", flush=True)

if media == "le_monde":
    reader = pd.read_csv(CSV, usecols=["text", "year", "month", "day"],
                         chunksize=20_000, on_bad_lines="skip")
else:
    reader = pd.read_csv(CSV, usecols=["text", "date_published"],
                         chunksize=20_000, on_bad_lines="skip")

vus = set()          # mots employés par CE média (pour la copie locale de token)
n_articles = 0
n_rejets = 0

for i, chunk in enumerate(reader, start=1):
    brut = len(chunk)
    if media == "le_monde":
        chunk = chunk.dropna(subset=["text"])
        for c in ["year", "month", "day"]:   # coerce : entetes repetees, valeurs corrompues
            chunk[c] = pd.to_numeric(chunk[c], errors="coerce")
        chunk = chunk.dropna(subset=["year", "month", "day"]).astype(
            {"year": int, "month": int, "day": int})
        chunk = chunk.assign(
            date=chunk["year"] * 10000 + chunk["month"] * 100 + chunk["day"])
    else:
        chunk = chunk.dropna(subset=["text", "date_published"])
        # match strict AAAA-MM-JJ : ecarte les entetes repetees dans les archives
        chunk = chunk[chunk["date_published"].str.match(r"\d{4}-\d{2}-\d{2}", na=False)]
        chunk = chunk.assign(date=chunk["date_published"].str[:10]
                             .str.replace("-", "", regex=False).astype(int))
    # garde-fou sur les dates aberrantes (champs vides ou corrompus)
    chunk = chunk[chunk["date"].between(19000101, 20301231)]
    n_articles += len(chunk)
    n_rejets += brut - len(chunk)

    for date, group in chunk.groupby("date"):
        date = int(date)
        uni = Counter()
        for text in group["text"]:
            for tokens in phrases(text):
                uni.update(tokens)
        if not uni:
            continue

        nouveaux = [w for w in uni if w not in ids]
        for w in nouveaux:
            ids[w] = prochain
            prochain += 1
        if nouveaux:
            conn.executemany("INSERT INTO vocab.token(id, word) VALUES (?,?)",
                             [(ids[w], w) for w in nouveaux])
        conn.executemany("INSERT INTO unigram_staging VALUES (?,?,?)",
                         [(ids[w], date, c) for w, c in uni.items()])
        vus.update(uni)
    conn.commit()   # le vocabulaire nouveau est validé en même temps que les comptes

    ecoule = time.time() - debut
    print(f"[{media}] chunk {i} | {n_articles} articles | {len(vus)} mots du média "
          f"| +{len(ids) - acquis} mots au vocabulaire | {ecoule / 60:.1f} min "
          f"({n_articles / max(ecoule, 1):.0f} art/s)", flush=True)

print(f"[{media}] lecture finie : {n_articles} articles, {n_rejets} lignes écartées "
      f"(date ou contenu manquant), {time.time() - debut:.0f} s", flush=True)

# staging -> final : SUM(n) agrège les jours répartis sur plusieurs chunks
conn.executescript("""
    -- totaux journaliers (denominateur N_t des frequences relatives)
    CREATE TABLE IF NOT EXISTS total_unigram (date INTEGER, total INTEGER,
        PRIMARY KEY (date)) WITHOUT ROWID;
    INSERT INTO total_unigram SELECT date, SUM(n) FROM unigram_staging GROUP BY date;

    CREATE TABLE IF NOT EXISTS unigram (w1 INTEGER, date INTEGER, n INTEGER,
        PRIMARY KEY (w1, date)) WITHOUT ROWID;
    INSERT INTO unigram SELECT w1, date, SUM(n) FROM unigram_staging GROUP BY w1, date;
    DROP TABLE unigram_staging;

    CREATE TABLE IF NOT EXISTS token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
""")
# copie locale du vocabulaire : mêmes ids que la base partagée, mots de ce média
conn.executemany("INSERT INTO token(id, word) VALUES (?,?)",
                 [(ids[w], w) for w in vus])
conn.commit()

n_lignes = conn.execute("SELECT COUNT(*) FROM unigram").fetchone()[0]
jours = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM total_unigram").fetchone()
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("VACUUM")
conn.close()

print(f"FINI : {media}_1gram.db | {n_lignes} lignes unigram | {len(vus)} mots "
      f"| {jours[0]} jours ({jours[1]} -> {jours[2]}) "
      f"| {(time.time() - debut) / 60:.1f} min", flush=True)
