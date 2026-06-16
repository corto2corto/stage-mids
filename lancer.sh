#!/bin/bash
# Boucle de scraping : relance le pipeline en continu (il s'auto-limite à 3h),
# puis nettoie les Firefox orphelins + profils temp avant le cycle suivant.
# À lancer dans la session tmux "scrapping" : bash lancer.sh

TMP_DIR="/data/elias/stage-mids/extensions/firefox/tmp"

while true; do
    python -m scraping.pipeline

    # --- Nettoyage des résidus de CE run (scopé strictement à mon tmp) ---
    # Tue les Firefox orphelins qui portent mon chemin tmp (et eux seuls),
    # puis vide le dossier. Un profil encore verrouillé partira au cycle suivant.
    pkill -9 -f "$TMP_DIR"
    sleep 5
    find "$TMP_DIR" -mindepth 1 -delete 2>/dev/null

    echo "[$(date '+%F %T')] Nettoyage fait, relance du pipeline."
done
