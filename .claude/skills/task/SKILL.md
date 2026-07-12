---
name: task
description: Note une tâche identifiée au fil de la discussion (contexte + piste de résolution envisagée) dans taches.md et l'ajoute à la section « Tâches en attente » du dashboard, avec un prompt de reprise prêt à coller dans une future session Claude. Utiliser quand Corto veut garder une tâche pour plus tard (« /task », « note ça pour plus tard »), ou pour marquer une tâche faite.
---

# Skill /task

Capture une tâche discutée dans la session courante, pour la reprendre plus tard depuis le dashboard.

## Références fixes

- **Source de vérité des tâches** : `.claude/taches.md`.
- **Dashboard** : fichier local versionné `site/static/dashboard.html` (dans le dépôt). Publié sur GitHub Pages à `https://corto2corto.github.io/stage-mids/dashboard.html` (Evidence copie `site/static/` à la racine du build). On l'édite directement, puis on push sur main pour publier. Plus d'artifact Claude (abandonné le 12/07/2026).

## Étape 1 — Comprendre la tâche depuis la conversation

Relire la discussion et en extraire :
- un **titre court** (une ligne) et un **slug** kebab-case (servira d'id HTML) ;
- le **contexte** : ce qui a été constaté, où, pourquoi c'est un problème ;
- la **piste de résolution** discutée — celle qui a été retenue, pas l'inventaire des options ;
- les **fichiers, bases et commandes** concernés, avec les détails précis établis dans la conversation (noms exacts, numéros de ligne, décisions prises).

S'il y a plusieurs tâches candidates dans la conversation, demander à Corto laquelle noter (AskUserQuestion).

## Étape 2 — Rédiger le prompt de reprise

Le prompt sera collé dans une **nouvelle session Claude sur ce dépôt** : CLAUDE.md et la mémoire y seront déjà chargés, donc ne pas répéter le contexte général du projet. Le prompt porte ce qu'une session neuve NE sait PAS :

- le constat de départ (symptôme observé, où on le voit) ;
- la piste retenue, en étapes concrètes et ordonnées ;
- les fichiers/bases exacts et les contraintes décidées en discussion (ex. « ne pas reconstruire les bases », « UPDATE ciblé seulement ») ;
- comment vérifier le résultat à la fin ;
- si la tâche touche au serveur, terminer par « Me demander avant de lancer quoi que ce soit sur le serveur. »

Ton : instructions directes à Claude, en français, 10-20 lignes. Voir l'entrée `stopwords-tops` de taches.md comme modèle.

## Étape 3 — Enregistrer dans taches.md

Ajouter l'entrée AVANT la section « ## Faites », au format existant : `## <slug> — <titre>`, date d'ajout, branche, **Contexte**, **Piste envisagée**, **Prompt** en bloc de code. Ce fichier est la source de vérité — le dashboard n'est qu'un affichage.

## Étape 4 — Mettre à jour le dashboard

Éditer directement `site/static/dashboard.html` (Edit, pas de récupération distante) : ajouter une carte dans la section « Tâches en attente », sur le modèle d'une carte existante — `carte-titre` (titre), `carte-sous` (date + branche), bouton `btn-prompt` avec `data-panneau="prompt-<slug>"`, `p.desc` (une phrase : constat + piste), panneau `panneau-prompt` d'id `prompt-<slug>` contenant le `<pre>` du prompt et un bouton `btn-copier` avec `data-copie="prompt-<slug>"`. Attention : dans le `<pre>`, échapper `<`, `>` et `&` en `&lt;`, `&gt;`, `&amp;`. Le `<script>` en bas de page gère déjà tous les boutons — ne rien y ajouter.

## Tâche terminée

Si Corto dit qu'une tâche est faite : déplacer son entrée de taches.md vers « ## Faites » (garder la trace, on peut retirer le prompt), et supprimer sa carte de `site/static/dashboard.html` (Edit).

## Étape 5 — Rendre compte

Une ou deux lignes : la tâche notée, où (taches.md + dashboard local), et rappeler que la publication sur GitHub Pages se fait via un push sur main (`/github`). Ne pas push soi-même sans que Corto le demande.
