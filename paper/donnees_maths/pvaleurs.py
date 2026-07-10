"""Etape 4 - p-valeurs sous la NB ajustee (Le Monde, 2020-2024).

Pour chaque jour t : p_t = P(X >= X_t) sous NB(mu*N_t, r) -> la loi du jour,
avec le vrai N_t (exposure). Diagnostic : l'histogramme des p_t doit etre
~uniforme si le modele colle ; un exces pres de 0 = jours anormaux (pics).
Surprise = -log10(p_t). Seuil indicatif : p < 1e-4.

Sorties :
  - figure 6 panneaux : histogramme des p_t par mot (build_pvaleurs/hist_pvaleurs.png)
  - top des jours les plus surprenants par mot (console + pics_detectes.csv)
"""
import os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import nbinom
from statsmodels.discrete.discrete_model import NegativeBinomial

ICI = "paper/donnees_maths"
OUT = f"{ICI}/build_pvaleurs"
os.makedirs(OUT, exist_ok=True)
MOTS = ["president", "gouvernement", "guerre", "climat", "economie", "inflation"]
LIB = {"president": "président", "economie": "économie"}
SEUIL = 1e-4

fig, axes = plt.subplots(2, 3, figsize=(11, 6))
tous_pics = []

for ax, nom in zip(axes.flat, MOTS):
    d = pd.read_csv(f"{ICI}/{nom}_lemonde.csv")
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, r = np.exp(res.params[0]), 1.0 / res.params[1]

    # p_t = P(X >= X_t) sous la loi du jour : sf(X_t - 1)
    p_nb = r / (r + mu * N)
    p = nbinom.sf(X - 1, r, p_nb)
    d["p_t"], d["surprise"] = p, -np.log10(np.clip(p, 1e-300, None))

    pics = d[d["p_t"] < SEUIL].copy()
    pics["mot"] = LIB.get(nom, nom)
    tous_pics.append(pics)

    ax.hist(p, bins=20, range=(0, 1), density=True, color="#c9ced6")
    ax.axhline(1, color="#c1440e", lw=1, ls="--")   # uniforme = densite 1
    ax.set_title(f"{LIB.get(nom, nom)}  ({len(pics)} j sous {SEUIL:g})", fontsize=10)
    ax.set_ylim(0, 3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

fig.suptitle("Histogramme des p-valeurs sous la NB ajustée (uniforme = modèle OK)", y=0.99)
fig.supxlabel("$p_t = P(X \\geq X_t)$"); fig.supylabel("densité")
fig.tight_layout()
fig.savefig(f"{OUT}/hist_pvaleurs.png", dpi=130)

pics = pd.concat(tous_pics).sort_values("surprise", ascending=False)
pics = pics[["mot", "date", "X_t", "N_t", "p_t", "surprise"]]
pics.to_csv(f"{ICI}/pics_detectes.csv", index=False)

print(f"{len(pics)} jours anormaux (p < {SEUIL:g}) sur les 6 mots\n")
print("Top 15 des jours les plus surprenants :")
top = pics.head(15).copy()
top["p_t"] = top["p_t"].map(lambda v: f"{v:.1e}")
top["surprise"] = top["surprise"].round(1)
print(top.to_string(index=False))
print("\n-> pics_detectes.csv + build_pvaleurs/hist_pvaleurs.png")
