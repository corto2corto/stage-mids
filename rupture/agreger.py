# Agregation temporelle des series du vocabulaire (variante de timeline) :
# regroupe les jours de parution de vocab_series_<media>.npz en blocs de PAS
# jours consecutifs, non chevauchants — X et N sommes, date du bloc = jour du
# milieu. Les jours de fin qui ne remplissent pas un bloc entier sont ecartes.
# La sortie vocab_series_<media><pas>j.npz garde le meme schema que l'entree :
# toute la chaine (pics_masse, nms, fenetres_masse, pca) tourne dessus telle
# quelle avec media=<media><pas>j — DEMI et PORTEE se lisent alors en blocs
# (fenetre de +/-15 blocs = +/-45 jours de parution pour pas=3).
# Usage (sur gallica) : python -m rupture.agreger [media] [pas]
import os
import sys

import numpy as np

media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
pas = int(sys.argv[2]) if len(sys.argv) > 2 else 3
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")

d = np.load(f"{DOSSIER}/vocab_series_{media}.npz")
X, dates, N = d["X"], d["dates"], d["N"]
n = len(dates) // pas * pas
Xb = X[:n].reshape(-1, pas, X.shape[1]).sum(axis=1, dtype=np.int64).astype(np.int32)
Nb = N[:n].reshape(-1, pas).sum(axis=1)
dates_b = dates[:n].reshape(-1, pas)[:, pas // 2]

sortie = f"{DOSSIER}/vocab_series_{media}{pas}j.npz"
np.savez_compressed(sortie, X=Xb, dates=dates_b, N=Nb, mots=d["mots"], cles=d["cles"])
print(f"{media} : {len(dates)} jours -> {len(dates_b)} blocs de {pas} jours de "
      f"parution ({len(dates) - n} jour(s) de fin ecarte(s)), meme vocabulaire "
      f"({X.shape[1]} mots) -> {sortie}", flush=True)
