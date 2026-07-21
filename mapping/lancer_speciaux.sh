#!/bin/bash
# Enchaine les mappings speciaux (Le Point, La Tribune, archives
# Liberation via CDX ; Ouest-France via Selenium ; La Provence via
# pagination). A lancer sur le serveur, dans une session tmux dediee (PAS
# celle du scrapping), depuis la racine du depot :
#
#     bash mapping/lancer_speciaux.sh
#
# Le log detaille va dans mapping/mappings_speciaux.log (hors suivi git).
# liberation_archives passe apres le mapping generique de liberation car il
# fusionne dans le meme CSV. Un seul Firefox a la fois (ouest_france), et les
# scripts CDX sont serialises pour menager l'API de la Wayback Machine.
set -u
cd "$(dirname "$0")/.."
source .venv/bin/activate

for media in latribune ouest_france lepoint liberation_archives laprovence laprovence_archives; do
    echo "=== $(date '+%F %T') debut $media ===" | tee -a mapping/mappings_speciaux.log
    python -m "mapping.$media" >> mapping/mappings_speciaux.log 2>&1
    echo "=== $(date '+%F %T') fin $media (code $?) ===" | tee -a mapping/mappings_speciaux.log
done
echo "=== $(date '+%F %T') TERMINE ===" | tee -a mapping/mappings_speciaux.log
wc -l exploration/*_url.csv | tee -a mapping/mappings_speciaux.log
