# Figures de synthese de la campagne PCA 48 h (tourne sur le Mac, lit les
# recoltes locales campagne_pca/resultats_rotation.csv). Deux figures dans
# campagne_pca/figures/ :
# 1. synthese_axes.png — pour chaque axe (media, grille, demi-fenetre,
#    seuil), les deux metriques a n apparie 5000 en brut : exces6 (structure
#    totale au-dela des marges, nul par melange de colonnes) et alignement6
#    (part ancree sur l'evenement, nul par decalage circulaire). Moyennes
#    sur le sous-ensemble equilibre (cellules presentes pour les 4 medias),
#    graines moyennees ; dispersion inter-graines mediane 0,0045 —
#    invisible a cette echelle, pas de barres d'erreur.
# 2. synthese_carte_medias.png — carte (exces6, alignement6) des 12
#    media-grilles a la config de reference (d15, s4, tous), brut : les deux
#    familles (texture vs ancrage) se separent.
# Usage : .venv/bin/python -m campagne_pca.figures_synthese
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.graphes import BLEU, ORANGE, GRILLE, ENCRE2

ICI = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)
NOMS_MEDIAS = {"lemonde": "Le Monde", "lefigaro": "Le Figaro",
               "lesechos": "Les Échos", "mediapart": "Mediapart"}

r = pd.read_csv(os.path.join(ICI, "resultats_rotation.csv"))
r = r[(r["n_fenetres"] == 5000) & ~r["tag"].str.contains("_log")].copy()
r["base"] = r["media"].str.replace(r"(3j|7j)$", "", regex=True)
r["grille"] = r["media"].str.extract(r"(3j|7j)$")[0].fillna("1j")
r["cellule"] = r["grille"] + "|" + r["demi"].astype(str) + "|" + \
    r["seuil"].astype(str) + "|" + r["filtre"]
r = r.groupby(["base", "cellule", "grille", "demi", "seuil", "filtre"],
              as_index=False)[["exces6", "alignement6"]].mean()   # graines
completes = r.groupby("cellule")["base"].nunique()
r = r[r["cellule"].map(completes) == 4]                           # equilibre
print(f"{len(r)} lignes (cellules completes x 4 medias), "
      f"{r['cellule'].nunique()} cellules")

# figure 1 : effets d'axes
AXES = [("base", "média", [NOMS_MEDIAS[b] for b in
                           ["mediapart", "lesechos", "lemonde", "lefigaro"]],
         ["mediapart", "lesechos", "lemonde", "lefigaro"]),
        ("grille", "grille de temps", ["journalier", "3 jours", "7 jours"],
         ["1j", "3j", "7j"]),
        ("demi", "demi-fenêtre (± pas)", ["10", "15", "25", "50"], [10, 15, 25, 50]),
        ("seuil", "seuil de surprise", ["4", "6"], [4.0, 6.0])]
fig, axs = plt.subplots(1, 4, figsize=(10.4, 3.2), sharey=True)
for ax, (col, titre, etiquettes, ordre) in zip(axs, AXES):
    m = r.groupby(col)[["exces6", "alignement6"]].mean().loc[ordre]
    x = np.arange(len(ordre))
    ax.axhline(1, lw=.8, color=GRILLE)
    ax.plot(x, m["alignement6"], "-", lw=2, color=ORANGE, marker="o", ms=6,
            label="alignement6 (part ancrée sur le pic)")
    ax.plot(x, m["exces6"], "-", lw=2, color=BLEU, marker="o", ms=6,
            label="exces6 (structure au-delà des marges)")
    ax.set_xticks(x, etiquettes, fontsize=8)
    ax.set_title(titre, fontsize=9.5, color=ENCRE2)
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
axs[0].set_ylabel("concentration relative au nul", fontsize=9)
poignees, textes = axs[0].get_legend_handles_labels()
fig.legend(poignees, textes, frameon=False, fontsize=8.5, ncol=2,
           loc="upper center", bbox_to_anchor=(0.5, 0.93))
fig.suptitle("Effets des hyperparamètres sur les deux métriques — brut, "
             "n apparié à 5 000 fenêtres, grille équilibrée",
             fontsize=10.5, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.86))
fig.savefig(f"{FIGURES}/synthese_axes.png", bbox_inches="tight", dpi=200)
plt.close(fig)
print("-> figures/synthese_axes.png")

# figure 2 : carte des media-grilles a la reference
ref = r[(r["demi"] == 15) & (r["seuil"] == 4.0) & (r["filtre"] == "tous")]
fig, ax = plt.subplots(figsize=(6.4, 4.6))
ax.axhline(1, lw=.8, color=GRILLE)
ax.axvline(1, lw=.8, color=GRILLE)
# decalages manuels pour les etiquettes qui se chevauchent au rendu
DECALAGES = {("mediapart", "3j"): (-8, -14), ("mediapart", "7j"): (7, 6),
             ("lemonde", "7j"): (-30, -16), ("lefigaro", "3j"): (7, 8)}
for _, ligne in ref.iterrows():
    ax.scatter(ligne["exces6"], ligne["alignement6"], s=46, color=BLEU,
               zorder=3)
    dx, dy = DECALAGES.get((ligne["base"], ligne["grille"]), (7, 3))
    ax.annotate(f"{NOMS_MEDIAS[ligne['base']]} {ligne['grille']}",
                (ligne["exces6"], ligne["alignement6"]),
                xytext=(dx, dy), textcoords="offset points",
                fontsize=8, color=ENCRE2)
ax.set_xlabel("exces6 — structure totale (texture comprise)", fontsize=9)
ax.set_ylabel("alignement6 — part ancrée sur l'événement", fontsize=9)
ax.set_title("Carte des médias × grilles (référence ±15, s4, tous, brut, "
             "n = 5 000)", fontsize=10, color=ENCRE2)
ax.grid(True, lw=.5, color=GRILLE)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{FIGURES}/synthese_carte_medias.png", bbox_inches="tight", dpi=200)
plt.close(fig)
print("-> figures/synthese_carte_medias.png")

# tableau des moyennes par axe pour le rapport
for col, titre, _, ordre in AXES:
    m = r.groupby(col)[["exces6", "alignement6"]].mean().loc[ordre].round(3)
    print(f"\n{titre} :\n{m.to_string()}")
