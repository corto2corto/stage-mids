# Kernel PCA a spectre entier + projections, sur une grille de gamma calee sur
# l'echelle REELLE des distances entre fenetres (heuristique de la mediane) et
# non plus sur une convention.
#
# gamma_med = 1 / (2 * mediane(||zi - zj||^2)), mediane estimee sur un tirage de
# paires (kernel_mediane.py mesure 16,75 au Figaro, 14,44 aux Echos, 9,98 a
# Mediapart : les fenetres se ressemblent bien plus que ne le voudrait
# l'hypothese "decorrelees", qui donnerait 2D = 42).
# La grille balaie gamma_med x [0.1 ... 30] : le bas tend vers la PCA lineaire,
# le haut va chercher le regime de degenerescence ou la Gram tend vers
# l'identite et le spectre s'aplatit.
#
# Deux sorties par gamma, la seconde etant ce que kernel_hebdo.py ne donnait pas :
#   - spectre entier (les N valeurs propres), pour la part de variance exacte
#   - les N_VEC premiers vecteurs propres -> projections des fenetres, de quoi
#     tracer le plan des deux premieres composantes comme sur une kernel PCA
#     classique. On ne demande pas les N vecteurs : au Figaro la matrice
#     complete pesserait 1 Go pour rien, 50 colonnes suffisent largement.
# Le Monde est hors perimetre ici (27 707 fenetres) : trop lourd des qu'on
# demande des vecteurs propres, son spectre entier est deja acquis.
# Usage : VOCAB_DIR=... .venv/bin/python -m campagne_pca.kernel_grille <media> --pics _s3
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
ap.add_argument("--demi", type=int, default=10)
ap.add_argument("--seuil", type=float, default=4.0)
ap.add_argument("--pics", default="")
ap.add_argument("--n_vec", type=int, default=50, help="vecteurs propres gardes")
ap.add_argument("--paires", type=int, default=4_000_000, help="paires tirees pour la mediane")
ap.add_argument("--mults", default="", help="sous-ensemble de multiplicateurs, "
                 "separes par des virgules (ex. '1' pour calibrer sur gamma_med "
                 "seul avant de lancer les 8) ; vide = les 8 par defaut")
a = ap.parse_args()

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
SORTIE = os.path.join(ICI, "kernel_spectres")
os.makedirs(SORTIE, exist_ok=True)
MEDIA, DEMI, SEUIL, N_VEC = a.media, a.demi, a.seuil, a.n_vec
MULTIPLES = tuple(float(m) for m in a.mults.split(",")) if a.mults else \
    (0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 10.0, 30.0)

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
Z, garde_z = normaliser(F, "z")   # les fenetres plates sont ecartees : on suit les indices
p = p.iloc[garde_z]
n, D = Z.shape
del X, F, lignes

# --- echelle reelle des distances -> gamma median
rng = np.random.default_rng(0)
i = rng.integers(0, n, a.paires)
j = rng.integers(0, n, a.paires)
i, j = i[i != j], j[i != j]
d2 = np.einsum("ij,ij->i", Z[i] - Z[j], Z[i] - Z[j])
mediane = float(np.median(d2))
gamma_med = 1.0 / (2.0 * mediane)
del d2, i, j

_, var_lin, _ = pca(Z)
n_vec = min(N_VEC, n)
print(f"{MEDIA} : {n:,}".replace(",", " ")
      + f" fenetres x {D} blocs (+/-{DEMI}, seuil {SEUIL:g})", flush=True)
print(f"  mediane d^2 = {mediane:.3f} -> gamma_med = {gamma_med:.5f} "
      f"| Gram {n * n * 8 / 1e9:.2f} Go, {n_vec} vecteurs propres gardes", flush=True)
print(f"  PCA lineaire  : comp1 {var_lin[0] * 100:5.2f} %, cum6 {var_lin[:6].sum() * 100:5.2f} %",
      flush=True)

for mult in MULTIPLES:
    gamma = gamma_med * mult
    t0 = time.time()
    K = Z @ Z.T
    carres = np.einsum("ij,ij->i", Z, Z)
    K *= -2.0
    K += carres[:, None]
    K += carres[None, :]
    np.maximum(K, 0, out=K)
    K *= -gamma
    np.exp(K, out=K)

    total = np.trace(K) - K.sum() / n           # trace de la Gram centree
    K -= K.mean(axis=0, keepdims=True)          # double centrage, en place
    K -= K.mean(axis=1, keepdims=True)
    # DEUX diagonalisations, et c'est necessaire : subset_by_index ne rend que
    # les valeurs propres du sous-ensemble demande, pas le spectre entier. Les
    # fusionner ferait retomber dans le piege du denominateur tronque (le
    # controle somme/trace tombait a 0,12 au lieu de 1). Premier appel pour le
    # spectre complet, second pour les seuls vecteurs propres utiles.
    #
    # Le second appel domine tres largement le temps : demander des vecteurs
    # propres fait quitter le chemin rapide de LAPACK (dsterf, valeurs propres
    # seules) pour un algorithme bien plus lourd. Mesure a n = 5 483 : 8 s pour
    # le spectre entier, 773 s pour 50 vecteurs. Le cout monte en N^3, d'ou des
    # heures au Figaro — c'est assume, le calcul tourne en tache de fond.
    # Chaque appel ecrase sa matrice (overwrite_a) : la Gram est donc remontee
    # entre les deux, ce qui coute quelques secondes contre une copie de N x N.
    t1 = time.time()
    lam = eigh(K.T, eigvals_only=True, overwrite_a=True, check_finite=False)[::-1]
    t_spectre = time.time() - t1

    t2 = time.time()
    K = Z @ Z.T                                      # Gram remontee a l'identique
    K *= -2.0
    K += carres[:, None]
    K += carres[None, :]
    np.maximum(K, 0, out=K)
    K *= -gamma
    np.exp(K, out=K)
    K -= K.mean(axis=0, keepdims=True)
    K -= K.mean(axis=1, keepdims=True)
    lam_h, vec = eigh(K.T, subset_by_index=[n - n_vec, n - 1], overwrite_a=True,
                      check_finite=False)
    del K
    lam_h, vec = lam_h[::-1], vec[:, ::-1]
    proj = vec * np.sqrt(np.clip(lam_h, 0, None))   # coordonnees kernel PCA

    v = np.clip(lam, 0, None) / total
    fichier = (f"{SORTIE}/grille_{MEDIA}_d{DEMI}_s{SEUIL:g}_m{mult:g}"
               f"_g{gamma:.6g}.npz")
    np.savez_compressed(fichier, lam=lam, total=total, var_lin=var_lin,
                        proj=proj.astype(np.float32), lam_vec=lam_h,
                        n=n, D=D, gamma=gamma, mult=mult, gamma_med=gamma_med,
                        mediane_d2=mediane, demi=DEMI, seuil=SEUIL,
                        date=p["date"].to_numpy(), mot=p["mot"].to_numpy())
    c = np.cumsum(v)
    print(f"  x{mult:<5g} gamma={gamma:<9.5f} : comp1 {v[0] * 100:5.2f} %, "
          f"cum6 {v[:6].sum() * 100:5.2f} %, cum20 {v[:20].sum() * 100:5.2f} % "
          f"| K50 {int(np.searchsorted(c, 0.5)) + 1:5d}, K90 {int(np.searchsorted(c, 0.9)) + 1:6d} "
          f"| somme/trace {lam.sum() / total:.6f} "
          f"| spectre {t_spectre:.0f} s, vecteurs {time.time() - t2:.0f} s", flush=True)
