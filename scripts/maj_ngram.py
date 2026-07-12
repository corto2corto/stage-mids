# MAJ quotidienne des comptes ngram d'un média : lit le CSV produit par le
# scrapping (data/csv/<media>.csv), saute les articles déjà comptés (table
# maj_articles dans la base), et ajoute les comptes des nouveaux par paquets.
# Chaque paquet est validé en UNE transaction (comptes + totaux + ids) :
# relançable après un plantage sans double compte ni perte. L'API continue de
# servir pendant l'écriture (mode WAL des bases).
# Usage : python -m scripts.maj_ngram les_echos /chemin/vers/la/base_ngram.db
# (chemin de base obligatoire — garde-fou : les bases de prod sont encore
#  filtrées, la MAJ ne doit viser que les bases sans filtre)

import os
import sqlite3
import sys
import time
from collections import Counter

import pandas as pd

from scripts.tokenisation import phrases

media = sys.argv[1]
base = sys.argv[2]
DATA_DIR = os.environ.get("STAGE_DATA_DIR", "/data/elias/stage-mids/data")
chemin_csv = f"{DATA_DIR}/csv/{media}.csv"

debut = time.time()
conn = sqlite3.connect(base)
conn.execute("PRAGMA busy_timeout = 30000")
conn.execute("PRAGMA synchronous = NORMAL")
conn.execute("PRAGMA cache_size = -2000000")  # ~2 Go : les upserts touchent des pages dispersées
conn.execute("CREATE TABLE IF NOT EXISTS maj_articles (id INTEGER PRIMARY KEY)")
deja = {r[0] for r in conn.execute("SELECT id FROM maj_articles")}

total_articles = 0
ajout_uni = ajout_bi = ajout_tri = 0  # occurrences ajoutées (contrôle contre les totaux)
for chunk in pd.read_csv(chemin_csv, usecols=["id", "date", "titre", "contenu"],
                         chunksize=10_000):
    d = pd.to_datetime(chunk["date"].str[:10], format="%Y-%m-%d", errors="coerce")
    chunk = chunk.assign(jour=d.dt.strftime("%Y%m%d"),
                         txt=chunk["titre"].fillna("") + "\n" + chunk["contenu"].fillna(""))
    chunk = chunk.dropna(subset=["id", "jour"]).astype({"id": int, "jour": int})
    chunk = chunk.drop_duplicates(subset="id")
    chunk = chunk[~chunk["id"].isin(deja)]
    if chunk.empty:
        continue

    # comptes du paquet — clés : (mot(s), jour)
    uni, bi, tri = Counter(), Counter(), Counter()
    for jour, group in chunk.groupby("jour"):
        jour = int(jour)
        for texte in group["txt"]:
            for tokens in phrases(texte):
                uni.update((w, jour) for w in tokens)
                bi.update((a, b, jour) for a, b in zip(tokens, tokens[1:]))
                tri.update((a, b, c, jour) for a, b, c in zip(tokens, tokens[1:], tokens[2:]))

    # totaux journaliers du paquet
    tot_uni, tot_bi, tot_tri = Counter(), Counter(), Counter()
    for (_, j), n in uni.items():
        tot_uni[j] += n
    for (*_, j), n in bi.items():
        tot_bi[j] += n
    for (*_, j), n in tri.items():
        tot_tri[j] += n

    # UNE transaction par paquet : comptes + totaux + ids, tout ou rien
    with conn:
        mots = list({w for (w, _) in uni})
        conn.executemany("INSERT OR IGNORE INTO token(word) VALUES (?)",
                         [(w,) for w in mots])
        ids = {}
        for i in range(0, len(mots), 30_000):  # limite SQLite sur le nombre de « ? »
            tranche = mots[i:i + 30_000]
            ids.update(conn.execute(
                f"SELECT word, id FROM token WHERE word IN ({','.join('?' * len(tranche))})",
                tranche))
        conn.executemany(
            "INSERT INTO unigram VALUES (?,?,?) "
            "ON CONFLICT(w1, date) DO UPDATE SET n = n + excluded.n",
            [(ids[w], j, n) for (w, j), n in uni.items()])
        conn.executemany(
            "INSERT INTO bigram VALUES (?,?,?,?) "
            "ON CONFLICT(w1, w2, date) DO UPDATE SET n = n + excluded.n",
            [(ids[a], ids[b], j, n) for (a, b, j), n in bi.items()])
        conn.executemany(
            "INSERT INTO trigram VALUES (?,?,?,?,?) "
            "ON CONFLICT(w1, w2, w3, date) DO UPDATE SET n = n + excluded.n",
            [(ids[a], ids[b], ids[c], j, n) for (a, b, c, j), n in tri.items()])
        conn.executemany(
            "INSERT INTO total_unigram VALUES (?,?) "
            "ON CONFLICT(date) DO UPDATE SET total = total + excluded.total",
            list(tot_uni.items()))
        conn.executemany(
            "INSERT INTO total_bigram VALUES (?,?) "
            "ON CONFLICT(date) DO UPDATE SET total = total + excluded.total",
            list(tot_bi.items()))
        conn.executemany(
            "INSERT INTO total_trigram VALUES (?,?) "
            "ON CONFLICT(date) DO UPDATE SET total = total + excluded.total",
            list(tot_tri.items()))
        conn.executemany("INSERT INTO maj_articles VALUES (?)",
                         [(int(i),) for i in chunk["id"]])

    deja.update(chunk["id"])
    total_articles += len(chunk)
    ajout_uni += sum(tot_uni.values())
    ajout_bi += sum(tot_bi.values())
    ajout_tri += sum(tot_tri.values())
    print(f"paquet : {len(chunk)} articles ({chunk['jour'].min()}–{chunk['jour'].max()}), "
          f"cumul {total_articles}, {time.time() - debut:.0f} s", flush=True)

conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # évite que le fichier -wal ne gonfle
conn.close()
print(f"--- FINI : {total_articles} articles nouveaux en {time.time() - debut:.0f} s ; "
      f"occurrences ajoutées : {ajout_uni:,} uni / {ajout_bi:,} bi / {ajout_tri:,} tri ---",
      flush=True)
