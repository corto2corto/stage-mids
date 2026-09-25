# Injecte dans composantes.html les données de l'outil : corpus unifié, blocs de 3 jours,
# ±15 blocs, seuil 6. Même calcul et même orientation des signes que la figure 6
# du rapport de stage (asymétrie des projections, puis composante 2 retournée).
# Lancer depuis la racine : python -m campagne_pca.outil_composantes.exporter_donnees
import json
import re
from pathlib import Path

import numpy as np

from rupture.pca import normaliser, pca

PAGE = Path(__file__).parent / "composantes.html"
fen = np.load("campagne_pca/data/pics_unifie/fenetres_unifie3j.npz")
Z, _ = normaliser(fen["fenetres"][fen["surprise"] >= 6].astype(np.float64), "z")
comp, var, proj = pca(Z)
signes = np.sign((proj ** 3).sum(axis=0))
comp, proj = comp * signes[:, None], proj * signes
comp[1] *= -1; proj[:, 1] *= -1           # comme FLIP = {1: -1} du rapport

donnees = dict(
    n=int(len(Z)),
    moyenne=np.round(Z.mean(axis=0), 5).tolist(),
    composantes=np.round(comp[:3], 5).tolist(),
    variance=np.round(var[:3], 5).tolist(),
    ecarts=np.round(proj[:, :3].std(axis=0), 5).tolist(),
    retournees=[2],
)
html = PAGE.read_text()
html = re.sub(r"/\*DONNEES\*/.*?/\*FIN\*/", lambda _: "/*DONNEES*/" + json.dumps(donnees) + "/*FIN*/", html, flags=re.S)
PAGE.write_text(html)
print(len(Z), var[:3], proj[:, :3].std(axis=0))
