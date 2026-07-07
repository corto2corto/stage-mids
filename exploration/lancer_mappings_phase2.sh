#!/bin/bash
# Enchaine les mappings de la phase 2 (Le Point, La Tribune, archives
# Liberation via CDX ; Ouest-France via Selenium ; La Provence via
# pagination). A lancer sur le serveur, dans une session tmux dediee (PAS
# celle du scrapping), depuis la racine du depot :
#
#     bash exploration/lancer_mappings_phase2.sh
#
# Le log detaille va dans exploration/mappings_phase2.log (hors suivi git).
# liberation_archives passe apres liberation (phase 1) car il fusionne dans
# le meme CSV. Un seul Firefox a la fois (ouest_france), et les scripts CDX
# sont serialises pour menager l'API de la Wayback Machine.
set -u
cd "$(dirname "$0")/.."
source .venv/bin/activate

for media in latribune ouest_france lepoint liberation_archives laprovence laprovence_archives; do
    echo "=== $(date '+%F %T') debut $media ===" | tee -a exploration/mappings_phase2.log
    python -m "exploration.mapping_$media" >> exploration/mappings_phase2.log 2>&1
    echo "=== $(date '+%F %T') fin $media (code $?) ===" | tee -a exploration/mappings_phase2.log
done
echo "=== $(date '+%F %T') TERMINE ===" | tee -a exploration/mappings_phase2.log
wc -l exploration/*_url.csv | tee -a exploration/mappings_phase2.log
