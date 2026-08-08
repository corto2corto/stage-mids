# Plans des deux premieres composantes de la grille de gamma (kernel_grille.py),
# un journal par figure : le lineaire en reference, puis les 8 gamma de x0,1 a
# x30 fois gamma_med, du plus proche du lineaire au regime degenere.
#
# Les projections kernel sont deja calculees et stockees (50 vecteurs propres
# par grille_*.npz) ; seule la PCA lineaire est rejouee ici (meme chaine que
# figures_kernel.py, cout negligeable : SVD sur N x 21, pas de Gram).
#
# Les parts de variance affichees viennent du spectre ENTIER stocke (lam/total),
# pas des 50 valeurs retenues pour les vecteurs propres — sinon on retombe dans
# le piege du denominateur tronque documente dans kernel_pca.qmd.
# Usage : .venv/bin/python -m campagne_pca.figures_grille_plans
import glob
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import normaliser, pca

GRILLE, ENCRE2 = "#e1e0d9", "#52514e"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
SPECTRES = os.path.join(ICI, "kernel_spectres")
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)

DEMI, SEUIL = 10, 4.0
MEDIAS = [("mediapart7j", "_s3", "Mediapart", "#fc392b"),
          ("lesechos7j", "_s3", "Les Échos", "#b00005"),
          ("lefigaro7j", "_s3", "Le Figaro", "#163860")]
MULTS = (0.1, 0.25, 0.5, 1, 2, 4, 10, 30)


def pca_lineaire(media, suffixe):
    """Rejoue la chaine jusqu'aux projections lineaires (identique a figures_kernel.py)."""
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
    _, var_lin, proj_lin = pca(Z)
    return proj_lin, var_lin


for media, suffixe, nom, couleur in MEDIAS:
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("m", ["#ffffff", couleur])
    proj_lin, var_lin = pca_lineaire(media, suffixe)

    fig, axes = plt.subplots(3, 3, figsize=(10.2, 10.2))
    ax = axes.flat[0]
    hb = ax.hexbin(proj_lin[:, 0], proj_lin[:, 1], gridsize=42, bins="log", cmap=cmap,
                   linewidths=0.2)
    fig.colorbar(hb, ax=ax, shrink=0.82, label="fenêtres (log)")
    ax.set_xlabel(f"PC1 ({var_lin[0] * 100:.1f} %)".replace(".", ","))
    ax.set_ylabel(f"PC2 ({var_lin[1] * 100:.1f} %)".replace(".", ","))
    ax.set_title("PCA linéaire", fontsize=9.5, color=ENCRE2)

    for k, mult in enumerate(MULTS):
        fichier = glob.glob(f"{SPECTRES}/grille_{media}_d{DEMI}_s{SEUIL:g}_m{mult:g}_g*.npz")[0]
        d = np.load(fichier, allow_pickle=True)
        proj, lam, total, gamma = d["proj"], d["lam"], float(d["total"]), float(d["gamma"])
        v = np.clip(lam, 0, None) / total   # spectre entier -> part de variance exacte

        ax = axes.flat[k + 1]
        hb = ax.hexbin(proj[:, 0], proj[:, 1], gridsize=42, bins="log", cmap=cmap,
                       linewidths=0.2)
        fig.colorbar(hb, ax=ax, shrink=0.82, label="fenêtres (log)")
        ax.set_xlabel(f"PC1 ({v[0] * 100:.1f} %)".replace(".", ","))
        ax.set_ylabel(f"PC2 ({v[1] * 100:.1f} %)".replace(".", ","))
        ax.set_title(f"γ = {mult:g}·γ_méd = {gamma:.3g}", fontsize=9.5, color=ENCRE2)

    fig.suptitle(f"{nom} — plan des deux premières composantes, linéaire puis kernel RBF "
                 f"de γ_méd/10 à 30·γ_méd\n"
                 "même continuum partout : le noyau ne fait jamais apparaître de groupe",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fichier_sortie = f"{FIGURES}/grille_plan12_{media}.png"
    fig.savefig(fichier_sortie, bbox_inches="tight", dpi=170)
    plt.close(fig)
    print(f"-> {os.path.relpath(fichier_sortie, ICI)}")
