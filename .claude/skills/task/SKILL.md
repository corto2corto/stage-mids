---
name: task
description: Note une tâche identifiée au fil de la discussion (contexte + piste de résolution envisagée) sous forme d'issue GitHub, avec un prompt de reprise prêt à coller dans une future session Claude. Utiliser quand Corto veut garder une tâche pour plus tard (« /task », « note ça pour plus tard »), ou pour marquer une tâche faite.
---

# Skill /task

Capture une tâche discutée dans la session courante sous forme d'issue GitHub, pour la reprendre plus tard.

## Références fixes

- **Source de vérité des tâches** : les issues du dépôt `corto2corto/stage-mids`, label `tâche`. Plus de `.claude/taches.md` ni de dashboard : ne pas y écrire.
- **Outil** : `gh` (connecté au compte `corto2corto`, protocole SSH).
- **Le dépôt est public** : tout ce qui est écrit dans l'issue est visible de tous.

## Étape 1 — Comprendre la tâche depuis la conversation

Relire la discussion et en extraire :
- un **titre court** (une ligne) ;
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

Ton : instructions directes à Claude, en français, 10-20 lignes. Voir l'issue n°2 (`stopwords-tops`) comme modèle.

## Étape 3 — Vérifier qu'il n'y a rien de sensible

L'issue est publique. Avant de créer, relire le texte : ni identifiant, mot de passe, jeton, adresse IP, e-mail, ni nom de compte dans un chemin serveur (écrire `/opt/<compte>/…`, `/data/<compte>`). En cas de doute, retirer le détail ou demander à Corto.

## Étape 4 — Créer l'issue

Écrire le corps dans un fichier du scratchpad (jamais dans le dépôt), au format :

```
- Ajoutée : <date>
- Branche : <branche>

**Contexte** : ...

**Piste envisagée** : ...

**Prompt** :

<bloc de code avec le prompt de reprise>
```

Puis :

```
gh issue create -R corto2corto/stage-mids --title "<titre>" --label tâche --body-file <fichier>
```

## Tâche terminée

Si Corto dit qu'une tâche est faite : retrouver son numéro (`gh issue list -R corto2corto/stage-mids --label tâche`), puis `gh issue close <n> -R corto2corto/stage-mids --comment "<une ligne sur ce qui a été fait>"`. Une issue peut aussi être fermée par un commit contenant « closes #<n> ».

## Étape 5 — Rendre compte

Une ligne : la tâche notée, son numéro et l'URL de l'issue. Rien à push, les issues ne passent pas par git.
