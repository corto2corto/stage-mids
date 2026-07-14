---
name: fiche-mot
description: Génère la fiche statistique d'un mot dans Le Monde sur une période donnée (série avec pics détectés, histogramme vs lois Poisson/binomiale négative, p-valeurs, test du χ², moments) — une page PDF comme celles de rapport.pdf. Utiliser quand Corto demande « la fiche de <mot> », « fais-moi la page de <mot> sur <période> », ou veut les mesures/plots d'un nouveau mot.
---

# Skill /fiche-mot

Produit `paper/donnees_maths/fiches/fiche_<slug>_<debut>_<fin>.pdf` : une page A4 portrait au **même rendu que les pages mot-par-mot de rapport.pdf** (Quarto→typst : série $f_t$ avec pics anormaux, histogramme de $X_t$ vs lois ajustées + p-valeurs, adéquation par test du χ² sur les résidus de Pearson — tableau χ²/ddl/p-valeur/verdict + histogrammes des $z_t$ vs N(0,1), même calcul que la route /fiche de l'API — tableau des moments great_tables, légendes Fig./Tableau). Tout le calcul est dans `paper/donnees_maths/fiche.py` (qui réutilise les fonctions de `rapport_lib.py` puis compile via `quarto render` — ne modifier ni l'un ni l'autre sans demande).

## Entrées

- **mot** : tel que donné par Corto (accents possibles).
- **période** : dates YYYYMMDD ; défaut `20200101 20241231`. Minimum ~60 jours (le script refuse en dessous : fit trop fragile).

## Étapes

1. **Slug** : minuscules, sans accents (`président` → `president`). Le CSV attendu est `paper/donnees_maths/<slug>_lemonde.csv`.

2. **Si le CSV manque, l'extraire** (serveur gallica, **lecture seule** — autorisé sans demander) :
   - Chercher **toutes les graphies** du mot (avec et sans accents — l'OCR a créé des doublons) :
     `ssh gallica "sqlite3 /data/elias/stage-mids/data/corpus/lemonde_ngram.db \"SELECT id, word FROM token WHERE word IN ('<avec accents>','<sans accents>')\""`
   - Extraire en **sommant les ids** trouvés, sur la **grille complète avec zéros** (années entières couvrant la période demandée, la fiche filtre ensuite) — modèle exact dans `paper/donnees_maths/extraire.sh` : `total_unigram LEFT JOIN` la somme des `unigram` des ids, `COALESCE(x, 0)`.
   - **Expression de deux mots** (ex. « Patrick Bruel ») : même schéma avec la table `bigram` (`WHERE w1=<id1> AND w2=<id2>`, requête indexée par la PK) et `total_bigram` comme dénominateur.
   - Sanity check : nb de lignes = nb de jours de la grille (1 827 pour 2020-2024), `X_t` plausible.

3. **Générer** :
   ```bash
   source .venv/bin/activate
   python paper/donnees_maths/fiche.py <slug> [debut] [fin]
   ```
   Le script imprime λ̂, μ̂, r̂, le nombre de pics et leurs dates, puis les χ²/ddl et p-valeurs des deux lois.

4. **Vérifier et rendre compte** : rasteriser le PDF (pymupdf, dans le scratchpad) et le regarder (axes, débordements) ; donner à Corto le chemin du PDF, les paramètres estimés et les pics datés (identifier l'événement si évident).

## Règles

- Ne rien installer ; venv du Mac ; serveur en lecture seule.
- Un mot très rare (X_t presque toujours 0) donne un fit dégénéré : le signaler plutôt que livrer une fiche trompeuse.
- Les PDF de `fiches/` sont gitignorés (`*.pdf`) : mentionner le chemin local, ne pas tenter de les committer.
