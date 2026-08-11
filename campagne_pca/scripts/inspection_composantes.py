# Inspection des composantes des configs de tete de la campagne PCA (tourne
# sur le Mac, donnees dans campagne_pca/data_local/). Question posee (suivi
# 31/07 20h20) : les composantes des grandes fenetres agregees sont-elles des
# formes alignees sur l'evenement (energie au centre) ou des derives lentes
# (rampes, cosinus basse frequence — signature d'autocorrelation generique) ?
# Pour chaque config : figure 2x3 des 6 premieres composantes (style de
# rupture/pca.py) + indicateurs par composante : croisements de zero, part
# d'energie a moins de 25 % de la largeur du centre, correlation a une rampe.
# Usage : .venv/bin/python -m campagne_pca.scripts.inspection_composantes
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.graphes import BLEU, GRILLE, ENCRE2

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ICI = os.path.dirname(SCRIPTS)          # campagne_pca/
DATA = os.path.join(ICI, "data")
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)
CONFIGS = ["lefigaro7j_d50_s4_tous_n0", "lefigaro7j_d25_s4_tous_n0",
           "lefigaro7j_d15_s4_tous_n0", "lemonde_d15_s4_tous_n5000",
           "mediapart_d15_s4_tous_n2000"]

for tag in CONFIGS:
    chemin = os.path.join(DATA, "data_local", f"composantes_{tag}.csv")
    if not os.path.exists(chemin):
        print(f"{tag} : composantes absentes en local, sautee")
        continue
    c = pd.read_csv(chemin, index_col="composante")
    D = c.shape[1]
    js = np.arange(D) - D // 2
    rampe = (js - js.mean()) / js.std()
    print(f"\n{tag} (D={D})")
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.2), sharex=True)
    for k, ax in enumerate(axes.flat):
        v = c.iloc[k].to_numpy()
        croisements = int((np.diff(np.sign(v)) != 0).sum())
        centre = float((v[np.abs(js) <= D // 8] ** 2).sum() / (v ** 2).sum())
        r_rampe = float(np.corrcoef(v, rampe)[0, 1])
        print(f"  comp {k + 1} : {croisements} croisements de zero, "
              f"{centre * 100:4.0f} % d'energie au centre (|j| <= D/8), "
              f"corr rampe {r_rampe:+.2f}")
        ax.axhline(0, lw=.6, color=GRILLE)
        ax.axvline(0, lw=.6, color=GRILLE)
        ax.plot(js, v, lw=1.6, color=BLEU)
        ax.set_title(f"composante {k + 1} — {croisements} crois., "
                     f"{centre * 100:.0f} % centre", fontsize=8.5, color=ENCRE2)
        ax.set_xticks([js[0], 0, js[-1]])
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    for ax in axes[1]:
        ax.set_xlabel("pas de grille autour du pic")
    fig.suptitle(f"Profils des 6 premières composantes — {tag}",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(f"{FIGURES}/composantes_{tag}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  -> figures/composantes_{tag}.png")
