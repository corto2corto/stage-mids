#!/usr/bin/env bash
# Attend la fin du build Le Monde, puis lance les précalculs top sur les 3 journaux.
# À détacher dans un tmux : tmux new -s top ; bash scripts/top_apres_lemonde.sh
set -u

BASE=/data/elias/stage-mids
DB=$BASE/data/corpus/lemonde_ngram.db
VENV=$BASE/.venv/bin/python
LOG=$BASE/data/top_apres_lemonde.log

echo "$(date '+%F %T') — attente de la fin du build Le Monde…" | tee -a "$LOG"

while true; do
    # 1. le process du build a disparu ?
    if pgrep -f "scripts.ngram_lemonde" > /dev/null; then
        etat="build encore en cours"
    # 2. la session tmux du build est fermée ? (sinon on attend qu'elle le soit)
    elif tmux has-session -t ngram_lemonde 2>/dev/null; then
        etat="process fini, session tmux ngram_lemonde encore ouverte"
    # 3. le build s'est-il terminé sans erreur ? (EXIT_CODE=0 écrit par la commande)
    elif [ -f /tmp/ngram_lemonde_status ] && ! grep -q "EXIT_CODE=0" /tmp/ngram_lemonde_status; then
        echo "$(date '+%F %T') — build Le Monde terminé en ERREUR, on n'enchaîne pas :" | tee -a "$LOG"
        cat /tmp/ngram_lemonde_status | tee -a "$LOG"
        exit 1
    # 4. la base répond-elle vraiment à une requête ? (plus verrouillée, VACUUM fini)
    elif ! "$VENV" - "$DB" <<'PY' 2>>"$LOG"; then
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True, timeout=5)
c.execute("SELECT 1 FROM unigram LIMIT 1").fetchone()   # lève si verrouillée/incomplète
PY
        etat="base pas encore interrogeable (verrou ou VACUUM en cours)"
    else
        break   # les 4 conditions sont réunies
    fi
    echo "$(date '+%F %T') — $etat, nouvelle vérification dans 30 min" | tee -a "$LOG"
    sleep 1800
done

echo "$(date '+%F %T') — build Le Monde OK, lancement des précalculs top" | tee -a "$LOG"
cd "$BASE" || exit 1
for corpus in lemonde lefigaro lesechos; do
    echo "$(date '+%F %T') — top_ngram $corpus…" | tee -a "$LOG"
    if "$VENV" -m scripts.top_ngram "$corpus" >> "$LOG" 2>&1; then
        echo "$(date '+%F %T') — $corpus terminé" | tee -a "$LOG"
    else
        echo "$(date '+%F %T') — ÉCHEC sur $corpus, arrêt" | tee -a "$LOG"
        exit 1
    fi
done
echo "$(date '+%F %T') — tous les tops sont construits ✓" | tee -a "$LOG"
