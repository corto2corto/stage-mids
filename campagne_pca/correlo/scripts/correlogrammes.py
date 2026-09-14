# Correlogrammes croises entre journaux autour des pics du corpus unifie
# (proposition de Simon C., 14/09/2026). Entree : fenetres_<nom>_<tag>.npz de
# rupture.fenetres_unifie_trio, tableau (n fenetres, M journaux, L jours) de
# frequences pour 10^5, centre sur le pic unifie. Les fenetres ou un journal est
# muet sur toute la periode (segment plat) sont deja ecartees a l'extraction.
#
# Pour chaque couple ordonne (A, B) et chaque decalage k de -demi a +demi, la
# correlation se calcule A TRAVERS LES FENETRES : les n couples (A_0, B_k), un
# par pic, donnent un Pearson (moyenne du produit des ecarts, divisee par le
# produit des ecarts-types, chaque position centree separement) et un Spearman
# (meme calcul sur les rangs). (A, B) et (B, A) different : la fenetre n'est pas
# stationnaire, le jour 0 est le pic.
# Deux lectures : brute (frequences telles quelles, dominees par le niveau de
# base du mot : un mot frequent est haut partout) et segment (chaque segment
# centre-reduit par sa propre moyenne et son ecart-type, comme dans la PCA : ne
# reste que la forme autour du pic).
#
# Usage : python -m campagne_pca.correlo.scripts.correlogrammes <npz> [seuil] [demi]
#   seuil : surprise minimale du pic unifie (defaut 5 = tout le fichier)
#   demi  : demi-largeur de lecture si le fichier est plus large (defaut : la sienne)
# Sortie : correlogrammes_<nom>_<tag>.csv dans campagne_pca/correlo/ (a, b, lag,
#   pearson, spearman, pearson_seg, spearman_seg, n) ; n identique partout.
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

chemin = Path(sys.argv[1])
seuil = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
d = np.load(chemin)
demi_fichier = int(d["demi"])
demi = int(sys.argv[3]) if len(sys.argv) > 3 else demi_fichier
assert demi <= demi_fichier and int(d["pas"]) == 1, "fenetre journaliere attendue"
medias = [str(m) for m in d["medias"]]
garde = d["surprise"] >= seuil
c = demi_fichier
Z = d["fenetres"][garde][:, :, c - demi:c + demi + 1].astype(np.float64)
muet = (Z.std(2) == 0).any(1)          # un journal muet sur la largeur lue
Z = Z[~muet]
n, M, L = Z.shape
print(f"{chemin.name} : {n} fenetres (surprise >= {seuil:g}, {int(muet.sum())} ecartees "
      f"pour un journal muet), {M} journaux, {L} jours (-{demi}..+{demi})", flush=True)


def standardiser(X):
    """Ecart a la moyenne sur les fenetres, divise par l'ecart-type, position par position."""
    return (X - X.mean(0)) / X.std(0)


Zs = (Z - Z.mean(2, keepdims=True)) / Z.std(2, keepdims=True)   # segment centre-reduit
lignes = []
for nom, T in (("pearson", Z), ("spearman", rankdata(Z, axis=0)),
               ("pearson_seg", Zs), ("spearman_seg", rankdata(Zs, axis=0))):
    S = standardiser(T)                                   # (n, M, L)
    for i, a in enumerate(medias):
        x0 = S[:, i, demi]                                # A au jour du pic
        for j, b in enumerate(medias):
            r = (x0[:, None] * S[:, j, :]).mean(0)        # corr(A_0, B_k), k = -demi..demi
            lignes.append(pd.DataFrame({"a": a, "b": b, "lag": np.arange(-demi, demi + 1),
                                        nom: r}))
res = pd.concat(lignes)
res = res.groupby(["a", "b", "lag"], sort=False).first().reset_index()
res["n"] = n
sortie = Path(__file__).parent.parent / f"correlogrammes_{chemin.stem.removeprefix('fenetres_')}.csv"
res.to_csv(sortie, index=False, float_format="%.4f")
seuil_bruit = 1.96 / np.sqrt(n)
print(f"-> {sortie} ({len(res)} lignes) ; bruit a 5 % : +/- {seuil_bruit:.3f}")
for a in medias:
    for b in medias:
        if a == b:
            continue
        r = res[(res.a == a) & (res.b == b)]
        k = int(r.loc[r.pearson.idxmax(), "lag"])
        print(f"  {a:12s} -> {b:12s} : pic de correlation a k={k:+d} "
              f"(pearson {r.pearson.max():.2f}, spearman {r.spearman.max():.2f}) ; "
              f"segment : k={int(r.loc[r.pearson_seg.idxmax(), 'lag']):+d} "
              f"(pearson {r.pearson_seg.max():.2f}, spearman {r.spearman_seg.max():.2f})")
