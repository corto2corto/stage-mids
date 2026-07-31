#!/bin/bash
# Salve 2 de la campagne PCA (31/07/2026 soir) : re-balayage COMPLET avec le
# temoin nul (colonnes exces6/cum6_nul ajoutees au runner — les 180 configs de
# la salve 1 sont rejouees pour avoir un schema unique). Trois medias :
# - lemonde (grilles 1j/3j/7j), seuils 4-6 (s3 en cours dans campagne_s3) ;
# - lefigaro et lesechos (grilles 1j/3j/7j), seuils 3-6 depuis les pics _s3.
# 180 + 240 + 240 = 660 configs, sequentiel, ~3-10 s piece.
# Usage (sur gallica) : bash campagne_pca/salve2_sweep.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4

for media in lemonde lemonde3j lemonde7j; do
  n=5000; case "$media" in *3j|*7j) n=0;; esac
  for demi in 5 10 15 25 50; do
    for seuil in 4 5 6; do
      for filtre in tous sans_verbes noms noms_propres; do
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n"
      done
    done
  done
done

for media in lefigaro lefigaro3j lefigaro7j lesechos lesechos3j lesechos7j; do
  n=5000; case "$media" in *3j|*7j) n=0;; esac
  for demi in 5 10 15 25 50; do
    for seuil in 3 4 5 6; do
      for filtre in tous sans_verbes noms noms_propres; do
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n" \
          --pics _s3
      done
    done
  done
done
echo SALVE2_FINIE
