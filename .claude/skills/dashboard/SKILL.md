---
name: dashboard
description: Met à jour le dashboard de suivi du stage MIDS (artifact Claude) à partir de l'état du serveur gallica, et arme une boucle de rafraîchissement automatique toutes les 20 min qui vit tant que la session Claude reste ouverte. Utiliser quand Corto veut voir / rafraîchir le dashboard, ou relancer la boucle de MAJ après une nouvelle session.
---

# Skill /dashboard

Met à jour le dashboard de suivi et arme (ou ré-arme) sa boucle de rafraîchissement.

## Références fixes

- **Artifact dashboard** : `https://claude.ai/code/artifact/42437963-1ba0-47af-9c84-55fc80c2b424`
- **HTML source** : `dashboard-stage-mids.html` dans le scratchpad de la session courante.
- **Source de données** : `/data/elias/stage-mids/statut_serveur.txt` sur gallica (collecté par la session tmux `statut`, toutes les 20 min).
- Le serveur est en **UTC** → toujours convertir en **heure de Paris** (+2 en été) pour l'affichage.

## Étape 0 — S'assurer d'avoir le HTML source dans le scratchpad courant

Le HTML n'est pas forcément dans le scratchpad de CETTE session (il a pu être créé par une session précédente).

1. Vérifier s'il existe : `ls <scratchpad_courant>/dashboard-stage-mids.html`.
2. S'il n'existe pas, le récupérer depuis le scratchpad le plus récent d'une session antérieure :
   `find /private/tmp/claude-*/-Users-corto-Documents-stage-mids -name dashboard-stage-mids.html` puis copier le plus récent (comparer les mtimes avec `ls -laT`, BSD ls sur macOS — pas `--time-style`) dans le scratchpad courant. Copier aussi `roadmap-stage-mids.html` s'il est là.

## Étape 1 — Mise à jour immédiate

1. Récupérer l'état frais : `ssh gallica "cat /data/elias/stage-mids/statut_serveur.txt"`.
2. Lire l'horodatage sur la ligne sous `=== date ===` (ne JAMAIS l'inventer), le convertir en heure de Paris.
3. Éditer `dashboard-stage-mids.html` — n'éditer QUE les valeurs qui ont changé, ne pas réécrire tout le HTML :
   - ligne « Mise à jour : ... » (heure de Paris)
   - bloc « En ce moment »
   - cartes « Runs sur le serveur » (croiser `=== tmux ===` + `=== process python ===` + les panes capturés)
   - tableau « Bases de données » (tailles + dernières écritures depuis `=== bases ===`)
   - barre disque `/data` (depuis `=== disque /data ===`)
   - section « Avancement du mémoire » si pertinent
4. Redéployer : appeler l'outil `Artifact` avec `file_path` = le HTML, `favicon` "📊", `url` = l'artifact fixe ci-dessus.

## Étape 2 — Armer la boucle (gestion du conflit de crons)

Une seule boucle doit tourner à la fois : le dernier `/dashboard` lancé gagne.

1. `CronList` pour lister les crons de session.
2. **Supprimer tout cron de MAJ dashboard existant** (n'importe quel cron dont le prompt met à jour cet artifact — le mien d'un lancement précédent, ou d'une session antérieure encore vivante). Utiliser `CronDelete` sur chacun.
3. Créer **un seul** cron neuf, `12,32,52 * * * *` (juste après les collectes serveur à :07/:27/:47), dont le prompt refait l'Étape 1 (collecte → édition ciblée → redéploiement via `url`). Rappeler dans le prompt : UTC→Paris, horodatage jamais inventé, ne pas tout réécrire.

Prévenir Corto : la boucle est **session-only** (meurt à la fermeture de Claude) et **expire après 7 jours**. Relancer `/dashboard` dans une nouvelle session pour la ré-armer — le skill nettoie alors l'ancien cron automatiquement.

## Étape 3 — Rendre compte

Réponse courte : l'heure affichée (Paris), ce qui a changé depuis la dernière MAJ, et l'ID du cron armé.
