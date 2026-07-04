#!/bin/bash
# Boucle de scraping : relance le pipeline en continu (il s'auto-limite à 2h,
# `timeout` l'abat à 2h30 si un appel Selenium gèle), en nettoyant avant chaque
# cycle les Firefox/geckodriver orphelins et les profils temp.
# À lancer dans la session tmux "scrapping" : bash lancer.sh

RACINE="/data/elias/stage-mids"
TMP_DIR="$RACINE/extensions/firefox/tmp"
GECKODRIVER="$RACINE/extensions/geckodriver/geckodriver"

# Verrou : une seule instance à la fois (deux pipelines sur la même base =
# doublons dans les CSV). Le descripteur est hérité par python/firefox : le
# verrou reste pris tant qu'un processus du run survit, c'est voulu.
exec 9>"$RACINE/lancer.lock"
if ! flock -n 9; then
    echo "Refus : un lancer.sh (ou ses navigateurs) tourne déjà."
    exit 1
fi

while true; do
    # --- Nettoyage des résidus du cycle précédent (ou d'un vieux run tué) ---
    # Tue les Firefox orphelins qui portent mon chemin tmp (et eux seuls) puis
    # les geckodriver du projet (leur ligne de commande ne contient pas le tmp),
    # et vide le dossier. Un profil encore verrouillé partira au cycle suivant.
    pkill -9 -f "$TMP_DIR"
    pkill -9 -f "$GECKODRIVER"
    sleep 5
    find "$TMP_DIR" -mindepth 1 -delete 2>/dev/null

    # Filet de sécurité : le pipeline s'arrête seul à 2h ; s'il gèle (appel
    # Selenium sans réponse), timeout le tue à 2h30 et le cycle repart.
    timeout -k 30 150m python -m scraping.pipeline

    echo "[$(date '+%F %T')] Pipeline terminé (code $?), nettoyage puis relance."
done
