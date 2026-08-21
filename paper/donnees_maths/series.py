"""Rebatit series_mots.csv depuis les bases ngram (gallica, lecture seule).

Une colonne par mot de RECUEIL puis de MOTS (rupture/fiches.py), avec les
totaux factorises une seule fois : N_1gram pour les mots simples, N_2gram pour
les expressions de deux mots. Remplace l'ancien extraire.sh (ids en dur) :
extraire.serie somme les graphies avec/sans accents et reinjecte les zeros.

Usage : python paper/donnees_maths/series.py   (~1,5 s par mot sans cache)
"""
import os, sys
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(ICI)))    # racine du depot
from rupture import extraire
from rupture.fiches import MOTS, RECUEIL

mots = [mot for groupe in RECUEIL.values() for mot, _, _ in groupe]
mots = list(dict.fromkeys(mots + list(MOTS)))

colonnes, totaux = {}, {}
for mot in mots:
    d = extraire.serie(mot).set_index("date")
    s = extraire.slug(mot)
    colonnes[s] = d["X_t"]
    totaux.setdefault("N_2gram" if "_" in s else "N_1gram", d["N_t"])
    print(f"  {mot:26s} {len(d):6d} jours  X_total={int(d['X_t'].sum()):9d}")

tab = pd.DataFrame(totaux)
for s, x in colonnes.items():
    tab[s] = x
tab = tab.sort_index().reset_index()
tab.to_csv(f"{ICI}/series_mots.csv", index=False)
print(f"-> series_mots.csv : {len(tab)} jours x {tab.shape[1]} colonnes, "
      f"{os.path.getsize(f'{ICI}/series_mots.csv') / 1e6:.1f} Mo")
