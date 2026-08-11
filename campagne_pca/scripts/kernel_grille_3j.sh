#!/bin/bash
# Meme grille de gamma que kernel_grille.sh (spectre entier + 50 vecteurs
# propres, 8 multiplicateurs de gamma_med), sur la grille a 3 jours au lieu de
# la grille hebdomadaire : demi=10, seuil=5. Choix acte le 08/08 apres
# comptage prealable — seuil=5 donne des effectifs du meme ordre que la
# config de la page 1 (seuil=6 les divise par ~2).
#
# Sequentiel strict, du plus petit corpus au plus gros :
#   Mediapart  4 665 fenetres, Gram 0,17 Go
#   Les Echos  8 188 fenetres, Gram 0,54 Go
#   Le Figaro  9 676 fenetres, Gram 0,75 Go
# Usage : tmux new -s grille3j -d 'bash campagne_pca/scripts/kernel_grille_3j.sh'
set -u
cd /data/elias/stage-mids
export VOCAB_DIR=/data/elias/stage-mids/data
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 NUMEXPR_NUM_THREADS=8
P=.venv/bin/python
LOG=/data/elias/stage-mids/data/logs/kernel_grille_3j.log

{
  echo "=== depart $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
  $P -m campagne_pca.scripts.kernel_grille mediapart3j --demi 10 --seuil 5 --pics _s3
  $P -m campagne_pca.scripts.kernel_grille lesechos3j  --demi 10 --seuil 5 --pics _s3
  $P -m campagne_pca.scripts.kernel_grille lefigaro3j  --demi 10 --seuil 5 --pics _s3
  echo "=== fin $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
} 2>&1 | tee -a "$LOG"
