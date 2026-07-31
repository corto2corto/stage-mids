#!/bin/bash
# Salve 4 : comparaisons A N APPARIE (le vrai comparatif d'axes — cf. suivi
# du 31/07 19h15 : exces6 s'ecrase a petit n, les moyennes brutes melangent
# effet et taille d'echantillon). Toutes les configs sous-echantillonnees a
# 5 000 fenetres (tirage seede) : 4 medias x 3 grilles x 4 demi x 2 seuils
# x 4 filtres = 384 configs. Les configs naturellement < 5000 gardent leur n
# (lisible dans n_fenetres).
# Usage (sur gallica) : bash campagne_pca/salve4_napparie.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4

for media in lemonde lemonde3j lemonde7j lefigaro lefigaro3j lefigaro7j \
             lesechos lesechos3j lesechos7j mediapart mediapart3j mediapart7j; do
  n=5000
  case "$media" in mediapart) n=2000;; *3j|*7j) n=0;; esac
  for demi in 10 15 25 50; do
    for seuil in 4 6; do
      for filtre in tous sans_verbes noms noms_propres; do
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n" \
          --pics _s3 --sous_ech 5000
      done
    done
  done
done
echo SALVE4_FINIE
