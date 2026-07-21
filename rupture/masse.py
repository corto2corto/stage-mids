# Extraction en masse des series du vocabulaire (phase 3, dataset de sauts).
# Construit la matrice dense jours x mots du top-K vocabulaire unigram d'un media,
# avec fusion EXACTE des graphies accent/sans accent (somme jour par jour — le
# recensement ne donnait qu'une borne basse, max des variantes). Une seule passe
# sur unigram par tranches d'ids (PK (w1, date)), pas une boucle sur serie().
# Les candidats sont le top 2K de la borne basse ; le classement final utilise
# les jours actifs exacts, la marge de la coupe est loggee.
#
# Usage (sur gallica) : python -m rupture.masse [media] [K]
# Sorties dans data/ :
# - vocab_series_<media>.npz : X (jours x K, int32), dates (YYYYMMDD), N (total
#   du jour), mots (graphie dominante), cles (graphie desaccentuee)
# - vocab_<media>_top<K>.csv : mot, cle, jours_actifs, total
import sqlite3
import sys
import time
import unicodedata

import numpy as np
import pandas as pd

from scripts.tokenisation import MOTS_OUTILS

media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
DOSSIER = "/data/elias/stage-mids/data"
PAS = 500  # ids par tranche
debut = time.time()

# 1. Candidats depuis le recensement : exclusions puis top 2K par borne basse
v = pd.read_csv(f"{DOSSIER}/vocab_{media}_unigram.csv", dtype={"mot": str}, keep_default_na=False)
v = v[~v["mot"].isin(set(MOTS_OUTILS))]
v = v[~v["mot"].str.match(r"[0-9]")]
v = v[v["mot"].str.len() > 1]
v["cle"] = [unicodedata.normalize("NFD", m).encode("ascii", "ignore").decode() for m in v["mot"]]
borne = v.groupby("cle")["jours_actifs"].max().sort_values(ascending=False)
candidats = borne.head(2 * K).index
v = v[v["cle"].isin(set(candidats))]
dominante = v.sort_values("total", ascending=False).groupby("cle")["mot"].first()
totaux = v.groupby("cle")["total"].sum()
print(f"candidats : {len(candidats)} cles ({len(v)} graphies), "
      f"borne basse du dernier : {int(borne.iloc[len(candidats) - 1])} jours", flush=True)

# 2. ids des graphies candidates (la table token est petite)
conn = sqlite3.connect(f"file:{DOSSIER}/corpus/{media}_ngram.db?mode=ro", uri=True)
tok = pd.read_sql_query("SELECT id, word FROM token", conn)
tok = tok[tok["word"].isin(set(v["mot"]))]
col_de_cle = {c: i for i, c in enumerate(candidats)}
mot2cle = dict(zip(v["mot"], v["cle"]))
tok["col"] = [col_de_cle[mot2cle[w]] for w in tok["word"]]
colmap = np.full(int(tok["id"].max()) + 1, -1, np.int32)
colmap[tok["id"].to_numpy()] = tok["col"].to_numpy()
ids = np.sort(tok["id"].to_numpy())
print(f"{len(ids)} ids de tokens a lire", flush=True)

# 3. Axe temps (zeros reinjectes par construction : toutes les dates du corpus)
t = pd.read_sql_query("SELECT date, total FROM total_unigram ORDER BY date", conn)
dates = t["date"].to_numpy(np.int64)
N = t["total"].to_numpy(np.int64)

# 4. Une passe sur unigram, tranches d'ids, cumul dans la matrice dense
X = np.zeros((len(dates), len(candidats)), np.int32)
n_lignes = 0
n_tranches = (len(ids) - 1) // PAS + 1
for i in range(0, len(ids), PAS):
    tranche = ids[i:i + PAS]
    df = pd.read_sql_query("SELECT w1, date, n FROM unigram WHERE w1 IN "
                           f"({','.join(map(str, tranche))})", conn)
    lignes = np.searchsorted(dates, df["date"].to_numpy())
    np.add.at(X, (lignes, colmap[df["w1"].to_numpy()]), df["n"].to_numpy())
    n_lignes += len(df)
    print(f"[{i // PAS + 1}/{n_tranches}] cumul {n_lignes / 1e6:.0f} M lignes, "
          f"{time.time() - debut:.0f} s", flush=True)

# 5. Classement exact et coupe au rang K
ja = (X > 0).sum(axis=0)
ordre = np.argsort(-ja, kind="stable")[:K]
coupe = int(ja[ordre[-1]])
print(f"coupe exacte au rang {K} : {coupe} jours actifs ; un exclu des candidats "
      f"ne peut depasser ~2 x {int(borne.iloc[len(candidats) - 1])} = "
      f"{2 * int(borne.iloc[len(candidats) - 1])} (marge ok si < {coupe})", flush=True)

# 6. Sorties
cles_f = candidats[ordre].to_numpy().astype(str)
mots_f = dominante[cles_f].to_numpy().astype(str)
np.savez_compressed(f"{DOSSIER}/vocab_series_{media}.npz",
                    X=X[:, ordre], dates=dates, N=N, mots=mots_f, cles=cles_f)
pd.DataFrame({"mot": mots_f, "cle": cles_f, "jours_actifs": ja[ordre],
              "total": totaux[cles_f].to_numpy()}
             ).to_csv(f"{DOSSIER}/vocab_{media}_top{K}.csv", index=False)
print(f"FINI : {K} mots x {len(dates)} jours -> vocab_series_{media}.npz "
      f"en {(time.time() - debut) / 60:.1f} min", flush=True)
