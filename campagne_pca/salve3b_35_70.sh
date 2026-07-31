#!/bin/bash
# Salve 3b : reprise de la section perdue de salve 3 (crash n < D sur
# mediapart7j d50 s6 noms_propres, corrige dans campagne.py) — fenetres
# +/-35 et +/-70 (piste Bouchot) sur les 12 media-grilles, seuils 4 et 6,
# filtres tous et noms_propres (96 configs), plus le rejeu de la config
# crashee (sa ligne resultats existe en double : dedupliquer par tag au
# moment de l'analyse, garder la derniere).
# Usage (sur gallica) : bash campagne_pca/salve3b_35_70.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4

nice -n 10 .venv/bin/python -m rupture.campagne mediapart7j \
  --demi 50 --seuil 6 --filtre noms_propres --nettoie 0 --pics _s3

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
echo SALVE3B_FINIE
