---
name: qmd-pdf
description: Génère un PDF depuis un fichier .md ou .qmd via quarto (moteur typst), puis supprime les fichiers annexes de quarto (dossier *_files, .html, .typ, .quarto) pour ne laisser que le .qmd et le .pdf. Utiliser quand Corto demande un PDF depuis un markdown, ou quand Claude rédige un document destiné à être rendu en PDF.
model: claude-sonnet-5
---

# Skill /qmd-pdf

Produit `<base>.pdf` à côté de `<base>.qmd`, et ne laisse rien d'autre : le
`.qmd` reste la source transportable, le PDF se régénère à la demande.

## Étapes

1. **Si la source est un .md** : la copier en `<base>.qmd` (même dossier, même
   nom de base). S'assurer qu'elle commence par un en-tête YAML ; sinon
   l'ajouter :

   ```yaml
   ---
   title: "<titre>"
   lang: fr
   format:
     typst:
       papersize: a4
       margin:
         x: 2cm
         y: 1.6cm
   ---
   ```

   Typst est le format par défaut : rapide, et sans dépendance LaTeX (le
   BasicTeX du Mac a des paquets manquants, cf. mémoire rsfs10). Ne passer en
   LaTeX que sur demande explicite.

2. **Rendre**, depuis le dossier du fichier :
   `quarto render <base>.qmd --quiet`
   (si le .qmd contient des chunks python exécutables : `source .venv/bin/activate` d'abord).

3. **Nettoyer** le dossier — ne garder que `<base>.qmd` et `<base>.pdf` :

   ```bash
   rm -rf "<base>_files" "<base>.html" "<base>.typ" .quarto
   ```

   (et les artefacts LaTeX `<base>.aux/.log/.toc` si ce format a été utilisé).

4. **Vérifier** que le PDF existe ; en cas de doute sur le rendu (tableaux,
   maths, débordements), rasteriser une page avec pymupdf dans le scratchpad
   et la regarder.

5. Donner le chemin du `.pdf` et du `.qmd` conservés.

## Écrire le .qmd : figures dans des chunks, jamais de png

Règle par défaut pour tout rapport texte + graphes : **la figure se calcule
dans un chunk `{python}` du .qmd**. On ne génère pas de `.png` sur le disque
pour y faire pointer le document — le dépôt ne garde que le `.qmd` et son
`.pdf`. Modèle de référence : `campagne_pca/rapport_qmd/`.

En-tête typique :

```yaml
---
title: "<titre neutre>"
lang: fr
format:
  typst:
    papersize: a4
    margin: {x: 2.2cm, y: 2cm}
    fontsize: 10.5pt
    fig-cap-location: bottom
    fig-format: png
    fig-dpi: 200
execute:
  echo: false
  warning: false
jupyter: python3
---
```

Le chunk appelle la fonction de figure avec **`chemin=None`** : elle fait
`plt.show()` et Quarto insère l'image (cf. `rendre()` dans
`campagne_pca/scripts/figures_lib.py`). Les données lourdes viennent d'un
cache préparé en amont, pas d'un recalcul à chaque rendu. Piège : un module
qui impose `matplotlib.use("Agg")` à l'import casse la capture sous Jupyter —
repasser au backend inline si `"ipykernel" in sys.modules`.

## Mise en page

Bloc `{=typst}` de préambule, après le chunk d'imports :

```typst
#set par(justify: true)
#show figure.caption: set text(size: 8.5pt, fill: rgb("#52514e"))
#show figure: set block(above: 1.2em, below: 1.4em)
```

- **Pas de grands blancs** : encadrer une figure isolée de `#v(1fr)` pour la
  centrer verticalement, et placer les `#pagebreak()` soi-même plutôt que de
  subir la coupe automatique.
- **Côte à côte** : `#grid(columns: N, column-gutter: 1.1cm, align: horizon, …)`.
- **Tableau large** : l'encadrer de `#set text(size: 9pt)` / `#set text(size: 10.5pt)`.
- **Dimensions** : elles se règlent côté matplotlib (`figsize`, largeurs
  usuelles 6,4 à 9,6 pouces) + `fig.tight_layout()` — pas par redimensionnement
  dans le document.

Texte court et pertinent : le rapport montre le résultat, il ne réexplique pas
la méthode ni les choix qui y ont mené.

## Règles

- Ne rien installer (quarto est déjà sur le Mac).
- Les PDF sont souvent gitignorés : donner le chemin local, ne pas les committer.
- Ne jamais supprimer le `.qmd` (contrairement aux scripts fiche.py/fiches_bnb.py
  qui suppriment leur .qmd intermédiaire : ici le .qmd EST la source).
