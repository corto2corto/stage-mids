#!/bin/bash
# Lance UNE session complète du pipeline sur la base de test (calqué sur
# scripts/lancer.sh : verrou, nettoyage des Firefox/profils temp, timeout),
# mais un seul cycle — pas de boucle — pour ne consommer qu'un login
# le_monde/mediapart par lancement.
# Usage : bash exploration/lancer_grp.sh   (depuis la racine du clone v2)

RACINE_V2="/data/elias/stage-mids-v2"
D="$RACINE_V2/exploration/test_run_grp"
TMP_DIR="/dev/shm/stage-mids-firefox-tmp"   # aligné sur TMP_FIREFOX (config.py)
GECKODRIVER="/data/elias/stage-mids/extensions/geckodriver/geckodriver"

exec 9>"$D/lancer_grp.lock"
if ! flock -n 9; then
    echo "Refus : un lancer_grp.sh tourne déjà."
    exit 1
fi

# Nettoyage des résidus d'un run précédent (mêmes motifs que lancer.sh prod).
pkill -9 -f "$TMP_DIR"
pkill -9 -f "$GECKODRIVER"
sleep 5
find "$TMP_DIR" -mindepth 1 -delete 2>/dev/null

cd "$RACINE_V2" || exit 1
export STAGE_DATA_DIR="$D"
export PYTHONUNBUFFERED=1

echo "[$(date '+%F %T')] Session unique : départ." >> "$D/grp.log"
# Le pipeline s'arrête seul à 4 h ; timeout l'abat à 4 h 30 s'il gèle.
timeout -k 30 270m .venv/bin/python -m scraping.pipeline >> "$D/grp.log" 2>&1
echo "[$(date '+%F %T')] Session terminée (code $?)." >> "$D/grp.log"

pkill -9 -f "$TMP_DIR"
pkill -9 -f "$GECKODRIVER"
