# Exporte les fichiers de presentation d'une PCA de fenetres — les quatre
# fichiers decrits en fin de presentation_<nom>.qmd — avec exactement les
# calculs du .qmd : z-score de chaque fenetre, PCA separee aux seuils 4 et 6,
# composantes orientees vers la queue lourde des projections, seuil 4 aligne
# sur le seuil 6.
# Sorties dans <dossier> :
# - composantes_<nom>.npz          : 4 premieres composantes + parts de variance, par seuil
# - valeurs_propres_<nom>.csv      : 31 valeurs propres (S^2/(n-1)) par seuil
# - projections_<nom>.csv          : une ligne par fenetre, coefficients c1..c4 par seuil
# - tops_mots_composantes_<nom>.csv : 15 fenetres les mieux alignees par seuil,
#   composante et cote, avec un drapeau `parlant` (mot dans <vocab_parlant>)
# Usage : .venv/bin/python -m campagne_pca.scripts.exporter_presentation \
#             <fenetres.npz> <dossier> <nom> <vocab_parlant.txt>
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from rupture.pca import normaliser, pca

fenetres, dossier, nom, parlant = sys.argv[1:5]
dossier = Path(dossier)
dossier.mkdir(parents=True, exist_ok=True)
fen = np.load(fenetres)
PARLANT = set(Path(parlant).read_text(encoding="utf-8").split("\n")) - {""}
N_TOP, N_COMP = 15, 4

res = {}
for s in (4, 6):
    m = fen["surprise"] >= s
    Z, garde = normaliser(fen["fenetres"][m].astype(np.float64), "z")
    comp, var, proj = pca(Z)
    signes = np.sign((proj ** 3).sum(axis=0))
    comp, proj = comp * signes[:, None], proj * signes
    res[s] = dict(comp=comp, var=var, proj=proj, n=len(Z),
                  mot=fen["mot"][m][garde].astype(str), date=fen["date"][m][garde],
                  surprise=fen["surprise"][m][garde])
ali = np.sign(np.einsum("ij,ij->i", res[4]["comp"], res[6]["comp"]))
ali[ali == 0] = 1
res[4]["comp"] = res[4]["comp"] * ali[:, None]
res[4]["proj"] = res[4]["proj"] * ali

np.savez(dossier / f"composantes_{nom}.npz", blocs=np.arange(-15, 16),
         composantes_s4=res[4]["comp"][:N_COMP], variance_s4=res[4]["var"][:N_COMP],
         composantes_s6=res[6]["comp"][:N_COMP], variance_s6=res[6]["var"][:N_COMP])

# valeurs propres : la PCA renvoie les parts S^2/somme ; on remonte a S^2/(n-1)
# via la variance totale des fenetres z-scorees centrees
vp = {}
for s in (4, 6):
    Zc = res[s]["proj"]                     # U*S : variance totale = somme des S^2 / (n-1)
    total = (Zc ** 2).sum() / (res[s]["n"] - 1)
    vp[f"valeur_propre_s{s}"] = np.round(res[s]["var"] * total, 6)
pd.DataFrame(vp).to_csv(dossier / f"valeurs_propres_{nom}.csv", index=False)

# projections : les fenetres du seuil 4 (toutes), colonnes s6 vides sous 6
d4 = res[4]
cle6 = {(m, int(d), float(su)): i for i, (m, d, su) in
        enumerate(zip(res[6]["mot"], res[6]["date"], res[6]["surprise"]))}
idx6 = np.array([cle6.get((m, int(d), float(su)), -1)
                 for m, d, su in zip(d4["mot"], d4["date"], d4["surprise"])])
proj6 = np.full((len(d4["mot"]), N_COMP), np.nan)
proj6[idx6 >= 0] = res[6]["proj"][idx6[idx6 >= 0], :N_COMP]
tab = pd.DataFrame({"mot": d4["mot"], "date": d4["date"].astype(int),
                    "surprise": np.round(d4["surprise"].astype(float), 4)})
for k in range(N_COMP):
    tab[f"c{k + 1}_s4"] = np.round(d4["proj"][:, k], 4)
for k in range(N_COMP):
    tab[f"c{k + 1}_s6"] = np.round(proj6[:, k], 4)
tab.to_csv(dossier / f"projections_{nom}.csv", index=False)

lignes = []
for s in (4, 6):
    d = res[s]
    for k in range(N_COMP):
        ordre = np.argsort(d["proj"][:, k])
        for cote, sel in (("positif", ordre[::-1][:N_TOP]), ("negatif", ordre[:N_TOP])):
            for rang, i in enumerate(sel, start=1):
                lignes.append(dict(seuil=s, composante=k + 1, cote=cote, rang=rang,
                                   mot=d["mot"][i], date=int(d["date"][i]),
                                   surprise=round(float(d["surprise"][i]), 2),
                                   coefficient=round(float(d["proj"][i, k]), 4),
                                   parlant=int(d["mot"][i] in PARLANT)))
pd.DataFrame(lignes).to_csv(dossier / f"tops_mots_composantes_{nom}.csv", index=False)
print(f"{nom} : {res[4]['n']} fenetres au seuil 4, {res[6]['n']} au seuil 6 -> {dossier}")
