#!/bin/bash
# Kernel PCA complete des quatre configurations hebdomadaires, une a la fois, du
# plus petit corpus au plus gros (Gram : 0,24 / 0,60 / 1,0 / 6,1 Go). Sequentiel
# strict : un seul calcul en memoire a la fois. Threads BLAS brides a 8 sur 20
# pour laisser tourner le scrapping.
# Usage : tmux new -s kernel -d 'bash campagne_pca/kernel_hebdo.sh'
set -u
cd /data/elias/stage-mids
export VOCAB_DIR=/data/elias/stage-mids/data
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8 NUMEXPR_NUM_THREADS=8
P=.venv/bin/python
LOG=/data/elias/stage-mids/data/logs/kernel_hebdo.log

{
  echo "=== depart $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
  $P -m campagne_pca.kernel_hebdo mediapart7j --pics _s3
  $P -m campagne_pca.kernel_hebdo lesechos7j  --pics _s3
  $P -m campagne_pca.kernel_hebdo lefigaro7j  --pics _s3
  $P -m campagne_pca.kernel_hebdo lemonde7j
  echo "=== fin $(date -u +'%Y-%m-%d %H:%M:%S UTC') ==="
} 2>&1 | tee -a "$LOG"
