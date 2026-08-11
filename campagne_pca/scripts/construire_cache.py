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
import os
import time

import numpy as np

from campagne_pca.scripts import figures_lib as lib
from campagne_pca.scripts.configs import CONFIGS

CACHE = os.path.join(lib.DATA, "cache_pca")

# Ce qu'on garde : tout ce dont les vues de figures_lib ont besoin. Z et proj en
# float32 (moitie moins lourd, precision largement suffisante pour un trace) ;
# composantes et variance restent en float64, ils tiennent en quelques ko.
CHAMPS = ("Z", "composantes", "variance", "proj", "mots", "dates", "surprise", "volume")


def chemin(prefixe):
    return os.path.join(CACHE, f"{prefixe}.npz")


def construire(prefixe, force=False):
    """Calcule et ecrit le cache d'une configuration. Renvoie son chemin."""
    sortie = chemin(prefixe)
    if os.path.exists(sortie) and not force:
        print(f"{prefixe} : deja en cache ({os.path.getsize(sortie) / 1048576:.1f} Mo), "
              "ignore")
        return sortie

    c = CONFIGS[prefixe]
    debut = time.time()
    d = lib.charger(c["media"], c["demi"], c["seuil"], c["pics"], c["nettoie"])
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(
        sortie,
        Z=d.Z.astype(np.float32), composantes=d.composantes, variance=d.variance,
        # mots vient de pandas en dtype object : le forcer en texte permet de
        # relire le cache avec allow_pickle=False (pas de code arbitraire execute)
        proj=d.proj.astype(np.float32), mots=d.mots.astype(str), dates=d.dates,
        surprise=d.surprise, volume=d.volume,
        # metadonnees : de quoi relire le cache sans configs.py
        media=c["media"], demi=c["demi"], seuil=c["seuil"], pas_jours=c["pas_jours"])
    print(f"{prefixe} : {len(d.Z)} fenetres x {d.D} blocs -> "
          f"{os.path.getsize(sortie) / 1048576:.1f} Mo en {time.time() - debut:.0f} s")
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
total = sum(os.path.getsize(chemin(p)) for p in demandees if os.path.exists(chemin(p)))
print(f"\n{len(demandees)} configurations, {total / 1048576:.0f} Mo de cache, "
      f"{time.time() - debut:.0f} s -> {os.path.relpath(CACHE, lib.ICI)}")
