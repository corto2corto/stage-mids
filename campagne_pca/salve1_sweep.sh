#!/bin/bash
# Salve 1 de la campagne PCA (31/07/2026) : balayage des axes gratuits sur
# les trois grilles lemonde existantes — 3 grilles x 5 demi-fenetres x 3
# seuils x 4 filtres = 180 configs, sequentiel (un seul ecrivain de
# resultats.csv). ~2-10 s par config.
# Usage (sur gallica) : bash campagne_pca/salve1_sweep.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4
for media in lemonde lemonde3j lemonde7j; do
  n=5000; [ "$media" != lemonde ] && n=0
  for demi in 5 10 15 25 50; do
    for seuil in 4 5 6; do
      for filtre in tous sans_verbes noms noms_propres; do
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n"
      done
    done
  done
done
echo SALVE1_FINIE
