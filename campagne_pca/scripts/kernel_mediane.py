# Echelle reelle des distances entre fenetres, pour caler gamma du noyau RBF
# au lieu de le poser par convention. Sur des fenetres z-scorees ||z_i||^2 = D,
# donc ||z_i - z_j||^2 = 2D - 2<z_i, z_j> vit dans [0, 4D] et vaut 2D pour deux
# fenetres decorrelees : la mediane mesuree dit ou se trouve vraiment le nuage.
#
# La mediane exacte demanderait les n(n-1)/2 paires (64 millions au Figaro) ;
# on l'estime sur un tirage aleatoire de paires distinctes, avec l'ecart entre
# deux moities du tirage comme controle de stabilite.
# Sortie : mediane des d^2, gamma = 1/(2*mediane) et la variante sans le
# facteur 2, plus les quantiles pour situer les gammas deja calcules.
# Usage : VOCAB_DIR=... .venv/bin/python -m campagne_pca.scripts.kernel_mediane
import os

import numpy as np
import pandas as pd

from rupture.nms import nms
from rupture.pca import normaliser

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ICI = os.path.dirname(SCRIPTS)          # campagne_pca/
DATA = os.path.join(ICI, "data")
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(DATA, "data_local"))
DEMI, SEUIL, N_PAIRES, GRAINE = 10, 4.0, 4_000_000, 0
CONFIGS = [("lefigaro7j", "_s3"), ("lesechos7j", "_s3"), ("mediapart7j", "_s3")]

rng = np.random.default_rng(GRAINE)
for media, suffixe in CONFIGS:
    g = np.load(f"{DONNEES}/vocab_series_{media}.npz")
    X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    colonne = {m: j for j, m in enumerate(g["mots"])}

    p = pd.read_csv(f"{DONNEES}/pics_{media}{suffixe}.csv")
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

    i = rng.integers(0, n, N_PAIRES)
    j = rng.integers(0, n, N_PAIRES)
    distinct = i != j
    i, j = i[distinct], j[distinct]
    d2 = np.einsum("ij,ij->i", Z[i] - Z[j], Z[i] - Z[j])

    med = np.median(d2)
    moitie = len(d2) // 2
    m1, m2 = np.median(d2[:moitie]), np.median(d2[moitie:])
    q = np.percentile(d2, [1, 5, 25, 50, 75, 95, 99])
    print(f"{media} : {n:,} fenetres x {D} blocs, {len(d2):,} paires tirees".replace(",", " "),
          flush=True)
    print(f"  d^2 : mediane {med:.3f} (moities {m1:.3f} / {m2:.3f}), "
          f"borne theorique [0, {4 * D}], decorrele {2 * D}", flush=True)
    print("  quantiles 1/5/25/50/75/95/99 : "
          + " ".join(f"{v:.2f}" for v in q), flush=True)
    print(f"  gamma = 1/(2*mediane) = {1 / (2 * med):.5f}   "
          f"| sans facteur 2 : {1 / med:.5f}", flush=True)
