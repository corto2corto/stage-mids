# Kernel PCA COMPLETE d'une configuration hebdomadaire de configurations_hebdo.qmd :
# toutes les fenetres (pas d'echantillon) et TOUT le spectre (les N valeurs propres
# de la Gram centree, pas les 30 premieres). C'est ce que la grille a la semaine rend
# possible : la Gram N x N pese 0,24 Go a Mediapart et 6,1 Go au Monde, contre 120 Go
# en journalier.
#
# Chaine amont identique aux autres configurations (figures_lib.charger) :
# pics au-dessus du seuil -> NMS de portee 2d+1 -> fenetres completes ->
# f = 1e5 * X / N -> z-score le long de chaque fenetre. La PCA lineaire est calculee
# sur la MEME matrice, pour la comparaison.
#
# Diagonalisation complete : la somme des valeurs propres vaut alors exactement la
# trace de la Gram centree (trace(K) - somme(K)/N), donc la part de variance est
# exacte par construction et le rapport somme(lam)/trace sert de controle.
#
# Memoire : une seule matrice N x N vivante. Le noyau est monte en place (produit
# scalaire puis exp sur le meme tableau) et LAPACK travaille dessus sans copie —
# K etant symetrique, K.T est une vue Fortran de la meme memoire.
# Usage : VOCAB_DIR=... .venv/bin/python -m campagne_pca.scripts.kernel_hebdo <media> [--pics _s3]
import argparse
import os
import time

import numpy as np
import pandas as pd
from scipy.linalg import eigh

from rupture.nms import nms
from rupture.pca import normaliser, pca

ap = argparse.ArgumentParser()
ap.add_argument("media")
ap.add_argument("--demi", type=int, default=10, help="demi-largeur en blocs (10 = +/-10 semaines)")
ap.add_argument("--seuil", type=float, default=4.0, help="seuil de surprise")
ap.add_argument("--pics", default="", help="suffixe du fichier pics (ex. _s3)")
a = ap.parse_args()

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ICI = os.path.dirname(SCRIPTS)          # campagne_pca/
DATA = os.path.join(ICI, "data")
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(DATA, "data_local"))
SORTIE = os.path.join(DATA, "kernel_spectres")
os.makedirs(SORTIE, exist_ok=True)
MEDIA, DEMI, SEUIL = a.media, a.demi, a.seuil

# --- chaine : pics filtres -> NMS -> fenetres -> z-score
g = np.load(f"{DONNEES}/vocab_series_{MEDIA}.npz")
X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
position = {int(dt): i for i, dt in enumerate(grille_dates)}
colonne = {m: j for j, m in enumerate(g["mots"])}

p = pd.read_csv(f"{DONNEES}/pics_{MEDIA}{a.pics}.csv")
p = p[p["surprise"] >= SEUIL].assign(pos=lambda x: x["date"].map(position))
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
del X, F, lignes

_, var_lin, _ = pca(Z)
GAMMAS = (0.01, 1 / D, 0.1)
print(f"{MEDIA} : {n:,}".replace(",", " ")
      + f" fenetres x {D} blocs (+/-{DEMI}, seuil {SEUIL:g})", flush=True)
print(f"  Gram N x N : {n * n * 8 / 1e9:.2f} Go", flush=True)
print(f"  PCA lineaire  : comp1 {var_lin[0] * 100:5.2f} %, cum6 {var_lin[:6].sum() * 100:5.2f} %",
      flush=True)

for gamma in GAMMAS:
    t0 = time.time()
    # noyau RBF monte en place : K = exp(-gamma * ||zi - zj||^2)
    K = Z @ Z.T
    carres = np.einsum("ij,ij->i", Z, Z)
    K *= -2.0
    K += carres[:, None]
    K += carres[None, :]
    np.maximum(K, 0, out=K)
    K *= -gamma
    np.exp(K, out=K)

    total = np.trace(K) - K.sum() / n          # trace de la Gram centree
    K -= K.mean(axis=0, keepdims=True)         # double centrage, en place
    K -= K.mean(axis=1, keepdims=True)
    t1 = time.time()
    # K symetrique -> K.T est la meme memoire vue en Fortran : LAPACK sans copie
    lam = eigh(K.T, eigvals_only=True, overwrite_a=True, check_finite=False)[::-1]
    del K

    v = np.clip(lam, 0, None) / total
    fichier = f"{SORTIE}/kernel_{MEDIA}_d{DEMI}_s{SEUIL:g}_g{gamma:.6g}.npz"
    np.savez_compressed(fichier, lam=lam, total=total, var_lin=var_lin,
                        n=n, D=D, gamma=gamma, demi=DEMI, seuil=SEUIL)
    print(f"  RBF gamma={gamma:<8.4g} : comp1 {v[0] * 100:5.2f} %, "
          f"cum6 {v[:6].sum() * 100:5.2f} %, cum{D - 1} {v[:D - 1].sum() * 100:5.2f} % "
          f"| somme/trace {lam.sum() / total:.6f} | noyau {t1 - t0:.0f} s, "
          f"diagonalisation {time.time() - t1:.0f} s", flush=True)
    print(f"    -> {os.path.relpath(fichier, ICI)}", flush=True)
