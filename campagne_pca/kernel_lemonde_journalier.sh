#!/bin/bash
# Kernel PCA sur Le Monde, grille journaliere (pas de blocs), demi=15,
# seuil=6 : 31 882 fenetres, Gram 8,1 Go. Choix acte le 08/08 : la plus grosse
# config qui tienne confortablement dans les ~22 Go libres du serveur (seuil=4
# et 5 depassent la RAM disponible, cf. compte_fenetres.py). Premier gamma
# lance seul pour calibrer un temps reel avant d'enchainer les 7 autres.
# Usage : tmux new -s lemonde_j -d 'bash campagne_pca/kernel_lemonde_journalier.sh'
set -u
cd /data/elias/stage-mids
export VOCAB_DIR=/data/elias/stage-mids/data
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 NUMEXPR_NUM_THREADS=8
P=.venv/bin/python
LOG=/data/elias/stage-mids/data/logs/kernel_lemonde_journalier.log

{
  echo "=== depart $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
  $P -m campagne_pca.kernel_grille lemonde --demi 15 --seuil 6 --mults 1
  echo "=== fin $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
} 2>&1 | tee -a "$LOG"
