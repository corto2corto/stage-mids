# Comptes BIGRAMMES d'un média du pipeline, par jour, dans <media>_2gram.db.
# Même mécanique que ngram_1gram.py (vocabulaire PARTAGÉ dans vocabulaire.db,
# constructions SÉQUENTIELLES, pas de filtre d'occurrences), avec deux écarts :
# - stdlib seule (csv, pas pandas) : le script tourne aussi sur gram, où rien
#   n'est installé hors la bibliothèque standard ;
# - chemins surchargeables (NGRAM_DIR, CSV_DIR) : gallica par défaut, gram via env.
# Les bigrammes ne franchissent pas les phrases (tokenisation.phrases).
#
# Usage : python -m scripts.ngram_2gram <media>
# Sur gram : NGRAM_DIR=/opt/bazoulay/stage-mids/data CSV_DIR=/opt/bazoulay/stage-mids/data/csv \
#            python -m scripts.ngram_2gram <media>

import os

DOSSIER = os.environ.get("NGRAM_DIR", "/data/elias/stage-mids/data/corpus")
CSV_DIR = os.environ.get("CSV_DIR", "/data/elias/stage-mids/data/csv")
TMPDIR = os.environ.get("SQLITE_TMPDIR", f"{DOSSIER}/../sqlite_tmp")
os.environ["SQLITE_TMPDIR"] = TMPDIR   # gros temp du tri final, pas /tmp

import csv
import sqlite3
import sys
import time
from collections import Counter

from scripts.tokenisation import phrases

media = sys.argv[1]
CSV = f"{CSV_DIR}/{media}.csv"
DB = f"{DOSSIER}/{media}_2gram.db"
CHUNK = int(os.environ.get("NGRAM_CHUNK", 20_000))   # articles entre deux flushs

os.makedirs(TMPDIR, exist_ok=True)
if os.path.exists(DB):
    sys.exit(f"ABANDON : {DB} existe déjà (le supprimer pour reconstruire).")

csv.field_size_limit(100_000_000)   # articles longs : la limite par défaut (128 ko) rejette
debut = time.time()
conn = sqlite3.connect(DB)
conn.executescript(f"""
    PRAGMA page_size = 65536;
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA cache_size = -4000000;   -- ~4 Go : gram est partagé, on reste poli
    ATTACH DATABASE '{DOSSIER}/vocabulaire.db' AS vocab;
    CREATE TABLE IF NOT EXISTS vocab.token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
    CREATE TABLE IF NOT EXISTS bigram_staging (w1, w2, date, n);
""")

ids = dict(conn.execute("SELECT word, id FROM vocab.token"))
prochain = max(ids.values(), default=0) + 1
acquis = len(ids)
print(f"[{media}] vocabulaire partagé au départ : {acquis} mots", flush=True)

vus = set()          # mots employés par CE média (pour la copie locale de token)
n_articles = 0
n_rejets = 0
n_chunk = 0
jours = {}           # date -> Counter des bigrammes du chunk courant


def flush():
    """Écrit les compteurs du chunk en staging (+ mots nouveaux au vocabulaire)."""
    global jours
    for date, big in jours.items():
        nouveaux = {w for paire in big for w in paire if w not in ids}
        for w in nouveaux:
            ids[w] = prochain_id()
        if nouveaux:
            conn.executemany("INSERT INTO vocab.token(id, word) VALUES (?,?)",
                             [(ids[w], w) for w in nouveaux])
        conn.executemany("INSERT INTO bigram_staging VALUES (?,?,?,?)",
                         [(ids[a], ids[b], date, c) for (a, b), c in big.items()])
        for a, b in big:
            vus.add(a)
            vus.add(b)
    conn.commit()
    jours = {}


def prochain_id():
    global prochain
    prochain += 1
    return prochain - 1


with open(CSV, newline="") as f:
    lecteur = csv.DictReader(f)
    while True:
        try:
            ligne = next(lecteur)
        except StopIteration:
            break
        except csv.Error:
            n_rejets += 1
            continue
        date, contenu = ligne.get("date") or "", ligne.get("contenu") or ""
        if len(date) < 10 or not contenu:
            n_rejets += 1
            continue
        date = date[:10].replace("-", "")
        if not date.isdigit() or not 19000101 <= int(date) <= 20301231:
            n_rejets += 1
            continue
        date = int(date)

        big = jours.setdefault(date, Counter())
        for tokens in phrases(contenu):
            big.update(zip(tokens, tokens[1:]))
        n_articles += 1

        if n_articles % CHUNK == 0:
            n_chunk += 1
            flush()
            ecoule = time.time() - debut
            print(f"[{media}] chunk {n_chunk} | {n_articles} articles | {len(vus)} mots du média "
                  f"| +{len(ids) - acquis} mots au vocabulaire | {ecoule / 60:.1f} min "
                  f"({n_articles / max(ecoule, 1):.0f} art/s)", flush=True)

flush()
print(f"[{media}] lecture finie : {n_articles} articles, {n_rejets} lignes écartées "
      f"(date ou contenu manquant), {time.time() - debut:.0f} s", flush=True)

# staging -> final : SUM(n) agrège les jours répartis sur plusieurs chunks
conn.executescript("""
    CREATE TABLE IF NOT EXISTS total_bigram (date INTEGER, total INTEGER,
        PRIMARY KEY (date)) WITHOUT ROWID;
    INSERT INTO total_bigram SELECT date, SUM(n) FROM bigram_staging GROUP BY date;

    CREATE TABLE IF NOT EXISTS bigram (w1 INTEGER, w2 INTEGER, date INTEGER, n INTEGER,
        PRIMARY KEY (w1, w2, date)) WITHOUT ROWID;
    INSERT INTO bigram SELECT w1, w2, date, SUM(n) FROM bigram_staging GROUP BY w1, w2, date;
    DROP TABLE bigram_staging;

    CREATE TABLE IF NOT EXISTS token (id INTEGER PRIMARY KEY, word TEXT UNIQUE);
""")
conn.executemany("INSERT INTO token(id, word) VALUES (?,?)",
                 [(ids[w], w) for w in vus])
conn.commit()

n_lignes = conn.execute("SELECT COUNT(*) FROM bigram").fetchone()[0]
njours = conn.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM total_bigram").fetchone()
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("VACUUM")
conn.close()

print(f"FINI : {media}_2gram.db | {n_lignes} lignes bigram | {len(vus)} mots "
      f"| {njours[0]} jours ({njours[1]} -> {njours[2]}) "
      f"| {(time.time() - debut) / 60:.1f} min", flush=True)
