# Matrice jours x mots du CORPUS UNIFIE (reunion de tous les medias) — meme
# objet que masse.py, mais en agregeant les 36 bases au lieu d'en lire une.
# Sortie au format EXACT de vocab_series_<media>.npz : toute la suite (agreger,
# pics_masse, nms, fenetres_masse, pca, campagne) tourne dessus telle quelle
# avec media=unifie.
#
# Vocabulaire : le top-10 000 du Monde deja etabli (vocab_lemonde_top10000.csv),
# repris tel quel — memes mots, meme ordre. La PCA unifiee est donc directement
# comparable a celle du Monde, colonne par colonne. Les mots sont apparies par
# GRAPHIE EXACTE : la regle d'absorption des doublons OCR de masse.py visait les
# annees mal numerisees du Monde (avant 1990), hors de la periode traitee ici.
#
# Grille CALENDAIRE (tous les jours de la periode, pas les jours de parution),
# bornee a la derniere date reellement collectee ; un jour sans aucun article
# reste dans la grille avec N_t = 0, il est compte et affiche.
#
# Sorties dans <VOCAB_DIR>/ :
# - vocab_series_unifie.npz : X (jours x 10 000, int32), dates (YYYYMMDD),
#                             N (total du jour, tous medias), mots, cles
# - couverture_unifie.csv   : mot, total, jours_actifs, n_medias — ce que
#                             chaque mot du top du Monde devient sur l'union
# - N_par_media_unifie.csv  : date x media, pour la figure des bascules de
#                             panel (entrees et sorties de journaux)
# Usage (sur gallica) : python -m rupture.masse_unifie [debut] [fin]
import glob
import os
import sqlite3
import sys
import time

import numpy as np
import pandas as pd

DEBUT = int(sys.argv[1]) if len(sys.argv) > 1 else 20080101
FIN = int(sys.argv[2]) if len(sys.argv) > 2 else 20261231
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
CORPUS = f"{DOSSIER}/corpus"
VOCAB = f"{DOSSIER}/vocab_lemonde_top10000.csv"
PAS = 500           # ids par tranche de lecture (comme masse.py)
# Bases d'archives a ids LOCAUX (numerotation propre a chaque base, filtre > 10
# sur le total global du mot) : raccordees par le mot, comme les autres.
ARCHIVES = ("lemonde", "lefigaro", "lesechos", "mediapart")
debut = time.time()

bases = [(os.path.basename(f)[:-len("_1gram.db")], f)
         for f in sorted(glob.glob(f"{CORPUS}/*_1gram.db"))]
bases += [(m, f"{CORPUS}/{m}_ngram.db") for m in ARCHIVES]

# 1. Vocabulaire : le top du Monde, tel quel
v = pd.read_csv(VOCAB, dtype={"mot": str, "cle": str}, keep_default_na=False)
mots = v["mot"].to_numpy(str)
colonne = {m: j for j, m in enumerate(mots)}
print(f"{len(bases)} medias | vocabulaire : {len(mots)} mots du top du Monde "
      f"({os.path.basename(VOCAB)})", flush=True)

# 2. Grille calendaire, bornee aux dates reellement presentes
bornes = []
for media, db in bases:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    a, b = conn.execute("SELECT MIN(date), MAX(date) FROM total_unigram "
                        f"WHERE date BETWEEN {DEBUT} AND {FIN}").fetchone()
    conn.close()
    if a is None:
        print(f"  {media:28s} AUCUNE donnee sur la periode — ecarte", flush=True)
        continue
    bornes.append((media, db, a, b))
    print(f"  {media:28s} {a} -> {b}", flush=True)
bases = [(m, db) for m, db, _, _ in bornes]
dates = pd.date_range(str(DEBUT), str(max(b for _, _, _, b in bornes)), freq="D")
dates = dates.strftime("%Y%m%d").astype(np.int64).to_numpy()
X = np.zeros((len(dates), len(mots)), np.int32)
N = np.zeros(len(dates), np.int64)
N_media, presence = {}, np.zeros((len(bases), len(mots)), bool)
print(f"grille : {len(dates)} jours calendaires ({dates[0]} -> {dates[-1]}), "
      f"matrice {X.shape[0]} x {X.shape[1]} ({X.nbytes / 1e6:.0f} Mo)", flush=True)

# 3. Une passe par base : totaux du jour, puis comptes des mots du vocabulaire
for numero, (media, db) in enumerate(bases, start=1):
    t0 = time.time()
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    t = pd.read_sql_query("SELECT date, total FROM total_unigram "
                          f"WHERE date BETWEEN {DEBUT} AND {FIN}", conn)
    pos = np.searchsorted(dates, t["date"].to_numpy())
    ok = (pos < len(dates)) & (dates[np.clip(pos, 0, len(dates) - 1)]
                               == t["date"].to_numpy())
    serie = np.zeros(len(dates), np.int64)
    np.add.at(serie, pos[ok], t.loc[ok, "total"].to_numpy())
    N += serie
    N_media[media] = serie

    tok = pd.read_sql_query("SELECT id, word FROM token", conn)
    tok = tok[tok["word"].isin(colonne)].copy()
    if not len(tok):
        conn.close()
        print(f"[{numero}/{len(bases)}] {media} : aucun mot du vocabulaire, "
              f"seuls ses totaux N_t comptent", flush=True)
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
            f"({','.join(map(str, tranche))}) "
            f"AND date BETWEEN {DEBUT} AND {FIN}", conn)
        if len(df):
            p = np.searchsorted(dates, df["date"].to_numpy())
            bon = (p < len(dates)) & (dates[np.clip(p, 0, len(dates) - 1)]
                                      == df["date"].to_numpy())
            np.add.at(X, (p[bon], colmap[df.loc[bon, "w1"].to_numpy()]),
                      df.loc[bon, "n"].to_numpy())
            n_lignes += int(bon.sum())
    conn.close()
    print(f"[{numero}/{len(bases)}] {media} : {len(tok)}/{len(mots)} mots du "
          f"vocabulaire presents, {n_lignes / 1e6:.1f} M lignes, "
          f"{serie.sum() / 1e9:.2f} Md tokens ({int((serie > 0).sum())} jours "
          f"actifs) | {(time.time() - t0) / 60:.1f} min", flush=True)

# 4. Sorties + controles
ja = (X > 0).sum(axis=0)
totaux = X.sum(axis=0, dtype=np.int64)
np.savez_compressed(f"{DOSSIER}/vocab_series_unifie.npz",
                    X=X, dates=dates, N=N, mots=mots, cles=v["cle"].to_numpy(str))
pd.DataFrame({"mot": mots, "total": totaux, "jours_actifs": ja,
              "n_medias": presence.sum(axis=0)}
             ).to_csv(f"{DOSSIER}/couverture_unifie.csv", index=False)
pd.DataFrame(N_media, index=dates).rename_axis("date").to_csv(
    f"{DOSSIER}/N_par_media_unifie.csv")

muets = np.where(totaux == 0)[0]
print(f"grille : {int((N == 0).sum())} jour(s) a N_t = 0, mediane N_t = "
      f"{int(np.median(N[N > 0]))}, total {N.sum() / 1e9:.1f} Md tokens", flush=True)
print(f"vocabulaire : {len(muets)} mot(s) du top du Monde jamais vus sur la "
      f"periode{' : ' + ', '.join(mots[muets][:10]) if len(muets) else ''}", flush=True)
print(f"jours actifs : mediane {int(np.median(ja))}/{len(dates)}, "
      f"{int((ja == len(dates)).sum())} mots presents tous les jours", flush=True)
print(f"FINI : {len(mots)} mots x {len(dates)} jours -> vocab_series_unifie.npz "
      f"en {(time.time() - debut) / 60:.1f} min", flush=True)
