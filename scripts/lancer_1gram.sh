#!/bin/bash
# Construit les bases 1gram des médias du pipeline, une par une, du plus petit
# CSV au plus gros, avec 4 min de pause entre chaque.
#
# Écartés : le_monde / le_figaro / les_echos / mediapart (bases ngram déjà
# construites, on n'y touche pas), agence_api (dépêches reprises par les autres
# médias), ouest_france et ouest_france_fil (remplacés par ouest_france2).
#
# Un média dont la base existe déjà est sauté : le script est relançable tel
# quel après une interruption.
#
# À lancer dans une session tmux : bash scripts/lancer_1gram.sh

RACINE=/data/elias/stage-mids
ECARTES=" le_monde le_figaro les_echos mediapart agence_api ouest_france ouest_france_fil "
PAUSE=240

cd "$RACINE" || exit 1

# Verrou : le vocabulaire partagé interdit deux constructions simultanées.
exec 9>"$RACINE/1gram.lock"
if ! flock -n 9; then
    echo "Refus : une série de constructions 1gram tourne déjà."
    exit 1
fi

source .venv/bin/activate

# ls -S trie par taille décroissante, -r inverse : du plus petit au plus gros.
MEDIAS=$(ls -S -r data/csv/*.csv | sed 's|.*/||; s|\.csv$||')

for media in $MEDIAS; do
    case "$ECARTES" in *" $media "*) continue ;; esac
    if [ -f "data/corpus/${media}_1gram.db" ]; then
        echo "[$(date '+%F %T')] $media : base déjà présente, on passe."
        continue
    fi

    echo "[$(date '+%F %T')] --- $media ($(du -h data/csv/$media.csv | cut -f1)) ---"
    python -u -m scripts.ngram_1gram "$media" 2>&1 | tee "data/logs/1gram_${media}.log"
    rc=${PIPESTATUS[0]}
    if [ "$rc" -ne 0 ]; then
        echo "[$(date '+%F %T')] $media : ÉCHEC (code $rc), on continue au suivant."
        # base incomplète mise de côté (jamais supprimée) : elle ne doit ni passer
        # pour une base valide, ni bloquer une relance du script.
        mv "data/corpus/${media}_1gram.db" "data/corpus/${media}_1gram.db.incomplet"
    fi

    echo "[$(date '+%F %T')] pause de $((PAUSE / 60)) min."
    sleep "$PAUSE"
done

echo "[$(date '+%F %T')] SÉRIE TERMINÉE."
