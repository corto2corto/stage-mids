#!/bin/bash
# Variante gros vocabulaire du Monde (campagne PCA, comparaison notee au
# to_do) : seuil >= 1000 jours actifs au lieu du top-10 000, soit 39 316
# unites. Sorties nommees lemondev40k pour ne toucher a aucun fichier
# officiel. X dense ~4,2 Go en RAM pendant masse/pics_masse — sequentiel,
# une seule instance. Le balayage de cette variante attendra la
# classification de son vocabulaire (fin de salve 3, pas d'ecriture
# concurrente de resultats.csv).
# Usage (sur gallica) : bash campagne_pca/salve3_40k_lemonde.sh
set -e
cd /data/elias/stage-mids
export OMP_NUM_THREADS=2
run() { nice -n 10 .venv/bin/python -m "$@"; }
run rupture.masse lemonde 39316 lemondev40k
run rupture.pics_masse lemondev40k bnb 2 3
run rupture.agreger lemondev40k 3
run rupture.agreger lemondev40k 7
run rupture.pics_masse lemondev40k3j bnb 2 3
run rupture.pics_masse lemondev40k7j bnb 2 3
echo CHAINE_40K_FINIE
