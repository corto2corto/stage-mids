#!/bin/bash
SERVEUR="gallica"
REMOTE_DIR="/data/elias/stage-mids/data/csv"
LOCAL_DIR="$(dirname "$0")/../tmp"

mkdir -p "$LOCAL_DIR"

for chemin in $(ssh "$SERVEUR" "ls $REMOTE_DIR/*.csv 2>/dev/null"); do
    nom=$(basename "$chemin")
    ssh "$SERVEUR" "{ head -n 1 $chemin; tail -n 100 $chemin; }" > "$LOCAL_DIR/$nom"
done
