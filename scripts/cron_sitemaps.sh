#!/bin/bash
# Cycle quotidien des sitemaps (appelé par cron 2x/jour) :
#   1. scripts.sitemap_news : lit les sitemap.news de chaque média et ajoute
#      aux CSV d'URLs les articles récents manquants ;
#   2. scripts.verser_nouveaux : verse ces URLs en base (INSERT OR IGNORE,
#      l'index unique (media,url) écarte les connues).
# Idempotent : un raté un jour est rattrapé le lendemain (fenêtre news ~48 h).
# À lancer depuis la racine du dépôt de prod.

RACINE="/data/elias/stage-mids"
cd "$RACINE" || exit 1

# Verrou : une seule instance à la fois (deux versements concurrents inutiles).
exec 9>"$RACINE/cron_sitemaps.lock"
if ! flock -n 9; then
    echo "$(date -u +'%F %T') UTC : cycle déjà en cours, on saute."
    exit 0
fi

# Temp SQLite sur /data (la partition racine / n'a que ~2 Go libres).
export SQLITE_TMPDIR="$RACINE/data/sqlite_tmp"

echo "=== $(date -u +'%F %T') UTC : début cycle sitemaps ==="
.venv/bin/python -m scripts.sitemap_news
.venv/bin/python -m scripts.verser_nouveaux
echo "=== $(date -u +'%F %T') UTC : fin cycle sitemaps ==="
