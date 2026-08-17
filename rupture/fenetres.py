"""Brique 3 : extraire les fenetres de serie autour des pics.

Pour chaque pic, la fenetre de f_t sur ±DEMI jours de parution (la base saute
les jours sans journal) devient une ligne de la matrice : metadonnees (mot,
date, X_t, f_t, p_t, surprise) puis colonnes j-15 ... j+15. Les pics a moins
de DEMI jours d'un bord de la periode sont ecartes. La NMS (etape 3 du to_do)
s'inserera entre detecter() et fenetres(), en filtrant le DataFrame des pics.

Usage : python -m rupture.fenetres <mot> [poisson|nb|bnb] [fits] [debut] [fin]
        [--media lemonde|lefigaro|lesechos] [--plot]
Sortie : rupture/sorties/fenetres_<media>_<slug>_<periode>_<loi><fits>.csv
         (+ .png si --plot)
"""
import os
import sys
import numpy as np
import pandas as pd

from rupture import extraire, pics as mod_pics, serie

DEMI = 15                                  # fenetre de 1 + 2*DEMI = 31 jours
SORTIES = f"{os.path.dirname(os.path.abspath(__file__))}/sorties"


def fenetres(d, les_pics, mot, demi=DEMI):
    """Matrice des fenetres (une ligne par pic complet) + nb de pics au bord."""
    colonnes = [f"j{j:+d}" for j in range(-demi, demi + 1)]
    lignes, bords = [], 0
    for i, p in les_pics.iterrows():
        if i - demi < 0 or i + demi >= len(d):
            bords += 1
            continue
        ligne = {"mot": mot, "date": int(p["date"]), "X_t": int(p["X_t"]),
                 "f_t": p["f_t"], "p_t": p["p_t"], "surprise": p["surprise"]}
        ligne.update(zip(colonnes, d["f_t"].iloc[i - demi:i + demi + 1]))
        lignes.append(ligne)
    return pd.DataFrame(lignes), bords


if __name__ == "__main__":
    mot, loi, fits, dates, media, plot = None, "bnb", 1, [], "lemonde", False
    args = iter(sys.argv[1:])
    for a in args:
        if a == "--plot":
            plot = True
        elif a == "--media":
            media = next(args)
        elif a.lower() in mod_pics.LOIS or a.lower() == "p":
            loi = "poisson" if a.lower() == "p" else a.lower()
        elif a.isdigit() and len(a) == 8:
            dates.append(int(a))
        elif a.isdigit():
            fits = int(a)
        elif mot is None:
            mot = a
        else:
            sys.exit(f"argument inconnu : {a}")
    if mot is None:
        sys.exit(__doc__)
    d1 = dates[0] if dates else 0
    d2 = dates[1] if len(dates) > 1 else 99999999

    try:
        d = serie.charger(mot, media, d1, d2)
    except ValueError as e:
        sys.exit(str(e))
    params, p, garde = mod_pics.ajuster(d["X_t"].to_numpy(), d["N_t"].to_numpy(), loi, fits)
    d["p_t"] = p
    d["surprise"] = -np.log10(np.maximum(p, 1e-300))
    nom = extraire.slug(mot)
    fen, bords = fenetres(d, mod_pics.detecter(d), nom)
    if not len(fen):
        sys.exit(f"{mot} ({media}) : aucun pic a fenetre complete")

    os.makedirs(SORTIES, exist_ok=True)
    periode = f"{d['date'].iloc[0]}_{d['date'].iloc[-1]}"
    chemin = f"{SORTIES}/fenetres_{media}_{nom}_{periode}_{loi}{fits}.csv"
    fen.to_csv(chemin, index=False)
    print(f"{mot} ({media}) : {len(fen)} fenetres de {2 * DEMI + 1} jours"
          + (f" ({bords} pic(s) trop pres du bord)" if bords else ""))
    print("->", os.path.relpath(chemin))
    if plot:
        from rupture import graphes
        png = chemin.replace(".csv", ".png")
        graphes.planche(fen, nom, png)
        print("->", os.path.relpath(png))
