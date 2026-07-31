#!/bin/bash
# Salve 5 : variante gros vocabulaire (lemondev40k, >= 1000 jours actifs,
# 39 316 mots — comparaison notee au to_do) et variante log (notes d'appel :
# fenetres en log(1+f) avant z-score) sur les configs de repere.
# - 40k : 3 grilles x 4 demi x 3 seuils x 4 filtres, en plein n ET a n
#   apparie 5000 (comparaison propre avec le top-10k) = 288 configs. Le npz
#   journalier fait 4,2 Go : chargements lents, ~2-3 h au total.
# - log : 4 medias x 3 grilles x {d15, d50} x s4 x {tous} en plein n = 24
#   configs, pour jauger l'effet avant d'elargir.
# A lancer APRES la fin de salve 4 (un seul ecrivain de resultats.csv).
# Usage (sur gallica) : bash campagne_pca/salve5_40k_log.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=4

for media in lemondev40k lemondev40k3j lemondev40k7j; do
  n=5000; case "$media" in *3j|*7j) n=0;; esac
  for demi in 10 15 25 50; do
    for seuil in 3 4 6; do
      for filtre in tous sans_verbes noms noms_propres; do
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n" \
          --pics _s3
        nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
          --demi "$demi" --seuil "$seuil" --filtre "$filtre" --nettoie "$n" \
          --pics _s3 --sous_ech 5000
      done
    done
  done
done

for media in lemonde lemonde3j lemonde7j lefigaro lefigaro3j lefigaro7j \
             lesechos lesechos3j lesechos7j mediapart mediapart3j mediapart7j; do
  n=5000
  case "$media" in mediapart) n=2000;; *3j|*7j) n=0;; esac
  for demi in 15 50; do
    nice -n 10 .venv/bin/python -m rupture.campagne "$media" \
      --demi "$demi" --seuil 4 --filtre tous --nettoie "$n" --pics _s3 --log
  done
done
echo SALVE5_FINIE
