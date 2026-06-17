#!/usr/bin/env bash
# Met à jour le site de suivi avec les dernières données de scraping.
#
# À lancer SUR LE SERVEUR (cron quotidien). Rafraîchit les sources du site
# (site/sources/suivi/, versionnées) :
#   - suivi_journal.csv : copié depuis data/ (taux de réussite dans le temps) ;
#   - avancement.csv    : régénéré depuis urls.db (avancement par média).
# Puis commite et pousse sur main, ce qui déclenche la reconstruction du site
# par la GitHub Action.
#
# Ne commite QUE si au moins un CSV a changé : pas de commit vide, pas de rebuild
# inutile. Ne touche qu'à des fichiers que personne n'édite à la main.
#
# Cron (une fois par jour, à 4h) :
#   0 4 * * * /data/elias/stage-mids/scripts/maj_csv_suivi.sh >> /data/elias/stage-mids/data/maj_csv_suivi.log 2>&1

set -euo pipefail

REPO=/data/elias/stage-mids
SOURCE="$REPO/data/suivi_journal.csv"                 # journal produit par le scraping (gitignoré)
DOSSIER_SITE="$REPO/site/sources/suivi"               # sources versionnées lues par le site
JOURNAL_SITE="$DOSSIER_SITE/suivi_journal.csv"
AVANCEMENT_SITE="$DOSSIER_SITE/avancement.csv"

cd "$REPO"

# Garde-fou : ne travaille que sur main (la branche qui publie le site).
branche=$(git branch --show-current)
if [ "$branche" != "main" ]; then
    echo "$(date '+%F %T') : abandon, le dépôt n'est pas sur main (branche : $branche)."
    exit 0
fi

# Repart du dernier état distant avant toute modification (évite les rejets au push).
git pull --rebase --quiet

# 1) Journal de suivi : copie du fichier frais (s'il existe).
if [ -f "$SOURCE" ]; then
    cp "$SOURCE" "$JOURNAL_SITE"
fi

# 2) Avancement : régénéré depuis urls.db via le venv du dépôt.
source "$REPO/.venv/bin/activate"
python -m scraping.suivi exporter_avancement > /dev/null

# Rien n'a changé ? On s'arrête là : pas de commit, pas de rebuild.
if git diff --quiet -- "$JOURNAL_SITE" "$AVANCEMENT_SITE"; then
    echo "$(date '+%F %T') : données inchangées — rien à publier."
    exit 0
fi

git add "$JOURNAL_SITE" "$AVANCEMENT_SITE"
git commit --quiet -m "data : mise à jour des données de suivi ($(date '+%F'))"
git push --quiet origin main

echo "$(date '+%F %T') : données mises à jour et poussées — le site va se reconstruire."
