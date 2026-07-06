---
name: task
description: Note une tâche identifiée au fil de la discussion (contexte + piste de résolution envisagée) dans taches.md et l'ajoute à la section « Tâches en attente » du dashboard, avec un prompt de reprise prêt à coller dans une future session Claude. Utiliser quand Corto veut garder une tâche pour plus tard (« /task », « note ça pour plus tard »), ou pour marquer une tâche faite.
---

# Skill /task

Capture une tâche discutée dans la session courante, pour la reprendre plus tard depuis le dashboard.

## Références fixes

- **Source de vérité** : `.claude/taches.md`.
- **Artifact dashboard** : `https://claude.ai/code/artifact/42437963-1ba0-47af-9c84-55fc80c2b424` — HTML `dashboard-stage-mids.html` dans le scratchpad (le récupérer via l'Étape 0 du skill /dashboard s'il n'est pas dans le scratchpad courant).

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

1. Récupérer `dashboard-stage-mids.html` (Étape 0 du skill /dashboard).
2. Ajouter une carte dans la section « Tâches en attente », sur le modèle de la carte existante : `carte-titre` (titre), `carte-sous` (date + branche), bouton `btn-prompt` avec `data-panneau="prompt-<slug>"`, `p.desc` (une phrase : constat + piste), panneau `panneau-prompt` d'id `prompt-<slug>` contenant le `<pre>` du prompt et un bouton `btn-copier` avec `data-copie="prompt-<slug>"`. Le `<script>` en bas de page gère déjà tous les boutons — ne rien y ajouter.
3. Redéployer via l'outil Artifact (favicon 📊, `url` = l'artifact fixe ci-dessus).
4. Recopier le HTML mis à jour sur les copies récentes des autres sessions (`find /private/tmp/claude-*/-Users-corto-Documents-stage-mids -name dashboard-stage-mids.html`), pour qu'une boucle /dashboard encore vivante ailleurs n'écrase pas la nouvelle carte au prochain rafraîchissement.

## Tâche terminée

Si Corto dit qu'une tâche est faite : déplacer son entrée de taches.md vers « ## Faites » (garder la trace, on peut retirer le prompt), supprimer sa carte du dashboard, redéployer et recopier comme à l'Étape 4.

## Étape 5 — Rendre compte

Une ou deux lignes : la tâche notée, et rappel que le prompt de reprise est derrière le bouton « Prompt » du dashboard.
