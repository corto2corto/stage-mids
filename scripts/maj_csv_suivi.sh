#!/usr/bin/env bash
# Met à jour le site de suivi avec les dernières données de scraping.
#
# À lancer SUR LE SERVEUR (cron quotidien). Copie le journal frais
# (data/suivi_journal.csv, hors versionnement) dans les sources du site
# (site/sources/suivi/, versionné), puis commite et pousse sur main.
# C'est le push sur main qui déclenche la reconstruction du site par la
# GitHub Action.
#
# Ne commite QUE si le CSV a changé : pas de commit vide, pas de rebuild inutile.
# Ne touche qu'à un seul fichier versionné, que personne d'autre n'édite à la
# main : pas de conflit attendu avec le travail local.
#
# Cron (une fois par jour, à 4h) :
#   0 4 * * * /data/elias/stage-mids/scripts/maj_csv_suivi.sh >> /data/elias/stage-mids/data/maj_csv_suivi.log 2>&1

set -euo pipefail

REPO=/data/elias/stage-mids
SOURCE="$REPO/data/suivi_journal.csv"          # journal produit par le scraping (gitignoré)
CIBLE="$REPO/site/sources/suivi/suivi_journal.csv"   # copie publiée (versionnée)

cd "$REPO"

# Garde-fou : ne travaille que sur main (la branche qui publie le site).
branche=$(git branch --show-current)
if [ "$branche" != "main" ]; then
    echo "$(date '+%F %T') : abandon, le dépôt n'est pas sur main (branche : $branche)."
    exit 0
fi

if [ ! -f "$SOURCE" ]; then
    echo "$(date '+%F %T') : journal source introuvable ($SOURCE) — rien à faire."
    exit 0
fi

# Repart du dernier état distant avant toute modification (évite les rejets au push).
git pull --rebase --quiet

# Copie le journal frais dans les sources du site.
cp "$SOURCE" "$CIBLE"

# Rien n'a changé ? On s'arrête là : pas de commit, pas de rebuild.
if git diff --quiet -- "$CIBLE"; then
    echo "$(date '+%F %T') : journal inchangé — rien à publier."
    exit 0
fi

git add "$CIBLE"
git commit --quiet -m "data : mise à jour du journal de suivi ($(date '+%F'))"
git push --quiet origin main

echo "$(date '+%F %T') : journal mis à jour et poussé — le site va se reconstruire."
