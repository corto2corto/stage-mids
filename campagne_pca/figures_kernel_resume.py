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
# Usage : .venv/bin/python -m campagne_pca.figures_kernel_resume
import glob
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ICI = os.path.dirname(os.path.abspath(__file__))
SPECTRES = os.path.join(ICI, "kernel_spectres")
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)

ENCRE, ENCRE2, TRAIT, FOND_ALT = "#1a1a1a", "#52514e", "#c3c2b7", "#f4f3ee"
MEDIAS = [("mediapart7j", "Mediapart", "#fc392b"),
          ("lesechos7j", "Les Échos", "#b00005"),
          ("lefigaro7j", "Le Figaro", "#163860")]
MULTS = (0.1, 1, 30)
COLONNES = ["", "linéaire", "0,1 · γ_méd", "γ_méd", "30 · γ_méd"]


def lire(media, mult=None):
    """Spectre entier -> (comp1 %, K50, K90) ; mult=None renvoie la reference lineaire."""
    f = glob.glob(f"{SPECTRES}/grille_{media}_d10_s4_m1_g*.npz")[0]
    d = np.load(f, allow_pickle=True)
    n = int(d["n"])
    if mult is None:
        v = d["var_lin"]
    else:
        f = glob.glob(f"{SPECTRES}/grille_{media}_d10_s4_m{mult:g}_g*.npz")[0]
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

fichier = f"{FIGURES}/kernel_resume_tableau.png"
fig.savefig(fichier, bbox_inches="tight", dpi=220, facecolor="white")
plt.close(fig)
print(f"-> {os.path.relpath(fichier, ICI)}")
