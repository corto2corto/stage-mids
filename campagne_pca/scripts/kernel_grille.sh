#!/bin/bash
# Grille de gamma calee sur la mediane des distances, avec spectre entier ET
# projections (50 vecteurs propres), sur les trois configurations hebdo hors
# Le Monde. Sequentiel strict, du plus petit corpus au plus gros.
#
# Duree attendue : les vecteurs propres dominent (cout en N^3) — de l'ordre de
# 3 h a Mediapart, 8 h aux Echos, 20 h au Figaro pour les 8 gammas. C'est
# assume : le calcul tourne en tache de fond, threads brides a 8 sur 20 pour
# laisser passer le scrapping.
# Usage : tmux new -s grille -d 'bash campagne_pca/scripts/kernel_grille.sh'
set -u
cd /data/elias/stage-mids
export VOCAB_DIR=/data/elias/stage-mids/data
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 NUMEXPR_NUM_THREADS=8
P=.venv/bin/python
LOG=/data/elias/stage-mids/data/logs/kernel_grille.log

{
  echo "=== depart $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
  $P -m campagne_pca.scripts.kernel_grille mediapart7j --pics _s3
  $P -m campagne_pca.scripts.kernel_grille lesechos7j  --pics _s3
  $P -m campagne_pca.scripts.kernel_grille lefigaro7j  --pics _s3
  echo "=== fin $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
} 2>&1 | tee -a "$LOG"
