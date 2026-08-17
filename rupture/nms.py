# NMS glouton 1D sur les pics de masse (phase 3, etape 4 du to_do) : pour
# chaque mot, trier ses pics par surprise decroissante ; chaque pic retenu
# supprime ses voisins a moins de PORTEE jours de parution de lui — et un pic
# supprime ne supprime personne (pas de transitivite, contrairement au
# groupement par recouvrement qui chaine les longues periodes type covid en
# un seul groupe geant). PORTEE = 31 = largeur d'une fenetre : deux pics
# gardes n'ont donc jamais des fenetres qui se recouvrent dans la matrice.
# Les distances sont en jours de parution (positions dans la grille du npz),
# comme les fenetres de fenetres.py.
#
# Contre-verification independante : scipy.signal.find_peaks sur le signal
# surprise (0 hors pics, rembourre d'un zero a chaque bord pour que les pics
# aux extremites de la grille restent visibles), avec height=4 et distance=31
# — son parametre `distance` est un NMS glouton 1D de reference. Les mots ou
# les deux methodes divergent sont consignes (attendu : egalites de surprise
# — le csv arrondit a 2 decimales — departagees differemment).
#
# Sorties ecrites dans le meme dossier que l'entree :
# - pics_<media>_nms.csv     : pics gardes (memes colonnes + n_absorbes)
# - pics_<media>_nms_ecarts.txt : mot <tab> dates gardees par une seule methode
# Usage (sur gallica) : python -m rupture.nms [media]
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

PORTEE = 31        # largeur d'une fenetre (1 + 2*15 jours de parution)
HAUTEUR = 4.0      # surprise minimale = -log10(SEUIL de pics.py)


def nms(pos, surprise, portee=PORTEE):
    """Indices gardes par NMS glouton (pos en jours de parution, tries ou non).

    Renvoie (gardes, absorbes) : indices retenus, et pour chacun le nombre
    de pics qu'il a supprimes dans sa zone."""
    ordre = np.argsort(-surprise, kind="stable")
    vivant = np.ones(len(pos), bool)
    gardes, absorbes = [], []
    for i in ordre:
        if not vivant[i]:
            continue
        zone = np.abs(pos - pos[i]) < portee
        gardes.append(i)
        absorbes.append(int(vivant[zone].sum()) - 1)
        vivant[zone] = False
    return np.array(gardes), np.array(absorbes)


if __name__ == "__main__":
    media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
    DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")

    dates_grille = np.load(f"{DOSSIER}/vocab_series_{media}.npz")["dates"]
    position = {int(d): i for i, d in enumerate(dates_grille)}
    pics = pd.read_csv(f"{DOSSIER}/pics_{media}.csv")
    pics["pos"] = pics["date"].map(position)
    mots = pics["mot"].unique()
    print(f"{media} : {len(pics)} pics, {len(mots)} mots, portee={PORTEE} j de parution",
          flush=True)
    debut = time.time()
    n_gardes = n_ecarts = 0

    with open(f"{DOSSIER}/pics_{media}_nms.csv", "w") as fp, \
         open(f"{DOSSIER}/pics_{media}_nms_ecarts.txt", "w") as fe:
        fp.write(",".join(list(pics.columns[:-1]) + ["n_absorbes"]) + "\n")
        for j, (mot, p) in enumerate(pics.groupby("mot", sort=False)):
            pos = p["pos"].to_numpy()
            surprise = p["surprise"].to_numpy()
            gardes, absorbes = nms(pos, surprise)

            # contre-verif : find_peaks sur le signal surprise complet
            signal = np.zeros(len(dates_grille) + 2)
            signal[pos + 1] = surprise
            verif, _ = find_peaks(signal, height=HAUTEUR, distance=PORTEE)
            verif -= 1
            a, b = set(pos[gardes]), set(verif)
            if a != b:
                n_ecarts += 1
                seuls_nms = sorted(int(p.loc[p["pos"] == x, "date"].iloc[0]) for x in a - b)
                seuls_fp = sorted(int(p.loc[p["pos"] == x, "date"].iloc[0]) for x in b - a)
                fe.write(f"{mot}\tnms_seul={seuls_nms}\tfind_peaks_seul={seuls_fp}\n")
                fe.flush()

            tri = np.argsort(pos[gardes])              # sortie en ordre de dates
            for i, n_abs in zip(gardes[tri], absorbes[tri]):
                fp.write(",".join(str(v) for v in p.iloc[i, :-1]) + f",{n_abs}\n")
            n_gardes += len(gardes)
            fp.flush()
            if (j + 1) % 1000 == 0:
                ecoule = time.time() - debut
                print(f"[{j + 1}/{len(mots)}] {n_gardes} pics gardes, "
                      f"{n_ecarts} mots avec ecarts | {ecoule:.0f} s", flush=True)

    print(f"FINI : {n_gardes} pics gardes sur {len(pics)} "
          f"({len(pics) - n_gardes} supprimes, {n_gardes / len(pics) * 100:.1f} % gardes), "
          f"{n_ecarts} mots avec ecarts nms/find_peaks sur {len(mots)}, "
          f"en {(time.time() - debut) / 60:.1f} min", flush=True)
