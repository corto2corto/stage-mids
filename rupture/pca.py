# PCA du modele zero sur le dataset de sauts (etapes 5 et 6 du to_do).
# Charge fenetres_<media>.npz et compare trois normalisations :
#   z   : z-score LE LONG de chaque fenetre (defaut de l'analyse)
#   01  : chaque fenetre ramenee sur [0, 1]
#   col : standardisation colonne par colonne — ce que fait l'option integree
#         des fonctions de PCA cle en main ; temoin pour la remarque de
#         Benoit, pas une normalisation candidate
# Les fenetres plates (ecart-type ou amplitude nulle) sont ecartees et
# comptees. Puis PCA classique sur chaque matrice : centrage des colonnes,
# SVD, variance expliquee = S^2 / somme.
#
# V2 (22/07/2026) — nettoyage des jours a corpus quasi vide (N_t minuscule
# => f_t = X_t/N_t explose et fabrique de fausses formes, cf. journal) :
# dans chaque fenetre, les jours a N_t < seuil sont remplaces par
# l'interpolation lineaire des jours sains voisins (extension constante aux
# bords) ; les fenetres dont le JOUR CENTRAL est quasi vide sont ecartees
# (le pic est statistiquement valide mais la forme n'est pas exploitable).
# seuil par defaut 5000 (les jours < 5000 forment une population a part :
# 321 jours sur 26 917, plateau net au-dela) ; seuil 0 = pas de nettoyage
# (reproduit la V1, fichiers sans suffixe ; sinon suffixe _v2).
# Sorties :
# - <VOCAB_DIR>/pca_<media>_<norme>.npz : composantes (31 x 31, une par
#   ligne), variance expliquee, projections float32, indices des fenetres
#   gardees dans fenetres_<media>.npz
# - rupture/sorties/pca_<media>_variance.png : variance expliquee comparee
# - rupture/sorties/pca_<media>_composantes.png : profils temporels des 6
#   premieres composantes (z, avec 01 superpose au signe pres)
# Usage : python -m rupture.pca [media] [seuil]     (seuil defaut 5000, 0 = V1)
import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.graphes import BLEU, VERT, ORANGE, GRILLE, ENCRE2

DEMI = 15
SORTIES = f"{os.path.dirname(os.path.abspath(__file__))}/sorties"


def normaliser(F, norme):
    """Matrice normalisee + indices des fenetres gardees."""
    F = F.astype(np.float64)
    if norme == "z":
        ecart = F.std(axis=1)
        garde = ecart > 0
        F = F[garde]
        F = (F - F.mean(axis=1, keepdims=True)) / F.std(axis=1, keepdims=True)
    elif norme == "01":
        amplitude = F.max(axis=1) - F.min(axis=1)
        garde = amplitude > 0
        F = F[garde]
        F = (F - F.min(axis=1, keepdims=True)) / (F.max(axis=1, keepdims=True)
                                                  - F.min(axis=1, keepdims=True))
    elif norme == "col":
        garde = np.ones(len(F), bool)
        F = (F - F.mean(axis=0)) / F.std(axis=0)
    else:
        raise ValueError(f"norme inconnue : {norme}")
    return F, np.where(garde)[0]


def pca(F):
    """Centrage colonne + SVD ; renvoie (composantes en lignes, part de
    variance expliquee, projections)."""
    Fc = F - F.mean(axis=0)
    U, S, Vt = np.linalg.svd(Fc, full_matrices=False)
    return Vt, S**2 / (S**2).sum(), U * S


def nettoyer(F, N_fen, seuil, demi=DEMI):
    """Interpole f_t sur les jours a N_t < seuil, ecarte les centres quasi
    vides. Renvoie (F nettoyee, indices gardes, jours interpoles, fenetres
    touchees)."""
    garde = np.where(N_fen[:, demi] >= seuil)[0]
    F = F[garde].astype(np.float64).copy()
    mauvais = N_fen[garde] < seuil
    x = np.arange(F.shape[1])
    for i in np.where(mauvais.any(axis=1))[0]:
        bon = ~mauvais[i]
        F[i, mauvais[i]] = np.interp(x[mauvais[i]], x[bon], F[i, bon])
    return F, garde, int(mauvais.sum()), int(mauvais.any(axis=1).sum())


if __name__ == "__main__":
    media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
    seuil = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    suffixe = "_v2" if seuil else ""
    DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
    debut = time.time()
    d = np.load(f"{DOSSIER}/fenetres_{media}.npz")
    F0 = d["fenetres"]
    print(f"{media} : {F0.shape[0]} fenetres x {F0.shape[1]} jours, "
          f"seuil quasi-vide = {seuil}", flush=True)

    idx0 = np.arange(len(F0))
    if seuil:
        g = np.load(f"{DOSSIER}/vocab_series_{media}.npz")
        position = {int(dt): i for i, dt in enumerate(g["dates"])}
        pos = np.array([position[int(dt)] for dt in d["date"]])
        N_fen = g["N"][pos[:, None] + np.arange(-DEMI, DEMI + 1)]
        F0, idx0, n_jours, n_fen = nettoyer(F0, N_fen, seuil)
        print(f"  nettoyage : {len(idx0)} fenetres gardees "
              f"({len(d['fenetres']) - len(idx0)} centres quasi vides ecartes), "
              f"{n_jours} jours interpoles dans {n_fen} fenetres", flush=True)

    resultats = {}
    for norme in ("z", "01", "col"):
        F, garde = normaliser(F0, norme)
        composantes, variance, proj = pca(F)
        resultats[norme] = (composantes, variance, garde)
        np.savez_compressed(
            f"{DOSSIER}/pca_{media}_{norme}{suffixe}.npz",
            composantes=composantes, variance=variance,
            projections=proj.astype(np.float32), garde=idx0[garde])
        print(f"  {norme:>3} : {len(F)} fenetres ({len(F0) - len(F)} plates "
              f"ecartees), 6 premieres composantes : "
              f"{np.round(variance[:6] * 100, 1)} % de variance", flush=True)

    # figure 1 : variance expliquee comparee (echelle log en y ; on s'arrete a
    # 30 composantes — la 31e du z-score est degeneree, le centrage par ligne
    # enleve un degre de liberte)
    os.makedirs(SORTIES, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    rangs = np.arange(1, 31)
    for norme, coul, nom in (("z", BLEU, "z-score par fenêtre"),
                             ("01", VERT, "min-max [0, 1] par fenêtre"),
                             ("col", ORANGE, "colonne par colonne (témoin)")):
        v = resultats[norme][1][:30] * 100
        ax.plot(rangs, v, lw=1.6, color=coul, label=nom)
        ax.scatter(rangs[:1], v[:1], s=14, color=coul)
        ax.annotate(f"{v[0]:.1f} %".replace(".", ","), (1, v[0]),
                    xytext=(6, 3), textcoords="offset points",
                    fontsize=8, color=ENCRE2)
    ax.set_yscale("log")
    ax.set_ylim(0.3, 130)
    ax.set_xlabel("rang de la composante")
    ax.set_ylabel("variance expliquée (%)")
    ax.set_xlim(0.5, 30.5)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.set_title(f"PCA des fenêtres de sauts ({media}) — variance par composante",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout()
    fig.savefig(f"{SORTIES}/pca_{media}_variance{suffixe}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)

    # figure 2 : profils temporels des 6 premieres composantes (z, 01 superpose
    # au signe pres — le signe d'une composante est arbitraire)
    comp_z, var_z, _ = resultats["z"]
    comp_01, var_01, _ = resultats["01"]
    js = np.arange(-DEMI, DEMI + 1)
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.2), sharex=True)
    for k, ax in enumerate(axes.flat):
        c01 = comp_01[k] * np.sign(comp_z[k] @ comp_01[k] or 1.0)
        ax.axhline(0, lw=.6, color=GRILLE)
        ax.axvline(0, lw=.6, color=GRILLE)
        ax.plot(js, c01, lw=1.2, color=VERT, ls="--",
                label="[0, 1]" if k == 0 else None)
        ax.plot(js, comp_z[k], lw=1.6, color=BLEU,
                label="z-score" if k == 0 else None)
        ax.set_title(f"composante {k + 1} — z : {var_z[k] * 100:.1f} %, "
                     f"[0,1] : {var_01[k] * 100:.1f} %", fontsize=8.5, color=ENCRE2)
        ax.set_xticks([-DEMI, 0, DEMI])
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    axes[0, 0].legend(frameon=False, fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("jours de parution autour du pic")
    fig.suptitle(f"PCA des fenêtres de sauts ({media}) — profils temporels "
                 "des premières composantes", fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(f"{SORTIES}/pca_{media}_composantes{suffixe}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)

    print(f"FINI en {time.time() - debut:.0f} s -> pca_{media}_<norme>{suffixe}.npz, "
          f"{os.path.relpath(SORTIES)}/pca_{media}_*{suffixe}.png", flush=True)
