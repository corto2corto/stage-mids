# Desaisonnalisation hebdomadaire des series du corpus unifie. Pour chaque mot,
# decomposition de f_t = 1e5 * X_t / N_t (grille de jours calendaires complete,
# 2008-2026) avec une periode de 7 jours ; on ne garde que la composante
# saisonniere S, retiree ensuite de f_t par fenetres_desaison.py.
#   --methode stl       : statsmodels STL (Cleveland et al. 1990), profil
#                         hebdomadaire lissé dans le temps (fenetre --seasonal,
#                         impaire, en nombre de semaines), --robust pour
#                         attenuer le poids des pics
#   --methode classique : statsmodels seasonal_decompose additif (moyenne mobile
#                         7 jours + profil hebdomadaire constant sur 18 ans)
# Sortie : campagne_pca/data/data_local/saison_<tag>.npz (S float32 jours x mots,
# dates, mots, reglage), hors git comme les series.
# Usage : .venv/bin/python -m campagne_pca.desaison.scripts.desaisonnaliser \
#             <tag> --methode stl --seasonal 53 --robust [--procs 8]
import argparse
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from statsmodels.tsa.seasonal import STL, seasonal_decompose

DL = Path(__file__).resolve().parents[2] / "data" / "data_local"
PERIODE = 7
F = None                                          # matrice f_t partagee par worker


def charger():
    d = np.load(DL / "vocab_series_unifie.npz")
    return (1e5 * d["X"] / d["N"][:, None]).astype(np.float32), d["dates"], d["mots"]


def init(seasonal, robust):
    global F, SEASONAL, ROBUST
    F, _, _ = charger()
    SEASONAL, ROBUST = seasonal, robust


def stl_colonnes(js):
    S = [STL(F[:, j].astype(np.float64), period=PERIODE, seasonal=SEASONAL,
             robust=ROBUST).fit().seasonal for j in js]
    return js[0], np.stack(S, axis=1).astype(np.float32)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--methode", choices=["stl", "classique"], default="stl")
    ap.add_argument("--seasonal", type=int, default=7)
    ap.add_argument("--robust", action="store_true")
    ap.add_argument("--procs", type=int, default=8)
    a = ap.parse_args()

    debut = time.time()
    F, dates, mots = charger()
    S = np.empty_like(F)
    if a.methode == "classique":
        for j in range(0, F.shape[1], 500):
            r = seasonal_decompose(F[:, j:j + 500].astype(np.float64), period=PERIODE,
                                   model="additive", two_sided=True, extrapolate_trend="freq")
            S[:, j:j + 500] = r.seasonal
        reglage = "seasonal_decompose additif, periode 7"
    else:
        lots = [np.arange(j, min(j + 100, F.shape[1])) for j in range(0, F.shape[1], 100)]
        with Pool(a.procs, initializer=init, initargs=(a.seasonal, a.robust)) as pool:
            for j0, bloc in pool.imap_unordered(stl_colonnes, lots):
                S[:, j0:j0 + bloc.shape[1]] = bloc
                print(f"  {j0 + bloc.shape[1]:>6} mots, {time.time() - debut:.0f} s", flush=True)
        reglage = f"STL periode 7, seasonal={a.seasonal}, robust={a.robust}"
    np.savez_compressed(DL / f"saison_{a.tag}.npz", S=S, dates=dates, mots=mots,
                        reglage=np.array(reglage))
    print(f"{a.tag} : {reglage} -> saison_{a.tag}.npz en {time.time() - debut:.0f} s")
