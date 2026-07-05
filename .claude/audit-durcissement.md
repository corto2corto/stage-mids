# Chantier — Audit et durcissement du pipeline (juillet 2026)

Chantier bonus du sprint Fable (5–7 juillet 2026) : session d'audit complet du pipeline stage-mids, à lancer si le temps le permet après les 5 autres projets (~/Documents/project/vie-watch, ~/Documents/project/stage-preview, ~/Documents/project/goat-dashboard, ~/Documents/project/uk-application-kit, ~/Documents/project/artist).

## Périmètre
- **Couverture de tests** : le pipeline (scraping, scripts d'init de base, API ngram) n'a pas de suite de tests — en construire une.
- **Robustesse de la reprise sur crash** : le scraping tourne en continu sur le serveur (session tmux `scrapping`, `scripts/lancer.sh`) — auditer ce qui se passe en cas de crash de Firefox, de perte réseau, de corruption SQLite.
- **Monitoring** : le dashboard Evidence (`site/`) existe ; vérifier qu'on détecte vite un scraping silencieusement arrêté ou dégradé (volume anormal, taux d'échec paywall).

## Pourquoi
Ce pipeline alimente le mémoire de fin de master de Corto ET le projet de détection de surges présenté dans ~/Documents/project/stage-preview. Sa fiabilité conditionne directement les deux.
