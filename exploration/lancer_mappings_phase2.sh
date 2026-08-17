#!/bin/bash
# Enchaine les mappings de la phase 2 (Le Point, La Tribune, archives
# Liberation via CDX ; Ouest-France via Selenium ; La Provence via
# pagination). A lancer sur le serveur, dans une session tmux dediee (PAS
# celle du scrapping), depuis la racine du depot :
#
#     bash exploration/lancer_mappings_phase2.sh
#
# Le log detaille va dans exploration/mappings_phase2.log (hors suivi git).
# liberation_archives passe apres liberation (phase 1) et laprovence_archives
# apres laprovence : ils fusionnent dans le CSV du mapping qu'ils completent.
# Les mappings CDX sont serialises pour menager l'API de la Wayback Machine,
# et ouest_france (le seul sous Firefox) passe en dernier, seul.
set -u
cd "$(dirname "$0")/.."
source .venv/bin/activate

for media in latribune lepoint liberation_archives laprovence laprovence_archives; do
    echo "=== $(date '+%F %T') debut $media ===" | tee -a exploration/mappings_phase2.log
    python -m exploration.mapping "$media" >> exploration/mappings_phase2.log 2>&1
    echo "=== $(date '+%F %T') fin $media (code $?) ===" | tee -a exploration/mappings_phase2.log
done

# ouest_france garde son script dedie : seul mapping passant par Firefox
# (DataDome ne sert ses sitemaps qu'a un vrai navigateur)
echo "=== $(date '+%F %T') debut ouest_france ===" | tee -a exploration/mappings_phase2.log
python -m exploration.mapping_ouest_france >> exploration/mappings_phase2.log 2>&1
echo "=== $(date '+%F %T') fin ouest_france (code $?) ===" | tee -a exploration/mappings_phase2.log
echo "=== $(date '+%F %T') TERMINE ===" | tee -a exploration/mappings_phase2.log
wc -l exploration/*_url.csv | tee -a exploration/mappings_phase2.log
