---
name: dashboard
description: Met à jour le dashboard de suivi du stage MIDS (fichier HTML local site/static/dashboard.html) à partir de l'état du serveur gallica, puis publie sur GitHub Pages via un push sur main. Utiliser quand Corto veut voir / rafraîchir le dashboard.
---

# Skill /dashboard

Met à jour le dashboard de suivi depuis l'état frais du serveur, puis (si Corto le demande) publie.

## Références fixes

- **Fichier dashboard** : `site/static/dashboard.html` — fichier local versionné dans le dépôt. On l'édite directement avec Edit, aucune récupération distante.
- **Publication** : GitHub Pages, à `https://corto2corto.github.io/stage-mids/dashboard.html`. Le workflow `.github/workflows/deploy.yml` build le site Evidence à chaque push sur `main` touchant `site/**` ; Evidence copie `site/static/` à la racine du build (`site/build/stage-mids/`). Donc **publier = push sur main** (via `/github`) — pas de scp, pas d'artifact Claude (abandonné le 12/07/2026).
- **Source de données** : `/data/elias/stage-mids/data/statut_serveur.txt` sur gallica (collecté par la session tmux `statut`, quand elle tourne).
- Le serveur est en **UTC** → toujours convertir en **heure de Paris** (+2 en été) pour l'affichage.
- Rafraîchissement de l'affichage : la page contient un `<meta http-equiv="refresh" content="600">` — l'onglet ouvert se recharge tout seul toutes les 10 min. Les **données**, elles, ne changent que quand on régénère le HTML et qu'on push (choix acté le 12/07/2026 : régénération à la demande, pas de cron autonome).

## Ligne éditoriale (demandée par Corto)

- **Échecs de scraping** : ne PAS alerter dans « En ce moment » pour des vagues d'échecs temporaires, ni pour des médias qui échouent déjà fréquemment. Alerter UNIQUEMENT si vraiment anormal : script complètement arrêté sans action de Corto (session tmux `scrapping` disparue, plus aucun process `scraping.pipeline`), ou `urls.db` qui ne s'écrit plus depuis longtemps.
- **Disque /data** : jamais d'alerte (disque immense). Juste tenir la barre à jour.
- **Ordre des sections** : « Avancement du mémoire » reste en haut, juste après « En ce moment » (Corto la consulte souvent).

## Étape 1 — Mise à jour du HTML

1. Récupérer l'état frais : `ssh gallica "cat /data/elias/stage-mids/data/statut_serveur.txt"`.
2. Lire l'horodatage sur la ligne sous `=== date ===` (ne JAMAIS l'inventer), le convertir en heure de Paris.
3. Éditer `site/static/dashboard.html` (Edit) — n'éditer QUE les valeurs qui ont changé, ne pas réécrire tout le HTML :
   - ligne « Mise à jour : ... » (heure de Paris)
   - bloc « En ce moment » (respecter la ligne éditoriale ci-dessus)
   - section « Avancement du mémoire » si pertinent
   - cartes « Runs sur le serveur » (croiser `=== tmux ===` + `=== process python ===` + les panes capturés)
   - tableau « Bases de données » (tailles + dernières écritures depuis `=== bases ===`)
   - barre disque `/data` (depuis `=== disque /data ===`)
   - section « Tâches en attente » : ne PAS y toucher ici — elle est gérée par le skill /task, source `.claude/taches.md`.

## Étape 2 — Publier (seulement si Corto le demande)

La publication se fait par un push sur `main` (le workflow Pages se déclenche sur les changements de `site/**`). **Ne pas push de sa propre initiative** — attendre que Corto le demande, puis passer par `/github`. Sinon, le laisser prévisualiser en local : `open site/static/dashboard.html`.

## Étape 3 — Rendre compte

Réponse courte : l'heure affichée (Paris), ce qui a changé, et si c'est publié ou juste prêt en local à pousser.
