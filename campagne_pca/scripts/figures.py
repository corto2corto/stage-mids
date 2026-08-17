# Toutes les figures de la campagne PCA, en un point d'entree unique. Remplace
# les neuf anciens scripts figures_*.py ; les briques communes (style, chaine
# pics -> NMS -> fenetres -> z-score -> PCA, vues partagees) sont dans figures_lib.
#
# Les noms des png produits sont inchanges : les .qmd n'ont pas bouge.
# Usage : .venv/bin/python -m campagne_pca.scripts.figures <commande> [options]
#   config <media>    les 5 vues d'une configuration (spectre, composantes,
#                     plan12, archetypes, reconstruction)
#   comp <media>      la planche d'une seule composante (12 sauts les plus alignes)
#   comparaison       profils compares de plusieurs configurations (--jeu medias|hebdo)
#   synthese          effets des hyperparametres + carte des medias
#   kernel            kernel PCA (RBF) contre PCA lineaire, avec le piege du denominateur
#   grille-plans      plans PC1-PC2 de la grille de gamma, un journal par figure
#   kernel-resume     tableau de synthese kernel + plans, pour kernel_hebdo.qmd
import argparse
import glob
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

import campagne_pca.scripts.figures_lib as lib
from campagne_pca.scripts.figures_lib import AXE, ENCRE, ENCRE2, GRILLE, GRIS
from campagne_pca.scripts.configs import JEUX
from rupture.pca import pca

# Decalages manuels des etiquettes du plan PC1-PC2, par prefixe de sortie : le
# placement automatique se chevauche sur certaines configurations. (dx, dy, ha)
DECALAGES = {
    "optimale": {"francisco": (9, 4, "left"), "algérie": (-9, -14, "right"),
                 "mitterrand": (9, 6, "left"), "chirac": (11, -15, "left"),
                 "attentats": (9, 11, "left"), "jaunes": (2, -18, "left")},
}

# Noms de composantes retenus apres inspection, par prefixe de sortie.
LIBELLES = {
    "optimale": ["pic confiné au bloc du saut", "montée progressive, chute brutale",
                 "changement de niveau avant/après", "pic élargi, creux encadrants",
                 "oscillation lente", "oscillation rapide"],
}


# --- config : les cinq vues d'une configuration ------------------------------

def donnees(a):
    """Le cache de la configuration s'il existe, sinon la chaine complete."""
    d = lib.depuis_cache(a.prefixe)
    if d is not None:
        print(f"{a.prefixe} : lu depuis le cache ({len(d.Z)} fenetres x {d.D} blocs)")
        return d
    return lib.charger(a.media, a.demi, a.seuil, a.pics, a.nettoie)


def cmd_config(a):
    d = donnees(a)
    pres = lib.presentation(a.media_nom, a.demi, a.seuil, a.pas_jours, a.couleur,
                            a.accent, LIBELLES.get(a.prefixe))
    print(f"{a.media} d{a.demi} s{a.seuil:g} : {len(d.Z)} fenetres x {d.D} blocs | "
          f"K50={d.K50} (K50_frac={d.K50 / d.rang:.2f}), "
          f"cum6={d.cum[min(5, d.rang - 1)] * 100:.1f} %")
    print("variance des 6 premieres (%) :", np.round(d.variance[:6] * 100, 1))
    lib.formes(d)

    seuil_vol, eligibles = lib.filtre_volume(d.volume, a.vol_q, a.vol_min, 3)
    lib.vue_spectre(d, pres, lib.sortie(f"{a.prefixe}_spectre.png"))
    lib.vue_composantes(d, pres, lib.sortie(f"{a.prefixe}_composantes.png"))
    lib.vue_plan12(d, pres, lib.sortie(f"{a.prefixe}_plan12.png"),
                   DECALAGES.get(a.prefixe))
    lib.vue_archetypes(d, pres, lib.sortie(f"{a.prefixe}_archetypes.png"),
                       seuil_vol, eligibles)
    lib.vue_reconstruction(d, pres, lib.sortie(f"{a.prefixe}_reconstruction.png"))
    print(f"-> {lib.FIGURES.relative_to(Path.cwd())} : "
          + ", ".join(f"{a.prefixe}_{v}.png" for v in
                      ("spectre", "composantes", "plan12", "archetypes", "reconstruction")))


# --- comp : la planche d'une seule composante --------------------------------

def cmd_comp(a):
    d = donnees(a)
    pres = lib.presentation(a.media_nom, a.demi, a.seuil, a.pas_jours, a.couleur,
                            a.accent, LIBELLES.get(a.prefixe))
    K = a.comp - 1
    v = d.composantes[K]
    centre = (v[np.abs(d.js) <= d.demi // 4] ** 2).sum() / (v ** 2).sum()
    print(f"{a.media} d{a.demi} s{a.seuil:g} : {len(d.Z)} fenetres | comp {a.comp} = "
          f"{d.variance[K] * 100:.1f} % | {int((np.diff(np.sign(v)) != 0).sum())} "
          f"croisements, {centre * 100:.0f} % d'energie au centre")

    seuil_vol, eligibles = lib.filtre_volume(d.volume, a.vol_q, a.vol_min, 12)
    chemin = lib.sortie(f"{a.prefixe}_comp{a.comp}_archetypes.png")
    lib.vue_comp_archetypes(d, pres, chemin, a.comp, seuil_vol, eligibles)
    print(f"-> {chemin.relative_to(Path.cwd())}")


# --- comparaison : profils compares de plusieurs configurations --------------

def cmd_comparaison(a):
    jeu = JEUX[a.jeu]
    chemin = lib.sortie(jeu["sortie"])
    lib.vue_comparaison(jeu["lignes"], jeu["titre"], jeu["rect"], chemin)
    print(f"-> {chemin.relative_to(Path.cwd())}")


# --- synthese : effets des hyperparametres, carte des medias -----------------

def cmd_synthese(a):
    r = lib.donnees_synthese()
    print(f"{len(r)} lignes (cellules completes x 4 medias), "
          f"{r['cellule'].nunique()} cellules")

    chemin = lib.sortie("synthese_axes.png")
    lib.vue_synthese_axes(r, chemin)
    print(f"-> {chemin.relative_to(Path.cwd())}")

    chemin = lib.sortie("synthese_carte_medias.png")
    lib.vue_synthese_carte(r, chemin)
    print(f"-> {chemin.relative_to(Path.cwd())}")

    for col, titre, _, ordre in lib.AXES_SYNTHESE:  # tableau des moyennes, pour le rapport
        m = r.groupby(col)[["exces6", "alignement6"]].mean().loc[ordre].round(3)
        print(f"\n{titre} :\n{m.to_string()}")


# --- kernel : kernel PCA (RBF) contre PCA lineaire ---------------------------
#
# ATTENTION AU DENOMINATEUR. sklearn KernelPCA(n_components=k).eigenvalues_ ne
# rend que k valeurs propres. Les diviser par LEUR PROPRE SOMME ne donne pas la
# part de variance : la variance totale dans l'espace induit par le noyau est la
# trace de la matrice de Gram centree, dont le rang va jusqu'a N (pas k). Avec le
# denominateur tronque on lit un gain spectaculaire qui n'existe pas. Ici on
# calcule les deux, et la figure 2 montre l'ecart — c'est le resultat principal.
#   trace(Kc) = trace(K) - somme(K)/N, et trace(K) = N pour le noyau RBF.
# La matrice de Gram est N x N : a 123k fenetres elle saturerait la RAM (~120 Go)
# -> echantillon de N_ECH fenetres, le meme pour les deux methodes.

KERNEL_DEMI, KERNEL_SEUIL = 15, 4
N_ECH, GRAINE = 8000, 0
KERNEL_MEDIAS = [("lemonde", "", "Le Monde", "#1a1a1a"),
                 ("lesechos", "_s3", "Les Échos", "#9b2226")]
KERNEL_BLEU = "#2a78d6"
GAMMAS = np.array([0.003, 0.01, 0.0323, 0.1, 0.3, 1.0])   # 0.0323 = 1/31 = 1/D
I_REF = 2                                                  # indice de gamma = 1/D


def kernel_variance(M, gamma, rang):
    """(part de variance CORRECTE, part avec denominateur TRONQUE, projections).

    La matrice de Gram est calculee une seule fois et passee en 'precomputed'
    pour ne pas la garder deux fois en memoire."""
    from sklearn.decomposition import KernelPCA
    from sklearn.metrics.pairwise import rbf_kernel
    K = rbf_kernel(M, gamma=gamma)
    total = np.trace(K) - K.sum() / len(K)      # trace de la Gram centree
    k = KernelPCA(n_components=rang, kernel="precomputed")
    proj = k.fit_transform(K)
    del K
    lam = k.eigenvalues_
    return lam / total, lam / lam.sum(), proj


def cmd_kernel(a):
    rng = np.random.default_rng(GRAINE)
    resultats = {}
    for media, pics, nom, couleur in KERNEL_MEDIAS:
        Z = lib.charger(media, KERNEL_DEMI, KERNEL_SEUIL, pics).Z
        n_total = len(Z)
        Z = Z[rng.choice(n_total, N_ECH, replace=False)] if n_total > N_ECH else Z
        D = Z.shape[1]
        rang = D - 1

        _, var_lin, proj_lin = pca(Z)
        balayage = {g: kernel_variance(Z, g, rang) for g in GAMMAS}
        var_ker, _, proj_ker = balayage[GAMMAS[I_REF]]
        resultats[media] = dict(nom=nom, couleur=couleur, n_total=n_total, D=D, rang=rang,
                                var_lin=var_lin, var_ker=var_ker, proj_lin=proj_lin,
                                proj_ker=proj_ker, balayage=balayage)
        print(f"{nom} : {n_total} fenetres ({len(Z)} echantillonnees) x {D} blocs")
        print(f"  lineaire   : comp1 {var_lin[0] * 100:5.2f} %, "
              f"cum6 {var_lin[:6].sum() * 100:5.2f} %")
        for g in GAMMAS:
            ok, tronque, _ = balayage[g]
            print(f"  RBF g={g:<6.4g} : comp1 {ok[0] * 100:5.2f} %, "
                  f"cum6 {ok[:6].sum() * 100:5.2f} % | tronque : "
                  f"comp1 {tronque[0] * 100:5.2f} %, cum6 {tronque[:6].sum() * 100:5.2f} % "
                  f"| les {rang} premieres pesent {ok.sum() * 100:5.1f} % du total")

    # Temoin : bruit blanc z-score par ligne, meme forme, aucune structure temporelle.
    D = resultats[KERNEL_MEDIAS[0][0]]["D"]
    rang = D - 1
    B = rng.standard_normal((N_ECH, D))
    B = (B - B.mean(axis=1, keepdims=True)) / B.std(axis=1, keepdims=True)
    _, var_lin_b, _ = pca(B)
    balayage_b = {g: kernel_variance(B, g, rang)[:2] for g in GAMMAS}
    temoin = dict(var_lin=var_lin_b, balayage=balayage_b)
    print(f"\ntemoin bruit blanc ({N_ECH} x {D}) :")
    print(f"  lineaire   : comp1 {var_lin_b[0] * 100:5.2f} %, "
          f"cum6 {var_lin_b[:6].sum() * 100:5.2f} %")
    for g in GAMMAS:
        ok, tronque = balayage_b[g]
        print(f"  RBF g={g:<6.4g} : comp1 {ok[0] * 100:5.2f} %, "
              f"cum6 {ok[:6].sum() * 100:5.2f} % | tronque : "
              f"comp1 {tronque[0] * 100:5.2f} %, cum6 {tronque[:6].sum() * 100:5.2f} %")

    # 1. spectre compare
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for ax, (media, _, _, _) in zip(axes, KERNEL_MEDIAS):
        r = resultats[media]
        rangs = np.arange(1, r["rang"] + 1)
        isotrope = 100 / r["rang"]
        ax.plot(rangs, r["var_lin"][:r["rang"]] * 100, lw=1.8, color=r["couleur"],
                label="PCA linéaire")
        ax.plot(rangs, r["var_ker"][:r["rang"]] * 100, lw=1.8, color=KERNEL_BLEU,
                label="kernel PCA (RBF, γ=1/D)")
        ax.axhline(isotrope, lw=1.0, ls="--", color=GRIS,
                   label=f"nuage sans structure ({isotrope:.1f} %)".replace(".", ","))
        for v, coul in ((r["var_lin"], r["couleur"]), (r["var_ker"], KERNEL_BLEU)):
            ax.scatter([1], [v[0] * 100], s=18, color=coul, zorder=3)
        ax.annotate(f"{r['var_lin'][0] * 100:.1f} %".replace(".", ","),
                    (1, r["var_lin"][0] * 100), xytext=(8, 3),
                    textcoords="offset points", fontsize=8.5, color=ENCRE2)
        ax.set_yscale("log")
        ax.set_xlabel("rang de la composante")
        ax.set_ylabel("variance expliquée (%)")
        ax.set_xlim(0.5, r["rang"] + 0.5)
        ax.set_xticks([1] + list(range(5, r["rang"] + 1, 5)))
        ax.legend(frameon=False, fontsize=8)
        lib.cadre(ax)
        ax.set_title(f"{r['nom']} — cum6 : {r['var_lin'][:6].sum() * 100:.1f} % en "
                     f"linéaire, {r['var_ker'][:6].sum() * 100:.1f} % en "
                     f"kernel".replace(".", ","), fontsize=9.5, color=ENCRE2)
    fig.suptitle("Variance expliquée par composante : la kernel PCA ne concentre pas "
                 f"mieux\nfenêtres ±{KERNEL_DEMI} jours, seuil de surprise "
                 f"{KERNEL_SEUIL}, échantillon de {N_ECH:,} fenêtres".replace(",", " "),
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.89))
    fig.savefig(lib.sortie("kernel_spectre.png"), bbox_inches="tight", dpi=200)
    plt.close(fig)

    # 2. le piege du denominateur
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for ax, tronque, titre in (
            (axes[0], True, "Dénominateur tronqué (les 30 rendues) — le faux gain"),
            (axes[1], False, "Dénominateur correct (variance totale) — la réalité")):
        for media, _, _, _ in KERNEL_MEDIAS:
            r = resultats[media]
            y = [r["balayage"][g][1 if tronque else 0][:6].sum() * 100 for g in GAMMAS]
            ax.plot(GAMMAS, y, lw=1.7, marker="o", ms=4, color=r["couleur"],
                    label=f"{r['nom']} — kernel")
            ax.axhline(r["var_lin"][:6].sum() * 100, lw=1.1, ls="--", color=r["couleur"],
                       alpha=0.55, label=f"{r['nom']} — linéaire")
        yb = [temoin["balayage"][g][1 if tronque else 0][:6].sum() * 100 for g in GAMMAS]
        ax.plot(GAMMAS, yb, lw=1.7, marker="s", ms=4, color=GRIS,
                label="bruit blanc (témoin)")
        ax.axvline(GAMMAS[I_REF], lw=1.0, color=KERNEL_BLEU, alpha=0.6)
        ax.annotate("γ = 1/D", (GAMMAS[I_REF], ax.get_ylim()[1]), xytext=(4, -10),
                    textcoords="offset points", fontsize=8, color=KERNEL_BLEU)
        ax.set_xscale("log")
        ax.set_xlabel("γ du noyau RBF (échelle log)")
        ax.set_ylabel("variance cumulée des 6 premières (%)")
        ax.set_ylim(0, 62)
        ax.set_title(titre, fontsize=9.5, color=ENCRE2)
        ax.legend(frameon=False, fontsize=7.5)
        lib.cadre(ax)
    fig.suptitle("Le même calcul lu de deux façons : diviser par la somme des seules "
                 "composantes retenues\nfabrique un gain qui disparaît dès qu'on "
                 "rapporte à la variance totale", fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.87))
    fig.savefig(lib.sortie("kernel_piege.png"), bbox_inches="tight", dpi=200)
    plt.close(fig)

    # 3. plan des deux premieres composantes
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 7.4))
    for ligne, (media, _, _, _) in enumerate(KERNEL_MEDIAS):
        r = resultats[media]
        cmap = lib.cmap_media(r["couleur"])
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
    fig.savefig(lib.sortie("kernel_plan12.png"), bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"-> {lib.FIGURES.relative_to(Path.cwd())} : kernel_spectre.png, kernel_piege.png, "
          "kernel_plan12.png")


# --- grille de gamma : plans PC1-PC2 et tableau de synthese ------------------
#
# Les projections kernel sont deja calculees et stockees (kernel_grille.py, 50
# vecteurs propres par grille_*.npz) ; seule la PCA lineaire est rejouee ici
# (cout negligeable : SVD sur N x 21, pas de Gram). Les parts de variance
# affichees viennent du spectre ENTIER stocke (lam/total), pas des 50 valeurs
# retenues — sinon on retombe dans le piege du denominateur ci-dessus.

GRILLE_MEDIAS = [("mediapart7j", "_s3", "Mediapart", "#fc392b"),
                 ("lesechos7j", "_s3", "Les Échos", "#b00005"),
                 ("lefigaro7j", "_s3", "Le Figaro", "#163860")]


def spectre_grille(media, demi, seuil, mult):
    """Le .npz d'un point de la grille de gamma (kernel_grille.py)."""
    motif = lib.SPECTRES / f"grille_{media}_d{demi}_s{seuil:g}_m{mult:g}_g*.npz"
    return np.load(glob.glob(str(motif))[0], allow_pickle=True)


def cmd_grille_plans(a):
    demi, seuil = 10, 4.0
    mults = (0.1, 0.25, 0.5, 1, 2, 4, 10, 30)
    for media, pics, nom, couleur in GRILLE_MEDIAS:
        cmap = lib.cmap_media(couleur)
        d = lib.charger(media, demi, seuil, pics)
        proj_lin, var_lin = d.proj, d.variance

        fig, axes = plt.subplots(3, 3, figsize=(10.2, 10.2))
        ax = axes.flat[0]
        hb = ax.hexbin(proj_lin[:, 0], proj_lin[:, 1], gridsize=42, bins="log",
                       cmap=cmap, linewidths=0.2)
        fig.colorbar(hb, ax=ax, shrink=0.82, label="fenêtres (log)")
        ax.set_xlabel(f"PC1 ({var_lin[0] * 100:.1f} %)".replace(".", ","))
        ax.set_ylabel(f"PC2 ({var_lin[1] * 100:.1f} %)".replace(".", ","))
        ax.set_title("PCA linéaire", fontsize=9.5, color=ENCRE2)

        for k, mult in enumerate(mults):
            g = spectre_grille(media, demi, seuil, mult)
            proj, gamma = g["proj"], float(g["gamma"])
            v = np.clip(g["lam"], 0, None) / float(g["total"])   # spectre entier
            ax = axes.flat[k + 1]
            hb = ax.hexbin(proj[:, 0], proj[:, 1], gridsize=42, bins="log",
                           cmap=cmap, linewidths=0.2)
            fig.colorbar(hb, ax=ax, shrink=0.82, label="fenêtres (log)")
            ax.set_xlabel(f"PC1 ({v[0] * 100:.1f} %)".replace(".", ","))
            ax.set_ylabel(f"PC2 ({v[1] * 100:.1f} %)".replace(".", ","))
            ax.set_title(f"γ = {mult:g}·γ_méd = {gamma:.3g}", fontsize=9.5, color=ENCRE2)

        fig.suptitle(f"{nom} — plan des deux premières composantes, linéaire puis "
                     f"kernel RBF de γ_méd/10 à 30·γ_méd\n"
                     "même continuum partout : le noyau ne fait jamais apparaître "
                     "de groupe", fontsize=10, color=ENCRE2)
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        chemin = lib.sortie(f"grille_plan12_{media}.png")
        fig.savefig(chemin, bbox_inches="tight", dpi=170)
        plt.close(fig)
        print(f"-> {chemin.relative_to(lib.ICI)}")


# Trois gamma retenus sur les huit de la grille, memes multiplicateurs pour les
# trois journaux (gamma_med differe par journal, le choix des points non) :
#   x0,1 : le plus proche du lineaire, teste si un petit gamma peut au moins
#          egaler la PCA classique
#   x1   : gamma_med, le reglage cale sur l'echelle reelle des distances
#   x30  : le regime degenere, piece a conviction du mecanisme
# comp1 et cum6 ne racontent pas le meme phenomene : cum6 dilue avec le nombre de
# rangs disponibles (plus eleve en kernel), comp1 compare la MEILLEURE direction
# unique des deux methodes sans cet artefact. K50/K90 (composantes pour 50 %/90 %
# de variance) mesurent directement l'etalement.
RESUME_MULTS = (0.1, 1, 30)
RESUME_COLONNES = ["", "linéaire", "0,1 · γ_méd", "γ_méd", "30 · γ_méd"]


def cmd_kernel_resume(a):
    demi, seuil = a.demi, a.seuil
    medias = [(f"mediapart{a.suffixe_media}", "Mediapart", "#fc392b"),
              (f"lesechos{a.suffixe_media}", "Les Échos", "#b00005"),
              (f"lefigaro{a.suffixe_media}", "Le Figaro", "#163860")]

    def lire(media, mult=None):
        """Spectre entier -> (n, comp1 %, K50, K90, gamma) ; mult=None = lineaire."""
        g = spectre_grille(media, demi, seuil, 1)
        n = int(g["n"])
        if mult is None:
            v = g["var_lin"]
        else:
            g = spectre_grille(media, demi, seuil, mult)
            v = np.clip(g["lam"], 0, None) / float(g["total"])
        c = np.cumsum(v)
        return (n, v[0] * 100, int(np.searchsorted(c, 0.5)) + 1,
                int(np.searchsorted(c, 0.9)) + 1,
                float(g["gamma"]) if mult is not None else None)

    lignes = []   # (type, texte_col0, [4 valeurs formatees], couleur_accent ou None)
    for media, nom, couleur in medias:
        n, c1_lin, k50_lin, k90_lin, _ = lire(media)
        gammas = [lire(media, m) for m in RESUME_MULTS]
        gamma_med = gammas[1][4]
        lignes.append(("media", f"{nom} — {n:,}".replace(",", " ") + " fenêtres, "
                       f"γ_méd = {gamma_med:.4f}".replace(".", ","), None, couleur))
        lignes.append(("val", "comp1 (%)", [f"{c1_lin:.2f}".replace(".", ",")]
                       + [f"{g[1]:.2f}".replace(".", ",") for g in gammas], None))
        lignes.append(("val", "K50", [f"{k50_lin:,}".replace(",", " ")]
                       + [f"{g[2]:,}".replace(",", " ") for g in gammas], None))
        lignes.append(("val", "K90", [f"{k90_lin:,}".replace(",", " ")]
                       + [f"{g[3]:,}".replace(",", " ") for g in gammas], None))

    H_ENTETE, H_MEDIA, H_VAL = 0.9, 0.75, 0.62
    hauteur = H_ENTETE + sum(H_MEDIA if t == "media" else H_VAL for t, *_ in lignes) + 0.3
    largeurs = [2.7, 1.35, 1.55, 1.35, 1.55]

    fig, ax = plt.subplots(figsize=(sum(largeurs) + 0.6, hauteur / 2.15))
    ax.set_xlim(0, sum(largeurs))
    ax.set_ylim(0, hauteur)
    ax.axis("off")
    x_cols = np.cumsum([0] + largeurs)
    y = hauteur - H_ENTETE
    for xc, w, texte in zip(x_cols, largeurs, RESUME_COLONNES):
        ax.text(xc + (0.12 if texte == "" else w / 2), y + H_ENTETE / 2, texte,
                ha="left" if texte == "" else "center", va="center",
                fontsize=10, fontweight="bold", color=ENCRE)
    ax.plot([0, sum(largeurs)], [y, y], lw=1.3, color=ENCRE)

    for typ, texte, valeurs, couleur in lignes:
        h = H_MEDIA if typ == "media" else H_VAL
        y -= h
        if typ == "media":
            ax.add_patch(plt.Rectangle((0, y), sum(largeurs), h, color=couleur,
                                       alpha=0.10, zorder=0))
            ax.add_patch(plt.Rectangle((0, y), 0.06, h, color=couleur, zorder=1))
            ax.text(0.20, y + h / 2, texte, ha="left", va="center",
                    fontsize=9.5, fontweight="bold", color=ENCRE2)
        else:
            ax.text(x_cols[0] + 0.35, y + h / 2, texte, ha="left", va="center",
                    fontsize=9, color=ENCRE2)
            for xc, w, val in zip(x_cols[1:], largeurs[1:], valeurs):
                ax.text(xc + w / 2, y + h / 2, val, ha="center", va="center",
                        fontsize=9, color=ENCRE)
            ax.plot([0, sum(largeurs)], [y, y], lw=0.5, color=AXE, zorder=0)

    chemin = lib.sortie(f"kernel_resume_tableau{a.sortie_suffixe}.png")
    fig.savefig(chemin, bbox_inches="tight", dpi=220, facecolor="white")
    plt.close(fig)
    print(f"-> {chemin.relative_to(lib.ICI)}")

    # plan PC1-PC2, memes 3 gamma que le tableau
    fig, axes = plt.subplots(3, 4, figsize=(11.2, 8.4))
    for ligne, (media, nom, couleur) in enumerate(medias):
        cmap = lib.cmap_media(couleur)
        d = lib.charger(media, demi, seuil, "_s3")
        panneaux = [(d.proj, d.variance, "linéaire")]
        for mult in RESUME_MULTS:
            g = spectre_grille(media, demi, seuil, mult)
            v = np.clip(g["lam"], 0, None) / float(g["total"])
            libelle = "0,1 · γ_méd" if mult == 0.1 else ("γ_méd" if mult == 1
                                                         else "30 · γ_méd")
            panneaux.append((g["proj"], v, libelle))

        for col, (proj, var, titre) in enumerate(panneaux):
            ax = axes[ligne, col]
            ax.hexbin(proj[:, 0], proj[:, 1], gridsize=35, bins="log", cmap=cmap,
                      linewidths=0.15)
            ax.set_xticks([])
            ax.set_yticks([])
            if ligne == 0:
                ax.set_title(titre, fontsize=10, color=ENCRE2)
            if col == 0:
                ax.set_ylabel(nom, fontsize=10, color=ENCRE2, fontweight="bold")
            ax.text(0.03, 0.03, f"PC1 {var[0] * 100:.1f} %".replace(".", ","),
                    transform=ax.transAxes, fontsize=7.5, color=ENCRE2, va="bottom")

    fig.suptitle("Plan des deux premières composantes : même continuum à chaque γ, "
                 "aucun groupe que le noyau ferait apparaître", fontsize=11, color=ENCRE)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    chemin = lib.sortie(f"kernel_resume_plans{a.sortie_suffixe}.png")
    fig.savefig(chemin, bbox_inches="tight", dpi=170, facecolor="white")
    plt.close(fig)
    print(f"-> {chemin.relative_to(lib.ICI)}")


# --- ligne de commande -------------------------------------------------------

def options_config(sp):
    """Options communes a `config` et `comp` (meme chaine, meme habillage)."""
    sp.add_argument("media")
    sp.add_argument("--demi", type=int, required=True)
    sp.add_argument("--seuil", type=float, required=True)
    sp.add_argument("--pas_jours", type=int, required=True,
                    help="taille d'un bloc, pour les libelles")
    sp.add_argument("--prefixe", required=True, help="prefixe des png de sortie")
    sp.add_argument("--media_nom", required=True,
                    help="nom du media pour les titres (ex. 'Les Échos')")
    sp.add_argument("--couleur", required=True,
                    help="couleur de charte du media (hex), pour les courbes")
    sp.add_argument("--accent", required=True,
                    help="couleur d'accent pour les annotations (repere, points) — "
                         "distincte de --couleur pour rester lisible")
    sp.add_argument("--pics", default="", help="suffixe du fichier pics (ex. _s3)")
    sp.add_argument("--nettoie", type=int, default=0,
                    help="seuil N_t sous lequel un jour est interpole (V2) ; 0 = desactive")
    sp.add_argument("--vol_q", type=float, default=50,
                    help="quantile de volume (occurrences brutes, max de la fenetre) sous "
                         "lequel une fenetre est ecartee du CHOIX DES ARCHETYPES ; "
                         "0 = pas de filtre. N'affecte pas la PCA.")
    sp.add_argument("--vol_min", type=int, default=50,
                    help="plancher absolu d'occurrences au pic pour un archetype, combine "
                         "au quantile par un max : sur un corpus court la mediane "
                         "elle-meme peut etre trop basse (Mediapart : 21 occurrences)")


def cmd_nommee(a):
    """Trace une configuration declaree dans configs.py, sans retaper ses parametres."""
    from types import SimpleNamespace
    from campagne_pca.scripts.configs import parametres
    p = parametres(a.nom)
    if p.get("libelles"):
        LIBELLES.setdefault(a.nom, p["libelles"])
    if p.get("decalages"):
        DECALAGES.setdefault(a.nom, p["decalages"])
    arg = SimpleNamespace(**{k: v for k, v in p.items()
                             if k not in ("libelles", "decalages")})
    if a.comp:
        arg.comp = a.comp
        return cmd_comp(arg)
    return cmd_config(arg)


ap = argparse.ArgumentParser(description=__doc__)
sous = ap.add_subparsers(dest="commande", required=True)

p = sous.add_parser("nommee", help="trace une configuration de configs.py")
p.add_argument("nom", help="ex. configA, hebdoMonde, optimale")
p.add_argument("--comp", type=int, default=None,
               help="ne tracer que la planche de cette composante")
p.set_defaults(fonction=cmd_nommee)

p = sous.add_parser("config", help="les 5 vues d'une configuration")
options_config(p)
p.set_defaults(fonction=cmd_config)

p = sous.add_parser("comp", help="la planche d'une seule composante")
options_config(p)
p.add_argument("--comp", type=int, default=3, help="numero de la composante (1-based)")
p.set_defaults(fonction=cmd_comp)

p = sous.add_parser("comparaison", help="profils compares de plusieurs configurations")
p.add_argument("--jeu", choices=sorted(JEUX), default="medias")
p.set_defaults(fonction=cmd_comparaison)

p = sous.add_parser("synthese", help="effets des hyperparametres + carte des medias")
p.set_defaults(fonction=cmd_synthese)

p = sous.add_parser("kernel", help="kernel PCA (RBF) contre PCA lineaire")
p.set_defaults(fonction=cmd_kernel)

p = sous.add_parser("grille-plans", help="plans PC1-PC2 de la grille de gamma")
p.set_defaults(fonction=cmd_grille_plans)

p = sous.add_parser("kernel-resume", help="tableau de synthese kernel + plans")
p.add_argument("--suffixe-media", default="7j",
               help="suffixe des noms de base (mediapart, lesechos, lefigaro)")
p.add_argument("--demi", type=int, default=10)
p.add_argument("--seuil", type=float, default=4.0)
p.add_argument("--sortie-suffixe", default="",
               help="suffixe des fichiers de sortie (ex. _3j)")
p.set_defaults(fonction=cmd_kernel_resume)

a = ap.parse_args()
a.fonction(a)
