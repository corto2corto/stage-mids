# Fenetres +/-15 autour des pics gardes par le NMS (pics_unifie_bnb_nms.csv ou
# pics_unifie3j_bnb_nms.csv, pics inchanges), decoupees dans la serie corrigee
# f' = f - S (S = composante saisonniere de saison_<tag>.npz). Pour les blocs de
# 3 jours, la correction est agregee comme les comptes (S moyenne ponderee par
# N_t sur les 3 jours), sur la grille de rupture/agreger.py.
# Sortie : campagne_pca/data/pics_desaison/fenetres_<tag><pas>j.npz, meme schema
# que fenetres_unifie.npz + S_pic (correction au jour du pic).
# Usage : .venv/bin/python -m campagne_pca.desaison.scripts.fenetres_desaison <tag> [pas]
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

DEMI = 15
tag = sys.argv[1]
pas = int(sys.argv[2]) if len(sys.argv) > 2 else 1
DATA = Path(__file__).resolve().parents[2] / "data"

debut = time.time()
d = np.load(DATA / "data_local" / "vocab_series_unifie.npz")
S = np.load(DATA / "data_local" / f"saison_{tag}.npz")["S"]
X, N, dates, mots = d["X"], d["N"], d["dates"], d["mots"]
if pas > 1:                                       # agregation identique a rupture/agreger.py
    n = len(dates) // pas * pas
    SN = (S[:n] * N[:n, None]).reshape(-1, pas, S.shape[1]).sum(axis=1)
    X = X[:n].reshape(-1, pas, X.shape[1]).sum(axis=1, dtype=np.int64)
    N = N[:n].reshape(-1, pas).sum(axis=1)
    S = SN / N[:, None]
    dates = dates[:n].reshape(-1, pas)[:, pas // 2]
Fc = (1e5 * X / N[:, None] - S).astype(np.float32)   # serie corrigee

csv = "pics_unifie_bnb_nms.csv" if pas == 1 else f"pics_unifie{pas}j_bnb_nms.csv"
pics = pd.read_csv(DATA / "pics_unifie" / csv)
pics = pics[pics["supprime_nms"] == 0].reset_index(drop=True)
position = {int(dt): i for i, dt in enumerate(dates)}
colonne = {m: j for j, m in enumerate(mots)}
pos = pics["date"].map(position).to_numpy()
col = pics["mot"].map(colonne).to_numpy()
complet = (pos - DEMI >= 0) & (pos + DEMI < len(dates))
pics, pos, col = pics[complet].reset_index(drop=True), pos[complet], col[complet]
idx = pos[:, None] + np.arange(-DEMI, DEMI + 1)
fen = Fc[idx, col[:, None]]

sortie = DATA / "pics_desaison" / f"fenetres_{tag}{pas}j.npz"
np.savez_compressed(sortie, fenetres=fen, mot=pics["mot"].to_numpy().astype(str),
                    date=pics["date"].to_numpy().astype(np.int32),
                    X_t=pics["X_t"].to_numpy().astype(np.int32), N_t=pics["N_t"].to_numpy(),
                    f_t=pics["f_t"].to_numpy().astype(np.float32),
                    p_t=pics["p_t"].to_numpy(), surprise=pics["surprise"].to_numpy().astype(np.float32),
                    S_pic=S[pos, col].astype(np.float32))
print(f"{tag} pas={pas} : {len(pics)} fenetres ({int((~complet).sum())} pics de bord ecartes) "
      f"-> {sortie.name} en {time.time() - debut:.0f} s")
