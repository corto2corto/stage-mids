# Compare les reglages de desaisonnalisation sur la PCA des fenetres (seuils 4
# et 6), face aux fenetres d'origine (fenetres_unifie.npz) :
#   hebdo     : part des fenetres z-scorees dont l'autocorrelation a 7 jours
#               depasse 0,3 (signature du rythme de parution)
#   ac7_c1..4 : autocorrelation a 7 jours du profil de chaque composante
#   var1..var4: parts de variance des 4 premieres composantes
#   K50       : part des axes pour atteindre la moitie de la variance
#   cos1..cos4: cosinus de chaque composante d'origine avec la composante
#               corrigee la plus proche (parmi les 6 premieres)
#   fuite     : mediane de |S_pic| / f_t au pic (part du pic absorbee par S)
#   pic_perdu : part des fenetres dont le jour du pic n'est plus le maximum
# Sortie : campagne_pca/desaison/calibrage<pas>j.csv
# Usage : .venv/bin/python -m campagne_pca.desaison.scripts.calibrage <pas> <tag> [<tag> ...]
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from rupture.pca import normaliser, pca

pas, tags = int(sys.argv[1]), sys.argv[2:]
DATA = Path(__file__).resolve().parents[2] / "data"
ICI = Path(__file__).resolve().parents[1]
suffixe = "" if pas == 1 else f"{pas}j"


def analyser(fen, seuil):
    m = fen["surprise"] >= seuil
    Z, garde = normaliser(fen["fenetres"][m].astype(np.float64), "z")
    comp, var, _ = pca(Z)
    hebdo = float(((Z[:, :-7] * Z[:, 7:]).mean(axis=1) > .3).mean())
    k50 = int(np.searchsorted(np.cumsum(var), .5) + 1) / len(var)
    return dict(Z=Z, comp=comp, var=var, hebdo=hebdo, K50=k50, n=len(Z), m=m, garde=garde)


ref = np.load(DATA / "pics_unifie" / f"fenetres_unifie{suffixe}.npz")
lignes = []
for tag in ["origine"] + tags:
    fen = ref if tag == "origine" else np.load(DATA / "pics_desaison" / f"fenetres_{tag}{pas}j.npz")
    for s in (4, 6):
        a, o = analyser(fen, s), analyser(ref, s)
        ligne = dict(reglage=tag, seuil=s, n=a["n"], hebdo=round(a["hebdo"], 3),
                     K50=round(a["K50"], 3))
        for k in range(4):
            ligne[f"var{k + 1}"] = round(float(a["var"][k]), 3)
        for k in range(4):
            c = a["comp"][k]
            ligne[f"ac7_c{k + 1}"] = round(float((c[:-7] * c[7:]).sum() / (c * c).sum()), 2)
        for k in range(4):
            ligne[f"cos{k + 1}"] = round(float(np.abs(a["comp"][:6] @ o["comp"][k]).max()), 2)
        if tag != "origine":
            f_t, S_pic = fen["f_t"][a["m"]][a["garde"]], fen["S_pic"][a["m"]][a["garde"]]
            ligne["fuite"] = round(float(np.median(np.abs(S_pic) / f_t)), 3)
            F = fen["fenetres"][a["m"]][a["garde"]]
            ligne["pic_perdu"] = round(float((F[:, 15] < F.max(axis=1)).mean()), 3)
        lignes.append(ligne)
tab = pd.DataFrame(lignes)
tab.to_csv(ICI / f"calibrage{pas}j.csv", index=False)
print(tab.to_string(index=False))
