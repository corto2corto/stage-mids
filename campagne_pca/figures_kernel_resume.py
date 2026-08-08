# Tableau de synthese kernel PCA vs PCA lineaire, pour le petit rapport
# kernel_hebdo.qmd. Relit les fichiers deja calcules (kernel_grille.py, spectre
# entier + projections) : aucun nouveau calcul, aucune matrice de Gram refaite.
#
# Trois gamma retenus sur les huit de la grille, memes multiplicateurs pour les
# trois journaux (gamma_med differe par journal, le choix des points non) :
#   x0,1  : le plus proche du lineaire, teste si un petit gamma peut au moins
#           egaler la PCA classique
#   x1    : gamma_med, le reglage cale sur l'echelle reelle des distances
#   x30   : le regime degenere, teste comme piece a conviction du mecanisme
# comp1 et cum6 ne racontent pas le meme phenomene : cum6 dilue avec le nombre
# de rangs disponibles (plus eleve en kernel), comp1 compare la MEILLEURE
# direction unique des deux methodes sans cet artefact. K50/K90 (composantes
# pour 50 %/90 % de variance) mesurent directement l'etalement.
# Usage : .venv/bin/python -m campagne_pca.figures_kernel_resume [--suffixe-media 3j
#         --demi 10 --seuil 5 --sortie-suffixe _3j]
import argparse
import glob
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import normaliser, pca

ap = argparse.ArgumentParser()
ap.add_argument("--suffixe-media", default="7j", help="suffixe des noms de base (mediapart, lesechos, lefigaro)")
ap.add_argument("--demi", type=int, default=10)
ap.add_argument("--seuil", type=float, default=4.0)
ap.add_argument("--sortie-suffixe", default="", help="suffixe des fichiers de sortie (ex. _3j)")
a = ap.parse_args()

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
SPECTRES = os.path.join(ICI, "kernel_spectres")
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)
GRILLE_AXE = "#e1e0d9"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
})
DEMI, SEUIL = a.demi, a.seuil

ENCRE, ENCRE2, TRAIT, FOND_ALT = "#1a1a1a", "#52514e", "#c3c2b7", "#f4f3ee"
MEDIAS = [(f"mediapart{a.suffixe_media}", "Mediapart", "#fc392b"),
          (f"lesechos{a.suffixe_media}", "Les Échos", "#b00005"),
          (f"lefigaro{a.suffixe_media}", "Le Figaro", "#163860")]
MULTS = (0.1, 1, 30)
COLONNES = ["", "linéaire", "0,1 · γ_méd", "γ_méd", "30 · γ_méd"]


def lire(media, mult=None):
    """Spectre entier -> (comp1 %, K50, K90) ; mult=None renvoie la reference lineaire."""
    f = glob.glob(f"{SPECTRES}/grille_{media}_d{DEMI}_s{SEUIL:g}_m1_g*.npz")[0]
    d = np.load(f, allow_pickle=True)
    n = int(d["n"])
    if mult is None:
        v = d["var_lin"]
    else:
        f = glob.glob(f"{SPECTRES}/grille_{media}_d{DEMI}_s{SEUIL:g}_m{mult:g}_g*.npz")[0]
        d = np.load(f, allow_pickle=True)
        v = np.clip(d["lam"], 0, None) / float(d["total"])
    c = np.cumsum(v)
    k50 = int(np.searchsorted(c, 0.5)) + 1
    k90 = int(np.searchsorted(c, 0.9)) + 1
    return n, v[0] * 100, k50, k90, (float(d["gamma"]) if mult is not None else None)


# --- construction des lignes -------------------------------------------------
lignes = []   # (type, texte_col0, [4 valeurs formatees], couleur_accent ou None)
for media, nom, couleur in MEDIAS:
    n, c1_lin, k50_lin, k90_lin, _ = lire(media)
    gammas = [lire(media, m) for m in MULTS]
    gamma_med = gammas[1][4]
    lignes.append(("media", f"{nom} — {n:,}".replace(",", " ") + " fenêtres, "
                   f"γ_méd = {gamma_med:.4f}".replace(".", ","), None, couleur))
    lignes.append(("val", "comp1 (%)",
                   [f"{c1_lin:.2f}".replace(".", ",")]
                   + [f"{g[1]:.2f}".replace(".", ",") for g in gammas], None))
    lignes.append(("val", "K50",
                   [f"{k50_lin:,}".replace(",", " ")]
                   + [f"{g[2]:,}".replace(",", " ") for g in gammas], None))
    lignes.append(("val", "K90",
                   [f"{k90_lin:,}".replace(",", " ")]
                   + [f"{g[3]:,}".replace(",", " ") for g in gammas], None))

# --- rendu ---------------------------------------------------------------
n_lignes = len(lignes)
H_ENTETE, H_MEDIA, H_VAL = 0.9, 0.75, 0.62
hauteur = H_ENTETE + sum(H_MEDIA if t == "media" else H_VAL for t, *_ in lignes) + 0.3
largeurs = [2.7, 1.35, 1.55, 1.35, 1.55]
largeur_fig = sum(largeurs) + 0.6

fig, ax = plt.subplots(figsize=(largeur_fig, hauteur / 2.15))
ax.set_xlim(0, sum(largeurs))
ax.set_ylim(0, hauteur)
ax.axis("off")

x_cols = np.cumsum([0] + largeurs)
y = hauteur

# entete
y -= H_ENTETE
for xc, w, texte in zip(x_cols, largeurs, COLONNES):
    ax.text(xc + (0.12 if texte == "" else w / 2), y + H_ENTETE / 2, texte,
            ha="left" if texte == "" else "center", va="center",
            fontsize=10, fontweight="bold", color=ENCRE)
ax.plot([0, sum(largeurs)], [y, y], lw=1.3, color=ENCRE)

for typ, texte, valeurs, couleur in lignes:
    h = H_MEDIA if typ == "media" else H_VAL
    y -= h
    if typ == "media":
        ax.add_patch(plt.Rectangle((0, y), sum(largeurs), h, color=couleur, alpha=0.10,
                                   zorder=0))
        ax.add_patch(plt.Rectangle((0, y), 0.06, h, color=couleur, zorder=1))
        ax.text(0.20, y + h / 2, texte, ha="left", va="center",
                fontsize=9.5, fontweight="bold", color=ENCRE2)
    else:
        ax.text(x_cols[0] + 0.35, y + h / 2, texte, ha="left", va="center",
                fontsize=9, color=ENCRE2)
        for xc, w, val in zip(x_cols[1:], largeurs[1:], valeurs):
            ax.text(xc + w / 2, y + h / 2, val, ha="center", va="center",
                    fontsize=9, color=ENCRE)
        ax.plot([0, sum(largeurs)], [y, y], lw=0.5, color=TRAIT, zorder=0)

fichier = f"{FIGURES}/kernel_resume_tableau{a.sortie_suffixe}.png"
fig.savefig(fichier, bbox_inches="tight", dpi=220, facecolor="white")
plt.close(fig)
print(f"-> {os.path.relpath(fichier, ICI)}")


# --- plan PC1-PC2, memes 3 gamma que le tableau -----------------------------
def pca_lineaire(media, suffixe="_s3"):
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
    lignes_idx = pos[:, None] + np.arange(-DEMI, DEMI + 1)
    F = (1e5 * X[lignes_idx, col[:, None]] / grille_N[lignes_idx]).astype(np.float64)
    Z, _ = normaliser(F, "z")
    _, var_lin, proj_lin = pca(Z)
    return proj_lin, var_lin


fig, axes = plt.subplots(3, 4, figsize=(11.2, 8.4))
for ligne, (media, nom, couleur) in enumerate(MEDIAS):
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("m", ["#ffffff", couleur])
    proj_lin, var_lin = pca_lineaire(media)
    panneaux = [(proj_lin, var_lin, "linéaire")]
    for mult in MULTS:
        f = glob.glob(f"{SPECTRES}/grille_{media}_d{DEMI}_s{SEUIL:g}_m{mult:g}_g*.npz")[0]
        d = np.load(f, allow_pickle=True)
        v = np.clip(d["lam"], 0, None) / float(d["total"])
        libelle = "0,1 · γ_méd" if mult == 0.1 else ("γ_méd" if mult == 1 else "30 · γ_méd")
        panneaux.append((d["proj"], v, libelle))

    for col, (proj, var, titre) in enumerate(panneaux):
        ax = axes[ligne, col]
        ax.hexbin(proj[:, 0], proj[:, 1], gridsize=35, bins="log", cmap=cmap, linewidths=0.15)
        ax.set_xticks([]); ax.set_yticks([])
        if ligne == 0:
            ax.set_title(titre, fontsize=10, color="#52514e")
        if col == 0:
            ax.set_ylabel(nom, fontsize=10, color="#52514e", fontweight="bold")
        ax.text(0.03, 0.03, f"PC1 {var[0] * 100:.1f} %".replace(".", ","),
                transform=ax.transAxes, fontsize=7.5, color="#52514e", va="bottom")

fig.suptitle("Plan des deux premières composantes : même continuum à chaque γ, "
             "aucun groupe que le noyau ferait apparaître", fontsize=11, color="#1a1a1a")
fig.tight_layout(rect=(0, 0, 1, 0.95))
fichier = f"{FIGURES}/kernel_resume_plans{a.sortie_suffixe}.png"
fig.savefig(fichier, bbox_inches="tight", dpi=170, facecolor="white")
plt.close(fig)
print(f"-> {os.path.relpath(fichier, ICI)}")
