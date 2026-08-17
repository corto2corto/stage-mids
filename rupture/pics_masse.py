# Detection des pics sur tout le vocabulaire (phase 3, dataset de sauts) :
# boucle sequentielle sur les colonnes de vocab_series_<media>.npz avec le
# mecanisme valide de pics.py (bnb + double fit par defaut). Un mot dont le fit
# echoue (exception ou p-valeurs non finies) est consigne dans le .txt d'echecs
# et n'arrete pas la campagne. Sorties ecrites au fil de l'eau dans data/ :
# - pics_<media>.csv        : mot, date, X_t, N_t, f_t (pour 10^5), p_t, surprise
# - pics_<media>_echecs.txt : mot <tab> erreur
# Usage (sur gallica, en tmux) : python -m rupture.pics_masse [media] [loi] [fits] [surprise]
# Le 4e argument (campagne PCA, defaut 4 = comportement historique) abaisse ou
# remonte le seuil de selection ; s'il differe de 4, les sorties prennent le
# suffixe _s<surprise> pour ne pas toucher aux pics_<media>.csv livres.
import os
import sys
import time

import numpy as np

from rupture import pics

media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
loi = sys.argv[2] if len(sys.argv) > 2 else "bnb"
fits = int(sys.argv[3]) if len(sys.argv) > 3 else 2
surprise_min = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0
seuil = 10.0 ** -surprise_min
etiq = "" if surprise_min == 4.0 else f"_s{surprise_min:g}"
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")

d = np.load(f"{DOSSIER}/vocab_series_{media}.npz")
X, dates, N, mots = d["X"], d["dates"], d["N"], d["mots"]
print(f"{media} : {X.shape[1]} mots x {X.shape[0]} jours, loi={loi}, fits={fits}, "
      f"surprise min={surprise_min:g}", flush=True)
debut = time.time()
n_pics = n_echecs = 0

with open(f"{DOSSIER}/pics_{media}{etiq}.csv", "w") as fp, \
     open(f"{DOSSIER}/pics_{media}{etiq}_echecs.txt", "w") as fe:
    fp.write("mot,date,X_t,N_t,f_t,p_t,surprise\n")
    for j, mot in enumerate(mots):
        x = X[:, j].astype(float)
        try:
            params, p, garde = pics.ajuster(x, N, loi, fits)
            if not np.all(np.isfinite(p)):
                raise ValueError("p-valeurs non finies")
        except Exception as e:
            n_echecs += 1
            fe.write(f"{mot}\t{type(e).__name__}: {e}\n")
            fe.flush()
            continue
        for i in np.where(p < seuil)[0]:
            surprise = -np.log10(max(p[i], 1e-300))
            fp.write(f"{mot},{dates[i]},{int(x[i])},{N[i]},"
                     f"{x[i] / N[i] * 1e5:.2f},{p[i]:.6e},{surprise:.4f}\n")
        n_pics += int((p < seuil).sum())
        fp.flush()
        if (j + 1) % 25 == 0:
            ecoule = time.time() - debut
            reste = ecoule / (j + 1) * (len(mots) - j - 1)
            print(f"[{j + 1}/{len(mots)}] {n_pics} pics, {n_echecs} echecs | "
                  f"{ecoule / 60:.1f} min, reste ~{reste / 60:.0f} min", flush=True)

print(f"FINI : {n_pics} pics, {n_echecs} echecs sur {len(mots)} mots "
      f"en {(time.time() - debut) / 60:.1f} min", flush=True)
