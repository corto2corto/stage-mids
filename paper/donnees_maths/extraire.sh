#!/usr/bin/env bash
# Extraction des series ngram (Le Monde) pour la partie maths du memoire.
# Grille complete 2020-2024 avec zeros reinjectes (LEFT JOIN sur total_unigram).
# Lecture seule sur gallica. A lancer depuis la racine du projet.
set -euo pipefail

DB=/data/elias/stage-mids/data/corpus/lemonde_ngram.db
OUT=paper/donnees_maths
D1=20200101
D2=20241231

extraire () {
  local nom="$1" ids="$2"
  echo "  -> $nom (w1 in $ids)"
  ssh gallica "sqlite3 -csv -header $DB" > "$OUT/${nom}_lemonde.csv" <<SQL
SELECT t.date AS date, COALESCE(u.x, 0) AS X_t, t.total AS N_t
FROM total_unigram t
LEFT JOIN (SELECT date, SUM(n) AS x FROM unigram
           WHERE w1 IN ($ids) AND date BETWEEN $D1 AND $D2 GROUP BY date) u
  ON u.date = t.date
WHERE t.date BETWEEN $D1 AND $D2
ORDER BY t.date;
SQL
}

echo "Extraction 2020-2024 ..."
extraire gouvernement 76
extraire president    "2173,16704"
extraire inflation    24247
extraire economie     "7617,59449"
extraire guerre       3014
extraire climat       3562

echo "OK ->"
wc -l "$OUT"/gouvernement_lemonde.csv "$OUT"/president_lemonde.csv "$OUT"/inflation_lemonde.csv "$OUT"/economie_lemonde.csv "$OUT"/guerre_lemonde.csv "$OUT"/climat_lemonde.csv
