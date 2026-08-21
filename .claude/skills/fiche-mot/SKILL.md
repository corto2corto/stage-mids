---
name: fiche-mot
description: Génère la fiche statistique d'un mot dans Le Monde sur une période donnée (série avec pics détectés, histogramme vs lois Poisson/binomiale négative, p-valeurs, test du χ², moments) — une page PDF comme celles de rapport.pdf. Utiliser quand Corto demande « la fiche de <mot> », « fais-moi la page de <mot> sur <période> », ou veut les mesures/plots d'un nouveau mot.
---

# Skill /fiche-mot

Produit `paper/donnees_maths/fiches/fiche_<slug>_<debut>_<fin>.pdf` : une page A4 portrait au **même rendu que les pages mot-par-mot de rapport.pdf** (Quarto→typst : série $f_t$ avec pics anormaux, histogramme de $X_t$ vs lois ajustées + p-valeurs, adéquation par test du χ² sur les résidus de Pearson — tableau χ²/ddl/p-valeur + histogrammes des $z_t$ vs N(0,1), même calcul que la route /fiche de l'API — tableau des moments, légendes Fig./Tableau ; tous les tableaux sont du typst natif, aucune image). Tout le calcul est dans `rupture/fiches.py`, la bibliothèque partagée avec `rapport.qmd` et le recueil `fiches_mots.qmd` ; `paper/donnees_maths/fiche.py` ne fait qu'assembler la page et compiler via `quarto render` — ne modifier ni l'un ni l'autre sans demande.

## Entrées

- **mot** : tel que donné par Corto (accents possibles).
- **période** : dates YYYYMMDD ; défaut `20200101 20241231`. Minimum ~60 jours (le script refuse en dessous : fit trop fragile).

## Étapes

1. **Générer** — le mot peut être donné avec ses accents ; le PDF est nommé
   d'après le slug (`président` → `fiche_president_…`) :

   ```bash
   source .venv/bin/activate
   python paper/donnees_maths/fiche.py "<mot>" [debut] [fin]
   ```

   Le script imprime λ̂, μ̂, r̂, le nombre de pics et leurs dates, puis les χ²/ddl
   et p-valeurs des deux lois.

2. **Les données sont trouvées toutes seules.** `rupture/fiches.py` lit d'abord
   `paper/donnees_maths/series_mots.csv` (43 mots figés dans le dépôt, une
   colonne par mot). Un mot absent de cette table est extrait de la base via
   `rupture/extraire.py` (gallica en **lecture seule** — autorisé sans demander,
   ~2 s) et mis en cache dans `rupture/cache/` : graphies avec/sans accents
   sommées, zéros réinjectés, expressions de 2-3 mots gérées.

3. **Pour figer un mot dans le dépôt** (fiche destinée au mémoire) : l'ajouter à
   `MOTS` ou à `RECUEIL` dans `rupture/fiches.py`, puis relancer
   `python paper/donnees_maths/series.py`.

4. **Vérifier et rendre compte** : rasteriser le PDF (pymupdf, dans le
   scratchpad) et le regarder (axes, débordements) ; donner à Corto le chemin du
   PDF, les paramètres estimés et les pics datés (identifier l'événement si
   évident).

## Règles

- Ne rien installer ; venv du Mac ; serveur en lecture seule.
- Un mot très rare (X_t presque toujours 0) donne un fit dégénéré : le signaler plutôt que livrer une fiche trompeuse.
- Les PDF de `fiches/` sont gitignorés (`*.pdf`) : mentionner le chemin local, ne pas tenter de les committer.
