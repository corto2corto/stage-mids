# Extraction en masse des fenetres +/-15 jours de parution autour des pics
# gardes par le NMS (phase 3, etapes 3 et 4 du to_do) : pour chaque ligne de
# pics_<media>_nms.csv, la fenetre de f_t (pour 10^5 mots) sur les 31 jours
# de parution centres sur le pic devient une ligne de la matrice. Les pics a
# moins de 15 jours de parution d'un bord de la grille sont ecartes et
# comptes (comme dans fenetres.py). Tout est vectorise : une passe d'indexage
# sur la matrice X du npz, pas de refit.
# Sortie : fenetres_<media>.npz avec
#   fenetres  float32 (n, 31)  f_t pour 10^5, colonnes j-15 ... j+15
#   mot, date, X_t, N_t, f_t, p_t, surprise, n_absorbes : metadonnees alignees
# Usage (sur gallica) : python -m rupture.fenetres_masse [media]
import os
import sys
import time

import numpy as np
import pandas as pd

DEMI = 15                                  # fenetre de 1 + 2*DEMI = 31 jours

media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")

debut = time.time()
d = np.load(f"{DOSSIER}/vocab_series_{media}.npz")
X, dates, N, mots = d["X"], d["dates"], d["N"], d["mots"]
position = {int(dt): i for i, dt in enumerate(dates)}
colonne = {m: j for j, m in enumerate(mots)}
pics = pd.read_csv(f"{DOSSIER}/pics_{media}_nms.csv")
print(f"{media} : {len(pics)} pics gardes, grille {X.shape[0]} jours x "
      f"{X.shape[1]} mots", flush=True)

pos = pics["date"].map(position).to_numpy()
col = pics["mot"].map(colonne).to_numpy()
if pics["mot"].map(colonne).isna().any():
    sys.exit("mots du csv absents du npz : " +
             str(pics.loc[pics["mot"].map(colonne).isna(), "mot"].unique()[:5]))

complet = (pos - DEMI >= 0) & (pos + DEMI < len(dates))
bords = int((~complet).sum())
pics, pos, col = pics[complet], pos[complet], col[complet].astype(int)

lignes = pos[:, None] + np.arange(-DEMI, DEMI + 1)         # (n, 31)
fenetres = (1e5 * X[lignes, col[:, None]] / N[lignes]).astype(np.float32)

chemin = f"{DOSSIER}/fenetres_{media}.npz"
np.savez_compressed(
    chemin, fenetres=fenetres,
    mot=pics["mot"].to_numpy(str), date=pics["date"].to_numpy(np.int32),
    X_t=pics["X_t"].to_numpy(np.int32), N_t=pics["N_t"].to_numpy(np.int32),
    f_t=pics["f_t"].to_numpy(np.float32), p_t=pics["p_t"].to_numpy(),
    surprise=pics["surprise"].to_numpy(np.float32),
    n_absorbes=pics["n_absorbes"].to_numpy(np.int32))

# controle : la colonne centrale doit redonner f_t des metadonnees
ecart_max = float(np.abs(fenetres[:, DEMI] - pics["f_t"].to_numpy()).max())
print(f"FINI : matrice {fenetres.shape[0]} x {fenetres.shape[1]} "
      f"({bords} pic(s) trop pres du bord), controle centre vs f_t : "
      f"ecart max {ecart_max:.3f} (arrondi csv attendu < 0.005), "
      f"{os.path.getsize(chemin) / 1e6:.0f} Mo en "
      f"{time.time() - debut:.0f} s -> {chemin}", flush=True)
