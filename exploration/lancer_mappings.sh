#!/bin/bash
# Enchaine les mappings des nouveaux medias, du plus court au plus long.
# A lancer sur le serveur, dans une session tmux dediee (PAS celle du
# scrapping), depuis la racine du depot :
#
#     bash exploration/lancer_mappings.sh
#
# Le log detaille va dans exploration/mappings.log (hors suivi git).
set -u
cd "$(dirname "$0")/.."
source .venv/bin/activate

for media in francesoir liberation paris_normandie gala la_croix midilibre bfmtv voici lexpress marianne leparisien; do
    echo "=== $(date '+%F %T') debut $media ===" | tee -a exploration/mappings.log
    python -m exploration.mapping "$media" >> exploration/mappings.log 2>&1
    echo "=== $(date '+%F %T') fin $media (code $?) ===" | tee -a exploration/mappings.log
done
echo "=== $(date '+%F %T') TERMINE ===" | tee -a exploration/mappings.log
wc -l exploration/*_url.csv | tee -a exploration/mappings.log
