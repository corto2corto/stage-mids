# Comparaison des formes de sauts entre les quatre configurations hebdomadaires
# retenues dans configurations_hebdo.qmd, les trois premieres composantes en
# colonnes. Rejoue la chaine (pics -> NMS -> fenetres -> z-score -> PCA) pour
# chacune, sans rien ecrire d'autre que ce PNG.
# Usage : .venv/bin/python -m campagne_pca.figures_comparaison_hebdo
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import nettoyer, normaliser, pca

GRILLE, ENCRE2 = "#e1e0d9", "#52514e"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)

# (media, demi, seuil, pas_jours, pics, nettoie, nom affiche, sous-titre, couleur)
LIGNES = [
    ("lemonde7j", 10, 4.0, 7, "", 0, "Le Monde", "seuil 4 — 27 707 fenêtres", "#1A171B"),
    ("lefigaro7j", 10, 4.0, 7, "_s3", 0, "Le Figaro", "seuil 4 — 11 311 fenêtres", "#163860"),
    ("lesechos7j", 10, 4.0, 7, "_s3", 0, "Les Échos", "seuil 4 — 8 633 fenêtres", "#b00005"),
    ("mediapart7j", 10, 4.0, 7, "_s3", 0, "Mediapart", "seuil 4 — 5 483 fenêtres", "#fc392b"),
]

fig, axes = plt.subplots(len(LIGNES), 3, figsize=(9.6, 10.4))
for row, (media, demi, seuil, pas_jours, pics, nettoie, nom, sous_titre, couleur) in enumerate(LIGNES):
    g = np.load(f"{DONNEES}/vocab_series_{media}.npz")
    X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    colonne = {m: j for j, m in enumerate(g["mots"])}

    p = pd.read_csv(f"{DONNEES}/pics_{media}{pics}.csv")
    p = p[p["surprise"] >= seuil].assign(pos=lambda x: x["date"].map(position))
    gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                     2 * demi + 1)[0]]
              for _, gr in p.groupby("mot", sort=False)]
    p = p.loc[np.concatenate(gardes)]
    pos, col = p["pos"].to_numpy(), p["mot"].map(colonne).to_numpy(int)
    complet = (pos - demi >= 0) & (pos + demi < len(grille_dates))
    pos, col = pos[complet], col[complet]
    lignes_idx = pos[:, None] + np.arange(-demi, demi + 1)
    F = (1e5 * X[lignes_idx, col[:, None]] / grille_N[lignes_idx]).astype(np.float64)

    if nettoie:
        F, _, _, _ = nettoyer(F, grille_N[lignes_idx], nettoie, demi)
    Z, _ = normaliser(F, "z")
    composantes, variance, _ = pca(Z)
    js = np.arange(-demi, demi + 1)
    unite = "jours" if pas_jours == 1 else f"semaines"

    for k in range(3):
        ax = axes[row, k]
        ax.axhline(0, lw=.6, color=GRILLE)
        ax.axvline(0, lw=.6, color=GRILLE)
        ax.plot(js, composantes[k], lw=1.7, color=couleur)
        ax.set_title(f"composante {k + 1} — {variance[k] * 100:.1f} %",
                     fontsize=8.5, color=ENCRE2)
        ax.set_xticks([-demi, 0, demi])
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
        if row == len(LIGNES) - 1:
            ax.set_xlabel(f"{unite} autour du pic", fontsize=8)
        if k == 0:
            ax.set_ylabel(f"{nom}\n{sous_titre}", fontsize=8.5)
    print(f"{nom} ({sous_titre}) : {len(Z)} fenêtres, variance 1-3 = "
          f"{np.round(variance[:3] * 100, 1)}")

fig.suptitle("La forme des sauts par journal — trois premières composantes\n"
             "Grille hebdomadaire, fenêtres ±10 semaines, seuil 4",
             fontsize=11, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(f"{FIGURES}/comparaison_hebdo.png", bbox_inches="tight", dpi=200)
plt.close(fig)
print(f"-> {os.path.relpath(FIGURES)}/comparaison_hebdo.png")
