#!/bin/bash
# Enchaine des mappings via le moteur generique (mapping.generique), dans
# l'ordre donne. A lancer sur le serveur, dans une session tmux dediee (PAS
# celle du scrapping), depuis la racine du depot :
#
#     bash mapping/lancer.sh gala bfmtv cnews ...
#
# Medias = cles du catalogue (mapping/catalogue.py). liberation_archives se
# lance apres liberation (fusion dans le meme CSV) ; un seul media Firefox
# (ouest_france) a la fois. Le log detaille va dans mapping/mappings.log
# (hors suivi git).
set -u
cd "$(dirname "$0")/.."
source .venv/bin/activate

if [ $# -lt 1 ]; then
    echo "usage : bash mapping/lancer.sh <media> [media...]"
    exit 2
fi

for media in "$@"; do
    echo "=== $(date '+%F %T') debut $media ===" | tee -a mapping/mappings.log
    python -m mapping.generique "$media" >> mapping/mappings.log 2>&1
    echo "=== $(date '+%F %T') fin $media (code $?) ===" | tee -a mapping/mappings.log
done
echo "=== $(date '+%F %T') TERMINE ===" | tee -a mapping/mappings.log
