# Figures du test kernel PCA (RBF) contre la PCA lineaire, sur la meme chaine
# que figures_config.py (pics -> NMS -> fenetres -> z-score).
#
# ATTENTION AU DENOMINATEUR. sklearn KernelPCA(n_components=k).eigenvalues_ ne
# rend que k valeurs propres. Les diviser par LEUR PROPRE SOMME ne donne pas la
# part de variance : la variance totale dans l'espace induit par le noyau est la
# trace de la matrice de Gram centree, dont le rang va jusqu'a N (pas k). Avec
# le denominateur tronque on lit un gain spectaculaire qui n'existe pas. Ici on
# calcule les deux, et la figure 2 montre l'ecart — c'est le resultat principal.
#   trace(Kc) = trace(K) - somme(K)/N, et trace(K) = N pour le noyau RBF.
#
# Trois vues :
#   1. spectre compare (part de variance correcte), un panneau par media
#   2. le piege du denominateur : faux gain (tronque) contre realite (correct)
#   3. plan des deux premieres composantes, lineaire contre kernel
# La matrice de Gram est N x N : a 123k fenetres elle saturerait la RAM
# (~120 Go) -> echantillon de N_ECH fenetres, le meme pour les deux methodes.
# Usage : .venv/bin/python -m campagne_pca.figures_kernel
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import KernelPCA
from sklearn.metrics.pairwise import rbf_kernel

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
MEDIAS = [("lemonde", "pics_lemonde.csv", "Le Monde", "#1a1a1a"),
          ("lesechos", "pics_lesechos_s3.csv", "Les Échos", "#9b2226")]
KERNEL = "#2a78d6"
GAMMAS = np.array([0.003, 0.01, 0.0323, 0.1, 0.3, 1.0])   # 0.0323 = 1/31 = 1/D
I_REF = 2                                                  # indice de gamma = 1/D


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


def kernel_variance(M, gamma, rang):
    """(part de variance CORRECTE, part avec denominateur TRONQUE, projections).

    La matrice de Gram est calculee une seule fois et passee en 'precomputed'
    pour ne pas la garder deux fois en memoire."""
    K = rbf_kernel(M, gamma=gamma)
    total = np.trace(K) - K.sum() / len(K)      # trace de la Gram centree
    k = KernelPCA(n_components=rang, kernel="precomputed")
    proj = k.fit_transform(K)
    del K
    lam = k.eigenvalues_
    return lam / total, lam / lam.sum(), proj


rng = np.random.default_rng(GRAINE)
resultats = {}
for media, fichier_pics, nom, couleur in MEDIAS:
    Z = charger_fenetres(media, fichier_pics)
    n_total = len(Z)
    Z = Z[rng.choice(n_total, N_ECH, replace=False)] if n_total > N_ECH else Z
    D = Z.shape[1]
    rang = D - 1

    _, var_lin, proj_lin = pca(Z)
    balayage = {g: kernel_variance(Z, g, rang) for g in GAMMAS}
    var_ker, _, proj_ker = balayage[GAMMAS[I_REF]]
    resultats[media] = dict(nom=nom, couleur=couleur, n_total=n_total, D=D, rang=rang,
                            var_lin=var_lin, var_ker=var_ker,
                            proj_lin=proj_lin, proj_ker=proj_ker, balayage=balayage)
    print(f"{nom} : {n_total} fenetres ({len(Z)} echantillonnees) x {D} blocs")
    print(f"  lineaire   : comp1 {var_lin[0] * 100:5.2f} %, cum6 {var_lin[:6].sum() * 100:5.2f} %")
    for g in GAMMAS:
        ok, tronque, _ = balayage[g]
        print(f"  RBF g={g:<6.4g} : comp1 {ok[0] * 100:5.2f} %, cum6 {ok[:6].sum() * 100:5.2f} % "
              f"| tronque : comp1 {tronque[0] * 100:5.2f} %, cum6 {tronque[:6].sum() * 100:5.2f} % "
              f"| les {rang} premieres pesent {ok.sum() * 100:5.1f} % du total")

# Temoin : bruit blanc z-score par ligne, meme forme, aucune structure temporelle.
D = resultats[MEDIAS[0][0]]["D"]
rang = D - 1
B = rng.standard_normal((N_ECH, D))
B = (B - B.mean(axis=1, keepdims=True)) / B.std(axis=1, keepdims=True)
_, var_lin_b, _ = pca(B)
balayage_b = {g: kernel_variance(B, g, rang)[:2] for g in GAMMAS}
temoin = dict(var_lin=var_lin_b, balayage=balayage_b)
print(f"\ntemoin bruit blanc ({N_ECH} x {D}) :")
print(f"  lineaire   : comp1 {var_lin_b[0] * 100:5.2f} %, cum6 {var_lin_b[:6].sum() * 100:5.2f} %")
for g in GAMMAS:
    ok, tronque = balayage_b[g]
    print(f"  RBF g={g:<6.4g} : comp1 {ok[0] * 100:5.2f} %, cum6 {ok[:6].sum() * 100:5.2f} % "
          f"| tronque : comp1 {tronque[0] * 100:5.2f} %, cum6 {tronque[:6].sum() * 100:5.2f} %")

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
    ax.annotate(f"{r['var_lin'][0] * 100:.1f} %".replace(".", ","),
                (1, r["var_lin"][0] * 100), xytext=(8, 3), textcoords="offset points",
                fontsize=8.5, color=ENCRE2)
    ax.set_yscale("log")
    ax.set_xlabel("rang de la composante")
    ax.set_ylabel("variance expliquée (%)")
    ax.set_xlim(0.5, r["rang"] + 0.5)
    ax.set_xticks([1] + list(range(5, r["rang"] + 1, 5)))
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.set_title(f"{r['nom']} — cum6 : {r['var_lin'][:6].sum() * 100:.1f} % en linéaire, "
                 f"{r['var_ker'][:6].sum() * 100:.1f} % en kernel".replace(".", ","),
                 fontsize=9.5, color=ENCRE2)
fig.suptitle("Variance expliquée par composante : la kernel PCA ne concentre pas mieux\n"
             f"fenêtres ±{DEMI} jours, seuil de surprise {SEUIL}, "
             f"échantillon de {N_ECH:,} fenêtres".replace(",", " "),
             fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.89))
fig.savefig(f"{FIGURES}/kernel_spectre.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 2. le piege du denominateur --------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
for ax, tronque, titre in (
        (axes[0], True, "Dénominateur tronqué (les 30 rendues) — le faux gain"),
        (axes[1], False, "Dénominateur correct (variance totale) — la réalité")):
    for media, _, _, _ in MEDIAS:
        r = resultats[media]
        y = [r["balayage"][g][1 if tronque else 0][:6].sum() * 100 for g in GAMMAS]
        ax.plot(GAMMAS, y, lw=1.7, marker="o", ms=4, color=r["couleur"],
                label=f"{r['nom']} — kernel")
        ax.axhline(r["var_lin"][:6].sum() * 100, lw=1.1, ls="--", color=r["couleur"],
                   alpha=0.55, label=f"{r['nom']} — linéaire")
    yb = [temoin["balayage"][g][1 if tronque else 0][:6].sum() * 100 for g in GAMMAS]
    ax.plot(GAMMAS, yb, lw=1.7, marker="s", ms=4, color=GRIS,
            label="bruit blanc (témoin)")
    ax.axvline(GAMMAS[I_REF], lw=1.0, color=KERNEL, alpha=0.6)
    ax.annotate("γ = 1/D", (GAMMAS[I_REF], ax.get_ylim()[1]), xytext=(4, -10),
                textcoords="offset points", fontsize=8, color=KERNEL)
    ax.set_xscale("log")
    ax.set_xlabel("γ du noyau RBF (échelle log)")
    ax.set_ylabel("variance cumulée des 6 premières (%)")
    ax.set_ylim(0, 62)
    ax.set_title(titre, fontsize=9.5, color=ENCRE2)
    ax.legend(frameon=False, fontsize=7.5)
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
fig.suptitle("Le même calcul lu de deux façons : diviser par la somme des seules "
             "composantes retenues\nfabrique un gain qui disparaît dès qu'on rapporte "
             "à la variance totale", fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.87))
fig.savefig(f"{FIGURES}/kernel_piege.png", bbox_inches="tight", dpi=200)
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
fig.suptitle("Le nuage des fenêtres dans le plan des deux premières composantes :\n"
             "même continuum, aucun groupe que le noyau ferait apparaître",
             fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig(f"{FIGURES}/kernel_plan12.png", bbox_inches="tight", dpi=200)
plt.close(fig)

print(f"-> {os.path.relpath(FIGURES)} : kernel_spectre.png, kernel_piege.png, "
      "kernel_plan12.png")
