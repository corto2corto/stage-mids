# Le Monde, blocs de 3 jours, fenetres +/-15 blocs : combien de fenetres
# survivent quand on durcit le seuil de surprise ET le plancher de tokens ?
# But : trouver une configuration assez petite pour une kernel PCA EXACTE
# (matrice de Gram N x N) tout en gardant des fenetres de meilleure qualite.
#
# Sur cette grille, un bloc agrege 3 jours de parution : la mediane est a
# 174 473 tokens et le minimum a 17 785, si bien qu'un plancher a 5 000
# (la valeur du journalier) n'ecarte rien. Les planchers testes sont donc
# cales sur les quantiles bas de la distribution des blocs.
# Usage : .venv/bin/python -m campagne_pca.scripts.kernel_qualite
import os
from pathlib import Path

import numpy as np
import pandas as pd

from rupture.nms import nms
from rupture.pca import nettoyer, normaliser

SCRIPTS = Path(__file__).resolve().parent
ICI = SCRIPTS.parent                    # campagne_pca/
DATA = ICI / "data"
DONNEES = Path(os.environ.get("VOCAB_DIR", DATA / "data_local"))
MEDIA, DEMI = "lemonde3j", 15
SEUILS = (5, 6)
PLANCHERS = (0, 65_000, 87_000, 120_918)      # 0, q5, q10, q25 des blocs

g = np.load(DONNEES / f"vocab_series_{MEDIA}.npz")
X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
position = {int(dt): i for i, dt in enumerate(grille_dates)}
colonne = {m: j for j, m in enumerate(g["mots"])}
pics = pd.read_csv(DONNEES / f"pics_{MEDIA}.csv")

print(f"{MEDIA}, fenetres +/-{DEMI} blocs (soit +/-{DEMI * 3} jours de parution)")
print(f"{'seuil':>5} {'plancher':>9} {'fenetres':>9} {'blocs interp.':>14} "
      f"{'fen. touchees':>14} {'Gram (Go)':>10}")
for seuil in SEUILS:
    p0 = pics[pics["surprise"] >= seuil].assign(pos=lambda x: x["date"].map(position))
    gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                     2 * DEMI + 1)[0]]
              for _, gr in p0.groupby("mot", sort=False)]
    p0 = p0.loc[np.concatenate(gardes)]
    pos, col = p0["pos"].to_numpy(), p0["mot"].map(colonne).to_numpy(int)
    complet = (pos - DEMI >= 0) & (pos + DEMI < len(grille_dates))
    pos, col = pos[complet], col[complet]
    lignes = pos[:, None] + np.arange(-DEMI, DEMI + 1)
    F0 = (1e5 * X[lignes, col[:, None]] / grille_N[lignes]).astype(np.float64)
    N_fen = grille_N[lignes]

    for plancher in PLANCHERS:
        F, n_interp, n_touchees = F0, 0, 0
        if plancher:
            F, _, n_interp, n_touchees = nettoyer(F0, N_fen, plancher, DEMI)
        Z, _ = normaliser(F, "z")
        n = len(Z)
        go = n * n * 8 / 1e9
        print(f"{seuil:>5} {plancher:>9,} {n:>9,} {n_interp:>14,} {n_touchees:>14,} "
              f"{go:>10.1f}".replace(",", " "))
