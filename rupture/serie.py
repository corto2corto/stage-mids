"""Brique 1 : charger la serie quotidienne d'un mot (extraction a la demande).

La donnee vient de rupture/extraire (bases ngram du serveur, cache local).
"""
import pandas as pd

from rupture import extraire


def charger(mot, media="lemonde", d1=0, d2=99999999):
    """Serie du mot sur [d1, d2] (defaut : tout) : (date, X_t, N_t, dt, f_t)."""
    d = extraire.serie(mot, media)
    d = d[(d["date"] >= d1) & (d["date"] <= d2)].reset_index(drop=True)
    if not len(d):
        raise ValueError(f"{mot} ({media}) : aucun jour sur [{d1}, {d2}]")
    d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
    d["f_t"] = 1e5 * d["X_t"] / d["N_t"]
    # la grille = les jours de parution presents en base ; les fenetres
    # (brique 3) se comptent donc en jours de parution
    if not d["date"].is_unique:
        raise ValueError(f"{mot} ({media}) : dates en double dans la serie")
    return d
