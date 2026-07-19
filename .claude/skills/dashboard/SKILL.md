---
name: dashboard
description: Met à jour le dashboard de suivi du stage MIDS (fichier HTML local site/static/dashboard.html) via scripts/maj_dashboard.py (injection des chiffres) + une passe éditoriale, puis l'ouvre en local. Utiliser quand Corto veut voir / rafraîchir le dashboard.
---

# Skill /dashboard

Met à jour le dashboard local depuis l'état frais du serveur, puis l'ouvre dans le navigateur.

## Références fixes

- **Fichier dashboard** : `site/static/dashboard.html` — fichier local, HORS suivi git (.gitignore), plus de publication GitHub Pages depuis le 19/07/2026. Consultation locale uniquement.
- **Source de données** : relevé en direct par ssh (lecture seule) — la session tmux `statut` et `statut_serveur.txt` n'existent plus.
- Rafraîchissement de l'affichage : `<meta http-equiv="refresh" content="600">` — l'onglet ouvert se recharge tout seul toutes les 10 min. Les données, elles, ne changent qu'en relançant la mise à jour.

## Ligne éditoriale (demandée par Corto)

- **Échecs de scraping** : ne PAS alerter dans « En ce moment » pour des vagues d'échecs temporaires, ni pour des médias qui échouent déjà fréquemment. Alerter UNIQUEMENT si vraiment anormal : script complètement arrêté sans action de Corto (session tmux `scrapping` disparue, plus aucun process `scraping.pipeline`), ou `urls.db` qui ne s'écrit plus depuis longtemps.
- **Disque /data** : jamais d'alerte (disque immense). Juste tenir la barre à jour.
- **Ordre des sections** : « Avancement du mémoire » reste en haut, juste après « En ce moment » (Corto la consulte souvent).

## Étape 1 — Injection des chiffres (script)

Lancer depuis la racine du dépôt : `python3 -m scripts.maj_dashboard`

Le script fait le ssh, met à jour tout le mécanique dans le HTML (heure de Paris, barre disque, tailles et dernières écritures des bases — via les marqueurs `id="maj-heure"`, `id="disque-*"`, `data-taille=` / `data-ecriture=`), et imprime un résumé : sessions tmux, process python, derniers panes `scrapping` et `build`. Ne PAS refaire ces éditions à la main ; signaler si le script affiche des ATTENTION.

## Étape 2 — Passe éditoriale (seulement si nécessaire)

D'après le résumé imprimé par le script, mettre à jour avec Edit — uniquement ce qui a réellement changé :
- bloc « En ce moment » (respecter la ligne éditoriale ci-dessus)
- section « Avancement du mémoire » si pertinent
- cartes « Runs sur le serveur » (croiser tmux + process + panes)
- pastilles « État » du tableau des bases si un statut a changé
- section « Tâches en attente » : ne PAS y toucher ici — gérée par le skill /task, source `.claude/taches.md`.

Si rien de notable n'a bougé côté serveur, sauter cette étape.

## Étape 3 — Ouvrir et rendre compte

`open site/static/dashboard.html`

Réponse courte : l'heure affichée (Paris) et ce qui a changé.
