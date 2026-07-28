# Fenetres archetypes des grilles agregees (blocs de 3 et 7 jours) : meme
# figure que pca_lemonde_archetypes.png (les 3 sauts reels les plus alignes
# sur chacune des 4 premieres composantes), mais sur lemonde3j et lemonde7j.
# Le signe d'une composante etant arbitraire, on l'aligne sur la composante
# journaliere de meme rang (cosinus) avant de classer les fenetres : les
# archetypes sont donc directement comparables a ceux de la grille au jour.
# Lit fenetres_<media>.npz et pca_<media>_z.npz, ecrit
# rupture/sorties/pca_<media>_archetypes.png.
# Usage : python -m exploration.figures_archetypes_agrege
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLEU, ROUGE, GRILLE, ENCRE2 = "#2a78d6", "#e34948", "#e1e0d9", "#52514e"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
SORTIES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rupture", "sorties")
os.makedirs(SORTIES, exist_ok=True)

LIBELLES = ["pic isolé d'un bloc", "plus actif après le pic",
            "bascule avant/après", "creux la veille, rebond"]
js = np.arange(-15, 16)

ref = np.load(f"{DOSSIER}/pca_lemonde_z.npz")["composantes"]   # grille journaliere

for media, taille in (("lemonde3j", 3), ("lemonde7j", 7)):
    d = np.load(f"{DOSSIER}/fenetres_{media}.npz")
    F, mots, dates = d["fenetres"].astype(float), d["mot"], d["date"]
    p = np.load(f"{DOSSIER}/pca_{media}_z.npz")
    proj, composantes, garde = p["projections"].astype(float), p["composantes"], p["garde"]
    F, mots, dates = F[garde], mots[garde], dates[garde]        # alignement sur la PCA
    Z = (F - F.mean(1, keepdims=True)) / F.std(1, keepdims=True)   # ce que voit la PCA

    signes = np.sign([composantes[k] @ ref[k] or 1.0 for k in range(4)])
    print(f"{media} : {len(F)} fenetres, cosinus aux composantes journalieres "
          f"{np.round([composantes[k] @ ref[k] for k in range(4)], 2)}", flush=True)

    fig, axes = plt.subplots(4, 3, figsize=(9.2, 9.6), sharex=True)
    for k in range(4):
        meilleurs = np.argsort(signes[k] * proj[:, k])[-3:][::-1]
        for c, i in enumerate(meilleurs):
            ax = axes[k, c]
            ax.axhline(0, lw=.6, color=GRILLE)
            ax.axvline(0, lw=.6, color=GRILLE)
            ax.plot(js, Z[i], lw=1.4, color=BLEU)
            ax.scatter([0], [Z[i, 15]], s=16, color=ROUGE, zorder=3)
            quand = pd.to_datetime(str(dates[i])).strftime("%d/%m/%Y")
            ax.set_title(f"{mots[i]} — {quand}", fontsize=8.5, color=ENCRE2)
            ax.grid(True, axis="y", lw=.5, color=GRILLE)
            ax.set_axisbelow(True)
            if c == 0:
                ax.set_ylabel(f"comp. {k + 1}\n({LIBELLES[k]})", fontsize=8.5)
    for ax in axes[-1]:
        ax.set_xticks([-15, 0, 15])
        ax.set_xlabel(f"blocs de {taille} jours autour du pic")
    fig.suptitle(f"Fenêtres archétypes, grille {taille} jours : les 3 sauts réels les plus "
                 "alignés sur chaque composante (fenêtres en z-score)",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(f"{SORTIES}/pca_{media}_archetypes.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  -> pca_{media}_archetypes.png", flush=True)
