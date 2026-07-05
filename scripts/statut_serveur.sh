#!/bin/bash
# Collecte l'état du serveur pour le dashboard de suivi, toutes les 20 min.
# Tourne dans la session tmux "statut" :
#   tmux new-session -d -s statut 'bash /data/elias/stage-mids/scripts/statut_serveur.sh'

RACINE=/data/elias/stage-mids
SORTIE=$RACINE/data/statut_serveur.txt

while true; do
  {
    echo "=== date ==="
    date "+%Y-%m-%d %H:%M:%S %Z"
    echo "=== tmux ==="
    tmux ls 2>&1
    echo "=== process python ==="
    ps -eo pid,etime,%cpu,%mem,args | grep python | grep -v grep
    echo "=== bases ==="
    ls -lh $RACINE/data/*.db $RACINE/data/corpus/*.db 2>/dev/null
    echo "=== disque /data ==="
    df -h /data | tail -1
    echo "=== pane scrapping ==="
    tmux capture-pane -t scrapping -p 2>/dev/null | tail -30
    echo "=== pane construction_bdd ==="
    tmux capture-pane -t construction_bdd -p 2>/dev/null | tail -15
    echo "=== pane api ==="
    tmux capture-pane -t api -p 2>/dev/null | tail -5
  } > "$SORTIE".tmp && mv "$SORTIE".tmp "$SORTIE"
  sleep 1200
done
