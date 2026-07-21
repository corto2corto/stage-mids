---
name: qmd-pdf
description: Génère un PDF depuis un fichier .md ou .qmd via quarto (moteur typst), puis supprime les fichiers annexes de quarto (dossier *_files, .html, .typ, .quarto) pour ne laisser que le .qmd et le .pdf. Utiliser quand Corto demande un PDF depuis un markdown, ou quand Claude rédige un document destiné à être rendu en PDF.
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

## Règles

- Ne rien installer (quarto est déjà sur le Mac).
- Les PDF sont souvent gitignorés : donner le chemin local, ne pas les committer.
- Ne jamais supprimer le `.qmd` (contrairement aux scripts fiche.py/fiches_bnb.py
  qui suppriment leur .qmd intermédiaire : ici le .qmd EST la source).
