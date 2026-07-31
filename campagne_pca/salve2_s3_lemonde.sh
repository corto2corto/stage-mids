#!/bin/bash
# Rejeu pics_masse a surprise >= 3 sur les trois grilles lemonde (campagne
# PCA, axe seuil 3). Ecrit pics_lemonde{,3j,7j}_s3.csv — les fichiers livres
# ne sont pas touches. Le mini-balayage s3 (60 configs) sera lance ensuite,
# jamais en meme temps que salve2_sweep.sh : un seul ecrivain de
# resultats.csv a la fois.
# Usage (sur gallica) : bash campagne_pca/salve2_s3_lemonde.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=2
for media in lemonde lemonde3j lemonde7j; do
  nice -n 10 .venv/bin/python -m rupture.pics_masse "$media" bnb 2 3
done
echo S3_LEMONDE_FINI
