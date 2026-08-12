# Construit le cache PCA d'une configuration : le resultat de la chaine
# (pics -> NMS -> fenetres -> z-score -> PCA), pret a tracer.
#
# A lancer SUR LE SERVEUR, la ou vivent les sources : vocab_series_<media>.npz
# (jusqu'a 250 Mo piece) et pics_<media>.csv. Le cache produit fait ~3 Mo par
# configuration — c'est lui, et lui seul, qui redescend en local. Les figures
# n'ont jamais besoin des sources.
#
# Une configuration deja en cache n'est pas recalculee (--force pour refaire).
# Usage (serveur) : VOCAB_DIR=/data/elias/stage-mids/data \
#                   .venv/bin/python -m campagne_pca.scripts.construire_cache [config...]
#                   sans argument : toutes les configurations de configs.py
import argparse
import time

import numpy as np

from campagne_pca.scripts import figures_lib as lib
from campagne_pca.scripts.configs import CONFIGS

CACHE = lib.DATA / "cache_pca"

# Ce qu'on garde : tout ce dont les vues de figures_lib ont besoin. Z et proj en
# float32 (moitie moins lourd, precision largement suffisante pour un trace) ;
# composantes et variance restent en float64, ils tiennent en quelques ko.
CHAMPS = ("Z", "composantes", "variance", "proj", "mots", "dates", "surprise", "volume")

# Configurations dont le cache porte, en plus de CHAMPS, ce qu'il faut pour une
# figure hors chaine standard (diagnostic corpus-vide + NMS avant/apres sur
# "syrienne", presentation_sauts.qmd — ex-resultats_PCA/). Seule la grille
# quotidienne s'y prete : vocab_series_lemonde.npz est une grille par jour.
AVEC_EXTRAS = {"lemonde"}


def chemin(prefixe):
    return CACHE / f"{prefixe}.npz"


def _extras_diagnostics(d):
    """Champs supplementaires pour AVEC_EXTRAS : agreges cote serveur, la
    grille de N_t (vocab_series_lemonde.npz, 126 Mo) ne redescend jamais."""
    import pandas as pd
    g = np.load(lib.DONNEES / "vocab_series_lemonde.npz")
    position = {int(dt): i for i, dt in enumerate(g["dates"])}
    pos = np.array([position[int(dt)] for dt in d.dates])
    N_min = g["N"][pos[:, None] + np.arange(-d.demi, d.demi + 1)].min(axis=1)

    BORDS = [0, 100, 1000, 5000, 20000, 10**9]
    taux, effectifs = [], []
    for a, b in zip(BORDS[:-1], BORDS[1:]):
        sel = (N_min >= a) & (N_min < b)
        taux.append(float((np.abs(d.proj[sel, 3]) > 2.5).mean() * 100))
        effectifs.append(int(sel.sum()))
    extra = dict(taux_corpusvide=np.array(taux), effectifs_corpusvide=np.array(effectifs))

    if "X" in g.files:                    # matrice complete : gallica seulement
        jcol = int(np.where(g["mots"] == "syrienne")[0][0])
        serie = 1e5 * g["X"][:, jcol].astype(float) / g["N"]
        i1, i2 = np.searchsorted(g["dates"], [20110701, 20140901])
        avant = pd.read_csv(lib.DONNEES / "pics_lemonde.csv")
        avant = avant[(avant["mot"] == "syrienne") & avant["date"].between(20110701, 20140901)]
        apres = pd.read_csv(lib.DONNEES / "pics_lemonde_nms.csv")
        apres = apres[(apres["mot"] == "syrienne") & apres["date"].between(20110701, 20140901)]
        extra.update(
            nms_dates=g["dates"][i1:i2], nms_serie=serie[i1:i2],
            nms_avant_date=avant["date"].to_numpy(), nms_avant_ft=avant["f_t"].to_numpy(),
            nms_apres_date=apres["date"].to_numpy(), nms_apres_ft=apres["f_t"].to_numpy())
    else:
        print("  (extras) nms_syrienne : matrice X absente, ignore")
    return extra


def construire(prefixe, force=False):
    """Calcule et ecrit le cache d'une configuration. Renvoie son chemin."""
    sortie = chemin(prefixe)
    if sortie.exists() and not force:
        print(f"{prefixe} : deja en cache ({sortie.stat().st_size / 1048576:.1f} Mo), "
              "ignore")
        return sortie

    c = CONFIGS[prefixe]
    debut = time.time()
    d = lib.charger(c["media"], c["demi"], c["seuil"], c["pics"], c["nettoie"])
    extra = _extras_diagnostics(d) if prefixe in AVEC_EXTRAS else {}
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        sortie,
        Z=d.Z.astype(np.float32), composantes=d.composantes, variance=d.variance,
        # mots vient de pandas en dtype object : le forcer en texte permet de
        # relire le cache avec allow_pickle=False (pas de code arbitraire execute)
        proj=d.proj.astype(np.float32), mots=d.mots.astype(str), dates=d.dates,
        surprise=d.surprise, volume=d.volume,
        # metadonnees : de quoi relire le cache sans configs.py
        media=c["media"], demi=c["demi"], seuil=c["seuil"], pas_jours=c["pas_jours"],
        **extra)
    print(f"{prefixe} : {len(d.Z)} fenetres x {d.D} blocs -> "
          f"{sortie.stat().st_size / 1048576:.1f} Mo en {time.time() - debut:.0f} s")
    return sortie


ap = argparse.ArgumentParser(description="Construit le cache PCA (a lancer sur le serveur)")
ap.add_argument("configs", nargs="*", default=None,
                help="configurations a construire (defaut : toutes)")
ap.add_argument("--force", action="store_true", help="recalculer meme si deja en cache")
a = ap.parse_args()

demandees = a.configs or list(CONFIGS)
inconnues = [p for p in demandees if p not in CONFIGS]
if inconnues:
    raise SystemExit(f"configuration inconnue : {', '.join(inconnues)} "
                     f"(connues : {', '.join(CONFIGS)})")

debut = time.time()
for prefixe in demandees:
    construire(prefixe, a.force)
total = sum(chemin(p).stat().st_size for p in demandees if chemin(p).exists())
print(f"\n{len(demandees)} configurations, {total / 1048576:.0f} Mo de cache, "
      f"{time.time() - debut:.0f} s -> {CACHE.relative_to(lib.ICI)}")
