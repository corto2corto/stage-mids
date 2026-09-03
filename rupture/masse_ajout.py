# Complement de masse_unifie.py : n'extrait que les mots d'un vocabulaire qui
# MANQUENT a une matrice unifiee deja construite, et les accole a ses colonnes.
# Les colonnes existantes, la grille de dates et les totaux N sont repris tels
# quels ; seuls les nouveaux mots sont lus dans les 36 bases (quelques
# minutes, contre ~40 pour tout reextraire).
# Sortie au format de vocab_series_<media>.npz : la suite (agreger, pics_masse,
# nms, fenetres_masse) tourne dessus avec media=<sortie>.
# Sorties dans <VOCAB_DIR>/ :
# - vocab_series_<sortie>.npz : X (jours x tous les mots), dates, N, mots, cles
# - couverture_<sortie>.csv   : mot, total, jours_actifs, n_medias (nouveaux mots seuls)
# Usage (sur gallica) : python -m rupture.masse_ajout [vocab.csv] [base] [sortie]
#   defauts : vocab_etendu.csv, unifie, etendu
import glob
import os
import sqlite3
import sys
import time

import numpy as np
import pandas as pd

DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
CORPUS = f"{DOSSIER}/corpus"
VOCAB = f"{DOSSIER}/{sys.argv[1] if len(sys.argv) > 1 else 'vocab_etendu.csv'}"
BASE = sys.argv[2] if len(sys.argv) > 2 else "unifie"
SORTIE = sys.argv[3] if len(sys.argv) > 3 else "etendu"
PAS = 500
ARCHIVES = ("lemonde", "lefigaro", "lesechos", "mediapart")
debut = time.time()

d = np.load(f"{DOSSIER}/vocab_series_{BASE}.npz")
X0, dates, N = d["X"], d["dates"], d["N"]
DEBUT, FIN = int(dates[0]), int(dates[-1])
v = pd.read_csv(VOCAB, dtype={"mot": str, "cle": str}, keep_default_na=False)
v = v[~v["mot"].isin(set(d["mots"].astype(str)))]
mots = v["mot"].to_numpy(str)
colonne = {m: j for j, m in enumerate(mots)}
print(f"base {BASE} : {X0.shape[1]} mots x {len(dates)} jours ({DEBUT} -> {FIN}) ; "
      f"{len(mots)} mots a ajouter depuis {os.path.basename(VOCAB)}", flush=True)

bases = [(os.path.basename(f)[:-len("_1gram.db")], f)
         for f in sorted(glob.glob(f"{CORPUS}/*_1gram.db"))]
bases += [(m, f"{CORPUS}/{m}_ngram.db") for m in ARCHIVES]
X = np.zeros((len(dates), len(mots)), np.int32)
presence = np.zeros((len(bases), len(mots)), bool)

for numero, (media, db) in enumerate(bases, start=1):
    t0 = time.time()
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    tok = pd.read_sql_query("SELECT id, word FROM token", conn)
    tok = tok[tok["word"].isin(colonne)].copy()
    if not len(tok):
        conn.close()
        print(f"[{numero}/{len(bases)}] {media} : aucun des nouveaux mots", flush=True)
        continue
    tok["col"] = [colonne[w] for w in tok["word"]]
    colmap = np.full(int(tok["id"].max()) + 1, -1, np.int32)
    colmap[tok["id"].to_numpy()] = tok["col"].to_numpy()
    presence[numero - 1, tok["col"].to_numpy()] = True
    ids = np.sort(tok["id"].to_numpy())
    n_lignes = 0
    for i in range(0, len(ids), PAS):
        tranche = ids[i:i + PAS]
        df = pd.read_sql_query(
            "SELECT w1, date, n FROM unigram WHERE w1 IN "
            f"({','.join(map(str, tranche))}) AND date BETWEEN {DEBUT} AND {FIN}", conn)
        if len(df):
            p = np.searchsorted(dates, df["date"].to_numpy())
            bon = (p < len(dates)) & (dates[np.clip(p, 0, len(dates) - 1)]
                                      == df["date"].to_numpy())
            np.add.at(X, (p[bon], colmap[df.loc[bon, "w1"].to_numpy()]),
                      df.loc[bon, "n"].to_numpy())
            n_lignes += int(bon.sum())
    conn.close()
    print(f"[{numero}/{len(bases)}] {media} : {len(tok)}/{len(mots)} nouveaux mots "
          f"presents, {n_lignes / 1e6:.2f} M lignes | {time.time() - t0:.0f} s", flush=True)

ja = (X > 0).sum(axis=0)
totaux = X.sum(axis=0, dtype=np.int64)
np.savez_compressed(f"{DOSSIER}/vocab_series_{SORTIE}.npz",
                    X=np.hstack([X0, X]), dates=dates, N=N,
                    mots=np.concatenate([d["mots"].astype(str), mots]),
                    cles=np.concatenate([d["cles"].astype(str), v["cle"].to_numpy(str)]))
pd.DataFrame({"mot": mots, "total": totaux, "jours_actifs": ja,
              "n_medias": presence.sum(axis=0)}
             ).to_csv(f"{DOSSIER}/couverture_{SORTIE}.csv", index=False)
muets = np.where(totaux == 0)[0]
print(f"nouveaux mots : {len(muets)} jamais vu(s) sur la periode"
      f"{' : ' + ', '.join(mots[muets][:10]) if len(muets) else ''} ; "
      f"jours actifs mediane {int(np.median(ja))}/{len(dates)}", flush=True)
print(f"FINI : {X0.shape[1]} + {len(mots)} mots x {len(dates)} jours -> "
      f"vocab_series_{SORTIE}.npz en {(time.time() - debut) / 60:.1f} min", flush=True)
