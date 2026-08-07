# Kernel PCA exacte sur UNE configuration : Le Monde, blocs de 3 jours,
# fenetres +/-15 blocs, seuil de surprise 6 (14 102 fenetres, sans nettoyage
# donc sans bloc interpole). Assez petite pour que la matrice de Gram tienne
# en memoire (1,6 Go), contrairement au journalier (120 Go).
#
# On ne calcule que les 30 premieres valeurs propres (Lanczos) : la variance
# totale, elle, s'obtient directement par la trace de la Gram centree
# (trace(K) - somme(K)/N), donc la part de variance reste exacte.
# Usage : .venv/bin/python -m campagne_pca.kernel_exact
import os
import time

import numpy as np
import pandas as pd
from scipy.sparse.linalg import eigsh
from sklearn.metrics.pairwise import rbf_kernel

from rupture.nms import nms
from rupture.pca import normaliser, pca

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
MEDIA, DEMI, SEUIL = "lemonde3j", 15, 6
GAMMAS = (0.01, 0.0323, 0.1)                 # 0.0323 = 1/D

g = np.load(f"{DONNEES}/vocab_series_{MEDIA}.npz")
X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
position = {int(dt): i for i, dt in enumerate(grille_dates)}
colonne = {m: j for j, m in enumerate(g["mots"])}
pics = pd.read_csv(f"{DONNEES}/pics_{MEDIA}.csv")

p = pics[pics["surprise"] >= SEUIL].assign(pos=lambda x: x["date"].map(position))
gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                 2 * DEMI + 1)[0]]
          for _, gr in p.groupby("mot", sort=False)]
p = p.loc[np.concatenate(gardes)]
pos, col = p["pos"].to_numpy(), p["mot"].map(colonne).to_numpy(int)
complet = (pos - DEMI >= 0) & (pos + DEMI < len(grille_dates))
pos, col = pos[complet], col[complet]
lignes = pos[:, None] + np.arange(-DEMI, DEMI + 1)
F = (1e5 * X[lignes, col[:, None]] / grille_N[lignes]).astype(np.float64)
Z, _ = normaliser(F, "z")
n, D = Z.shape
rang = D - 1

_, var_lin, _ = pca(Z)
print(f"{MEDIA} seuil {SEUIL} : {n:,} fenetres x {D} blocs".replace(",", " "), flush=True)
print(f"  PCA lineaire       : comp1 {var_lin[0] * 100:5.2f} %, "
      f"cum6 {var_lin[:6].sum() * 100:5.2f} %", flush=True)

for gamma in GAMMAS:
    t0 = time.time()
    K = rbf_kernel(Z, gamma=gamma)
    total = np.trace(K) - K.sum() / n          # variance totale = trace de la Gram centree
    moy_l = K.mean(axis=0, keepdims=True)
    K -= moy_l
    K -= K.mean(axis=1, keepdims=True)
    lam = eigsh(K, k=rang, which="LA", return_eigenvectors=False)[::-1]
    del K
    v = np.clip(lam, 0, None) / total
    print(f"  RBF gamma={gamma:<6.4g} : comp1 {v[0] * 100:5.2f} %, "
          f"cum6 {v[:6].sum() * 100:5.2f} %  | les {rang} premieres pesent "
          f"{v.sum() * 100:5.1f} % du total | {time.time() - t0:.0f} s", flush=True)
