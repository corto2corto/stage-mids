"""Brique 3 : extraire les fenetres de serie autour des pics.

Pour chaque pic, la fenetre de f_t sur ±DEMI jours de parution (la base saute
les jours sans journal) devient une ligne de la matrice : metadonnees (mot,
date, X_t, f_t, p_t, surprise) puis colonnes j-15 ... j+15. Les pics a moins
de DEMI jours d'un bord de la periode sont ecartes. La NMS (etape 3 du to_do)
s'inserera entre detecter() et extraire(), en filtrant le DataFrame des pics.

Usage : python -m rupture.fenetres <slug> [debut] [fin] [--plot] [--poisson]
Sortie : rupture/sorties/fenetres_<slug>_<periode>[_poisson].csv (+ .png si --plot)
"""
import os
import sys
import pandas as pd

from rupture import pics as mod_pics, serie

DEMI = 15                                  # fenetre de 1 + 2*DEMI = 31 jours
SORTIES = f"{os.path.dirname(os.path.abspath(__file__))}/sorties"


def extraire(d, les_pics, slug, demi=DEMI):
    """Matrice des fenetres (une ligne par pic complet) + nb de pics au bord."""
    colonnes = [f"j{j:+d}" for j in range(-demi, demi + 1)]
    lignes, bords = [], 0
    for i, p in les_pics.iterrows():
        if i - demi < 0 or i + demi >= len(d):
            bords += 1
            continue
        ligne = {"mot": slug, "date": int(p["date"]), "X_t": int(p["X_t"]),
                 "f_t": p["f_t"], "p_t": p["p_t"], "surprise": p["surprise"]}
        ligne.update(zip(colonnes, d["f_t"].iloc[i - demi:i + demi + 1]))
        lignes.append(ligne)
    return pd.DataFrame(lignes), bords


if __name__ == "__main__":
    plot = "--plot" in sys.argv
    en_poisson = "--poisson" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--plot", "--poisson")]
    slug = args[0]
    d1 = int(args[1]) if len(args) > 1 else 0
    d2 = int(args[2]) if len(args) > 2 else 99999999

    d = serie.charger(slug, d1, d2)
    d = (mod_pics.ajuster_poisson(d) if en_poisson else mod_pics.ajuster(d))[0]
    fen, bords = extraire(d, mod_pics.detecter(d), slug)
    if not len(fen):
        sys.exit(f"{slug} : aucun pic a fenetre complete sur [{d1}, {d2}]")

    os.makedirs(SORTIES, exist_ok=True)
    periode = f"{d['date'].iloc[0]}_{d['date'].iloc[-1]}"
    chemin = f"{SORTIES}/fenetres_{slug}_{periode}" + ("_poisson" if en_poisson else "") + ".csv"
    fen.to_csv(chemin, index=False)
    print(f"{slug} : {len(fen)} fenetres de {2 * DEMI + 1} jours"
          + (f" ({bords} pic(s) trop pres du bord)" if bords else ""))
    print("->", os.path.relpath(chemin))
    if plot:
        from rupture import graphes
        png = chemin.replace(".csv", ".png")
        graphes.planche(fen, slug, png)
        print("->", os.path.relpath(png))
