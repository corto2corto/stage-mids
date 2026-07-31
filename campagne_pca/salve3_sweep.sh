#!/bin/bash
# Salve 3 de la campagne PCA (31/07/2026 soir) : 396 configs —
# - mini-balayage s3 lemonde (3 grilles x 5 demi x 4 filtres = 60), depuis
#   les pics_lemonde*_s3.csv produits par salve2_s3_lemonde.sh ;
# - balayage complet mediapart (3 grilles x 5 demi x 4 seuils x 4 filtres
#   = 240), nettoie 2000 en journalier (corpus petit : N median 9 092,
#   25 % des jours < 5000 — le seuil des autres medias serait trop violent) ;
# - extension demi 35 et 70 (piste Bouchot +/-70) sur les 12 media-grilles,
#   seuils 4 et 6, filtres tous et noms_propres (96 configs), pics _s3.
# Sequentiel : un seul ecrivain de resultats.csv.
# Usage (sur gallica) : bash campagne_pca/salve3_sweep.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4

for media in lemonde lemonde3j lemonde7j; do
  n=5000; case "$media" in *3j|*7j) n=0;; esac
  for demi in 5 10 15 25 50; do
    for filtre in tous sans_verbes noms noms_propres; do
      nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
        --demi "$demi" --seuil 3 --filtre "$filtre" --nettoie "$n" --pics _s3
    done
  done
done

for media in mediapart mediapart3j mediapart7j; do
  n=2000; case "$media" in *3j|*7j) n=0;; esac
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

for media in lemonde lemonde3j lemonde7j lefigaro lefigaro3j lefigaro7j \
             lesechos lesechos3j lesechos7j mediapart mediapart3j mediapart7j; do
  n=5000
  case "$media" in mediapart) n=2000;; *3j|*7j) n=0;; esac
  for demi in 35 70; do
    for seuil in 4 6; do
      for filtre in tous noms_propres; do
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n" \
          --pics _s3
      done
    done
  done
done
echo SALVE3_FINIE
