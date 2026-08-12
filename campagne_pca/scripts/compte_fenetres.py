# Comptage rapide de fenetres pour reperer une config plus volumineuse pour la
# kernel PCA, sans rien calculer de lourd (pas de Gram, pas de PCA). Meme chaine
# que kernel_grille.py (pics -> NMS -> fenetres completes), juste le compte.
# Usage : VOCAB_DIR=... .venv/bin/python -m campagne_pca.scripts.compte_fenetres
import os
from pathlib import Path

import numpy as np
import pandas as pd

from rupture.nms import nms

SCRIPTS = Path(__file__).resolve().parent
ICI = SCRIPTS.parent                    # campagne_pca/
DATA = ICI / "data"
DONNEES = Path(os.environ.get("VOCAB_DIR", DATA / "data_local"))

# (media, suffixe_pics, nom, demis, seuils)
CONFIGS = [
    ("lemonde", "", "Le Monde (journalier)", (10, 15), (4, 5, 6)),
    ("lefigaro", "_s3", "Le Figaro (journalier)", (10, 15), (4, 5, 6)),
    ("lesechos", "_s3", "Les Echos (journalier)", (10, 15), (4, 5, 6)),
    ("mediapart", "_s3", "Mediapart (journalier)", (10, 15), (4, 5, 6)),
]

print(f"{'media':24s} {'demi':>5s} {'seuil':>6s} {'fenetres':>9s} {'Gram (Go)':>10s}")
for media, suffixe, nom, demis, seuils in CONFIGS:
    g = np.load(DONNEES / f"vocab_series_{media}.npz")
    grille_dates = g["dates"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    pics = pd.read_csv(DONNEES / f"pics_{media}{suffixe}.csv")
    for seuil in seuils:
        p = pics[pics["surprise"] >= seuil].assign(pos=lambda x: x["date"].map(position))
        for demi in demis:
            gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                             2 * demi + 1)[0]]
                      for _, gr in p.groupby("mot", sort=False)]
            pp = p.loc[np.concatenate(gardes)]
            pos = pp["pos"].to_numpy()
            complet = (pos - demi >= 0) & (pos + demi < len(grille_dates))
            n = int(complet.sum())
            go = n * n * 8 / 1e9
            print(f"{nom:24s} {demi:>5d} {seuil:>6d} {n:>9,} {go:>10.1f}".replace(",", " "))
    print()
