# Chevauchement d'agenda entre journaux (campagne PCA jointe, chantier 1) :
# pour chaque paire ordonnee (A, B), part des EVENEMENTS de A (pics NMS,
# surprise >= 4, mots du vocabulaire commun a la paire, periode commune) qui
# trouvent un ECHO dans B (pic brut s3 du meme mot a moins de TOL jours
# calendaires). C'est la mesure duale de l'appariement des triplets : elle
# porte sur les ~99 % de pics que l'exigence du triple accord ecarte.
# Agregation par annee et par tranche de surprise de l'evenement.
# Prerequis : pics_<media>_s3_nms.csv (rupture.nms --pics _s3) pour chaque media.
# Sortie : <VOCAB_DIR>/appariement_paires.csv
#          (media_a, media_b, annee, tranche, n, echo)
# Usage (sur gallica) : python -m exploration.appariement_paires
import os
import time

import numpy as np
import pandas as pd

MEDIAS = ["lemonde", "lefigaro", "ouestfrance", "mediapart"]
TOL = 7                    # meme tolerance que fenetres_triplets
SEUIL_EVT = 4.0            # un evenement de A = pic NMS a surprise >= 4
TRANCHES = [4, 5, 6, 8, np.inf]
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
debut_t = time.time()


def en_jours(dates):
    return (pd.to_datetime(pd.Series(dates).astype(str), format="%Y%m%d")
            .to_numpy().astype("datetime64[D]").astype(np.int64))


mots_m, bornes, evenements, echos = {}, {}, {}, {}
for m in MEDIAS:
    d = np.load(f"{DOSSIER}/vocab_series_{m}.npz")
    mots_m[m] = set(d["mots"].astype(str))
    jours_grille = en_jours(d["dates"])
    bornes[m] = (int(jours_grille[0]), int(jours_grille[-1]))
    ev = pd.read_csv(f"{DOSSIER}/pics_{m}_s3_nms.csv")
    ev["jour"] = en_jours(ev["date"].to_numpy())
    evenements[m] = ev[ev["surprise"] >= SEUIL_EVT]
    raw = pd.read_csv(f"{DOSSIER}/pics_{m}_s3.csv", usecols=["mot", "date"])
    raw["jour"] = en_jours(raw["date"].to_numpy())
    echos[m] = {mot: np.sort(g.to_numpy())
                for mot, g in raw.groupby("mot", sort=False)["jour"]}
    print(f"{m:12s} {len(evenements[m]):7d} evenements (NMS >= {SEUIL_EVT:g}), "
          f"{len(raw):7d} pics bruts", flush=True)

lignes = []
for a in MEDIAS:
    for b in MEDIAS:
        if a == b:
            continue
        commun = mots_m[a] & mots_m[b]
        debut = max(bornes[a][0], bornes[b][0])
        fin = min(bornes[a][1], bornes[b][1])
        ev = evenements[a]
        ev = ev[ev["mot"].isin(commun) & (ev["jour"] >= debut) & (ev["jour"] <= fin)]
        trouve = np.zeros(len(ev), bool)
        for i, (mot, jour) in enumerate(zip(ev["mot"].to_numpy(), ev["jour"].to_numpy())):
            arr = echos[b].get(mot)
            if arr is not None:
                k = np.searchsorted(arr, jour - TOL)
                trouve[i] = k < len(arr) and arr[k] <= jour + TOL
        annee = (ev["date"].to_numpy() // 10000).astype(int)
        tranche = np.digitize(ev["surprise"].to_numpy(), TRANCHES[1:-1])
        for (an, tr), grp in pd.DataFrame(
                {"an": annee, "tr": tranche, "ok": trouve}).groupby(["an", "tr"]):
            lignes.append((a, b, int(an), int(tr), len(grp), int(grp["ok"].sum())))
        print(f"{a:12s} -> {b:12s} {len(ev):6d} evenements, "
              f"echo {trouve.mean() * 100:5.1f} % ({len(commun)} mots communs)", flush=True)

pd.DataFrame(lignes, columns=["media_a", "media_b", "annee", "tranche", "n", "echo"]
             ).to_csv(f"{DOSSIER}/appariement_paires.csv", index=False)
print(f"FINI en {(time.time() - debut_t) / 60:.1f} min -> "
      f"{DOSSIER}/appariement_paires.csv", flush=True)
