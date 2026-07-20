"""Brique 1 : charger la serie quotidienne (date, X_t, N_t) d'un mot.

Meme source que /fiche-mot : paper/donnees_maths/<slug>_lemonde.csv,
grille complete avec zeros extraite du serveur (voir extraire.sh).
"""
import os
import sys
import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONNEES = f"{RACINE}/paper/donnees_maths"


def charger(slug, d1=0, d2=99999999):
    """Serie du mot sur [d1, d2] (defaut : tout le CSV) : (date, X_t, N_t, dt, f_t)."""
    chemin = f"{DONNEES}/{slug}_lemonde.csv"
    if not os.path.exists(chemin):
        sys.exit(f"{chemin} introuvable : extraire le CSV d'abord "
                 "(skill /fiche-mot ou paper/donnees_maths/extraire.sh)")
    d = pd.read_csv(chemin)
    d = d[(d["date"] >= d1) & (d["date"] <= d2)].reset_index(drop=True)
    d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
    d["f_t"] = 1e5 * d["X_t"] / d["N_t"]
    # la grille = les jours de parution presents en base ; il manque des jours
    # calendaires (pas de journal ce jour-la), les fenetres (brique 3) se
    # comptent donc en jours de parution
    if not d["date"].is_unique:
        sys.exit(f"{slug} : dates en double dans le CSV")
    return d
