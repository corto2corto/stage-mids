#!/bin/bash
# Salve 6 (nuit du 31/07 au 01/08) : requalification de tous les axes avec
# les DEUX nuls — melange par colonne (exces6, deja en place) ET decalage
# circulaire par ligne (alignement6 : structure ancree sur le pic vs
# autocorrelation generique ; cf. test local — lemonde d15 brut 1,27,
# lemonde d50 log 1,01). Grille appariee de salve 4 x {brut, log}, puis
# replicats graines 2 et 3 pour les barres d'erreur. Tout part dans
# resultats_rotation.csv (chaque ligne porte exces6 ET alignement6) —
# resultats.csv n'est pas touche.
# ~2300 configs, ~2h30. Usage (sur gallica) : bash campagne_pca/salve6_rotation_log.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4

for graine in 1 2 3; do
  for variante in brut log; do
    v=""; [ "$variante" = log ] && v="--log"
    for media in lemonde lemonde3j lemonde7j lefigaro lefigaro3j lefigaro7j \
                 lesechos lesechos3j lesechos7j mediapart mediapart3j mediapart7j; do
      n=5000
      case "$media" in mediapart) n=2000;; *3j|*7j) n=0;; esac
      for demi in 10 15 25 50; do
        for seuil in 4 6; do
          for filtre in tous sans_verbes noms noms_propres; do
            nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
              --demi "$demi" --seuil "$seuil" --filtre "$filtre" \
              --nettoie "$n" --pics _s3 --sous_ech 5000 --graine "$graine" \
              --nul_rotation $v
          done
        done
      done
    done
  done
done
echo SALVE6_FINIE
