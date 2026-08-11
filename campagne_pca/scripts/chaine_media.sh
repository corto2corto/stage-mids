#!/bin/bash
# Chaine complete d'un nouveau media pour la campagne PCA (sur gallica, en
# tmux dedie) : recensement du vocabulaire -> series top-10k -> pics a
# surprise >= 3 (sur-ensemble du seuil 4, ne sera jamais recalcule) ->
# grilles agregees 3j/7j -> pics s3 dessus. Les etapes pics_masse durent des
# heures ; tout est nice et borne en threads. set -e : un echec arrete la
# chaine (visible dans le log).
# Usage : bash campagne_pca/scripts/chaine_media.sh <media>     (ex. lefigaro)
set -e
cd /data/elias/stage-mids
media=$1
export OMP_NUM_THREADS=2
run() { nice -n 10 .venv/bin/python -m "$@"; }
run exploration.scan_vocab "$media"
run rupture.masse "$media"
run rupture.pics_masse "$media" bnb 2 3
run rupture.agreger "$media" 3
run rupture.agreger "$media" 7
run rupture.pics_masse "${media}3j" bnb 2 3
run rupture.pics_masse "${media}7j" bnb 2 3
echo "CHAINE_${media}_FINIE"
