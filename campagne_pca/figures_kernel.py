# Figures du test kernel PCA (RBF) contre la PCA lineaire, sur la meme chaine
# que figures_config.py (pics -> NMS -> fenetres -> z-score). Trois vues :
#   1. spectre compare (variance expliquee par rang), un panneau par media
#   2. sensibilite au parametre gamma du noyau (cum6 et part de la comp. 1)
#   3. plan des deux premieres composantes, lineaire vs kernel
# La kernel PCA calcule une matrice de Gram N x N : a 123k fenetres elle
# saturerait la RAM (~120 Go) -> on tire un echantillon de N_ECH fenetres,
# le meme pour les deux methodes, pour que la comparaison soit honnete.
# Usage : .venv/bin/python -m campagne_pca.figures_kernel
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import KernelPCA

from rupture.nms import nms
from rupture.pca import normaliser, pca

GRILLE, ENCRE2, GRIS = "#e1e0d9", "#52514e", "#c9ced6"
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

DEMI, SEUIL = 15, 4
N_ECH, GRAINE = 8000, 0
# couleurs de charte des deux medias (memes que configurations_A_C)
MEDIAS = [("lemonde", "pics_lemonde.csv", "Le Monde", "#1a1a1a"),
          ("lesechos", "pics_lesechos_s3.csv", "Les Échos", "#9b2226")]
KERNEL = "#2a78d6"      # bleu : la kernel PCA, sur tous les panneaux
GAMMAS = np.array([0.003, 0.01, 0.0323, 0.1, 0.3, 1.0])   # 0.0323 = 1/31 = 1/D


def charger_fenetres(media, fichier_pics):
    """Rejoue la chaine jusqu'aux fenetres z-scorees (identique a figures_config)."""
    g = np.load(f"{DONNEES}/vocab_series_{media}.npz")
    X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    colonne = {m: j for j, m in enumerate(g["mots"])}

    p = pd.read_csv(f"{DONNEES}/{fichier_pics}")
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
    return Z


def variance_kernel(Z, gamma, rang):
    """Part de variance expliquee par rang, dans l'espace induit par le noyau."""
    k = KernelPCA(n_components=rang, kernel="rbf", gamma=gamma)
    proj = k.fit_transform(Z)
    return k.eigenvalues_ / k.eigenvalues_.sum(), proj


rng = np.random.default_rng(GRAINE)
resultats = {}
for media, fichier_pics, nom, couleur in MEDIAS:
    Z = charger_fenetres(media, fichier_pics)
    n_total = len(Z)
    Z = Z[rng.choice(n_total, N_ECH, replace=False)] if n_total > N_ECH else Z
    D = Z.shape[1]
    rang = D - 1

    _, var_lin, proj_lin = pca(Z)
    balayage = {g: variance_kernel(Z, g, rang) for g in GAMMAS}
    var_ker, proj_ker = balayage[GAMMAS[2]]          # gamma = 1/D, le cas de reference
    resultats[media] = dict(nom=nom, couleur=couleur, n_total=n_total, D=D, rang=rang,
                            var_lin=var_lin, var_ker=var_ker,
                            proj_lin=proj_lin, proj_ker=proj_ker, balayage=balayage)
    print(f"{nom} : {n_total} fenetres ({len(Z)} echantillonnees) x {D} blocs")
    print(f"  lineaire   : comp1 {var_lin[0] * 100:.1f} %, cum6 {var_lin[:6].sum() * 100:.1f} %")
    for g in GAMMAS:
        v = balayage[g][0]
        print(f"  RBF g={g:<6.4g} : comp1 {v[0] * 100:.1f} %, cum6 {v[:6].sum() * 100:.1f} %")

# --- 1. spectre compare -----------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
for ax, (media, _, _, _) in zip(axes, MEDIAS):
    r = resultats[media]
    rangs = np.arange(1, r["rang"] + 1)
    isotrope = 100 / r["rang"]
    ax.plot(rangs, r["var_lin"][:r["rang"]] * 100, lw=1.8, color=r["couleur"],
            label="PCA linéaire")
    ax.plot(rangs, r["var_ker"][:r["rang"]] * 100, lw=1.8, color=KERNEL,
            label="kernel PCA (RBF, γ=1/D)")
    ax.axhline(isotrope, lw=1.0, ls="--", color=GRIS,
               label=f"nuage sans structure ({isotrope:.1f} %)".replace(".", ","))
    for v, coul in ((r["var_lin"], r["couleur"]), (r["var_ker"], KERNEL)):
        ax.scatter([1], [v[0] * 100], s=18, color=coul, zorder=3)
        ax.annotate(f"{v[0] * 100:.1f} %".replace(".", ","), (1, v[0] * 100),
                    xytext=(7, 2), textcoords="offset points", fontsize=8.5, color=ENCRE2)
    ax.set_yscale("log")
    ax.set_xlabel("rang de la composante")
    ax.set_ylabel("variance expliquée (%)")
    ax.set_xlim(0.5, r["rang"] + 0.5)
    ax.set_xticks([1] + list(range(5, r["rang"] + 1, 5)))
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.set_title(f"{r['nom']} — cum6 : {r['var_lin'][:6].sum() * 100:.1f} % → "
                 f"{r['var_ker'][:6].sum() * 100:.1f} %".replace(".", ","),
                 fontsize=9.5, color=ENCRE2)
fig.suptitle("Variance expliquée par composante : PCA linéaire contre kernel PCA\n"
             f"fenêtres ±{DEMI} jours, seuil de surprise {SEUIL}, "
             f"échantillon de {N_ECH:,} fenêtres".replace(",", " "),
             fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.90))
fig.savefig(f"{FIGURES}/kernel_spectre.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 2. sensibilite a gamma -------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.7))
for ax, quoi, titre in ((axes[0], 0, "part de la composante 1"),
                        (axes[1], 1, "variance cumulée des 6 premières")):
    for media, _, _, _ in MEDIAS:
        r = resultats[media]
        y = [(r["balayage"][g][0][0] if quoi == 0 else r["balayage"][g][0][:6].sum()) * 100
             for g in GAMMAS]
        ref = (r["var_lin"][0] if quoi == 0 else r["var_lin"][:6].sum()) * 100
        ax.plot(GAMMAS, y, lw=1.7, marker="o", ms=4, color=r["couleur"],
                label=f"{r['nom']} — kernel")
        ax.axhline(ref, lw=1.1, ls="--", color=r["couleur"], alpha=0.55,
                   label=f"{r['nom']} — linéaire")
    ax.axvline(1 / 31, lw=1.0, color=KERNEL, alpha=0.6)
    ax.annotate("γ = 1/D", (1 / 31, ax.get_ylim()[1]), xytext=(4, -10),
                textcoords="offset points", fontsize=8, color=KERNEL)
    ax.set_xscale("log")
    ax.set_xlabel("γ du noyau RBF (échelle log)")
    ax.set_ylabel("variance expliquée (%)")
    ax.set_title(titre, fontsize=9.5, color=ENCRE2)
    ax.legend(frameon=False, fontsize=7.5)
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
fig.suptitle("Sensibilité du gain au paramètre γ : le noyau ne bat le linéaire "
             "que sur une plage étroite", fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.91))
fig.savefig(f"{FIGURES}/kernel_gamma.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 3. plan des deux premieres composantes ---------------------------------
fig, axes = plt.subplots(2, 2, figsize=(9.2, 7.4))
for ligne, (media, _, _, _) in enumerate(MEDIAS):
    r = resultats[media]
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "m", ["#ffffff", r["couleur"]])
    for col, (proj, var, quoi) in enumerate((
            (r["proj_lin"], r["var_lin"], "PCA linéaire"),
            (r["proj_ker"], r["var_ker"], "kernel PCA (RBF, γ=1/D)"))):
        ax = axes[ligne, col]
        hb = ax.hexbin(proj[:, 0], proj[:, 1], gridsize=45, bins="log",
                       cmap=cmap, linewidths=0.2)
        fig.colorbar(hb, ax=ax, shrink=0.82, label="fenêtres par case (log)")
        ax.set_xlabel(f"composante 1 ({var[0] * 100:.1f} %)".replace(".", ","))
        ax.set_ylabel(f"composante 2 ({var[1] * 100:.1f} %)".replace(".", ","))
        ax.set_title(f"{r['nom']} — {quoi}", fontsize=9.5, color=ENCRE2)
fig.suptitle("Le nuage des fenêtres dans le plan des deux premières composantes",
             fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(f"{FIGURES}/kernel_plan12.png", bbox_inches="tight", dpi=200)
plt.close(fig)

print(f"-> {os.path.relpath(FIGURES)} : kernel_spectre.png, kernel_gamma.png, "
      "kernel_plan12.png")
