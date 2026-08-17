# Audit du dépôt stage-mids — regard d'ingénieur extérieur

*Fichier temporaire, 11/07/2026. Aucune modification de code : uniquement une lecture et des recommandations.*

## 1. Comment je procéderais si je reprenais ce projet

Le réflexe naturel serait de juger le code du pipeline. Ce serait une erreur de priorité :
le produit final de ce projet n'est pas le pipeline, c'est **le corpus** (les CSV d'articles
et les bases ngram) qui servira à répondre à la question de recherche. Le pipeline peut être
moche et le mémoire excellent ; l'inverse est impossible. Donc mon ordre de travail :

1. **Auditer la qualité du corpus existant** avant d'écrire une ligne de code : taux de dates
   vides ou non normalisées par média, doublons dans les CSV de sortie, part d'articles
   potentiellement tronqués (colonne `free`), trous de couverture temporelle par média.
2. **Verrouiller ce qui est irréversible** : tout ce qui écrit dans les CSV d'articles et
   dans `urls.db` (une URL passée en etat=4 ne sera plus jamais tentée ; une ligne CSV
   corrompue reste corrompue).
3. **Factoriser avant d'étendre** : les bases ngram vont passer de 3 à ~29 médias ; c'est
   maintenant qu'il faut un script paramétré et une tokenisation partagée, pas après.
4. Seulement ensuite : confort, refactorings, outillage.

## 2. Ce qui est solide (à préserver tel quel)

- **La documentation des décisions** : chaque réglage du code porte sa justification datée
  (« mesuré le 07/07 », « A/B 4s vs 6s »). C'est rare et précieux : on peut rejouer chaque
  choix. Le journal.qmd complète bien. Ne pas perdre cette discipline.
- **L'architecture par moteurs** (`firefox` / `log` / `basic` / `hybride` déclarés dans
  `medias.py`) : ajouter un média = une ligne de config. Bonne séparation config/plomberie.
- **La boucle par média en threads** (pipeline v2) : un site lent ne pénalise que lui.
- **Les précautions ops** : verrou `flock` dans lancer.sh, `timeout` en filet, WAL sur
  SQLite, profils Firefox en /dev/shm, collecte sitemaps idempotente (append + dédup).
- **Le suivi** : snapshot périodique, carte de contrôle 3σ, site Evidence. Peu de projets
  de cette taille ont une observabilité pareille.
- **Les tests mockés** (`tests/test_scraping_v2.py`) : le cœur du dispatch et du pipeline
  est couvert sans réseau ni Firefox.

## 3. Axes d'amélioration, par priorité

### P1 — Intégrité du corpus (le risque le plus sérieux)

**a) Le CSV de sortie peut se corrompre ou se dupliquer silencieusement.**
`ecriture_csv` fait un append, puis `maj_bdd` pose etat=2, puis commit. Deux scénarios :
- le processus est tué (pkill -9 de lancer.sh, `timeout -k`) **pendant** l'écriture d'une
  ligne → ligne tronquée au milieu du fichier ;
- il est tué **entre** l'écriture CSV et le commit → l'URL reste etat=0/1, sera re-scrapée,
  et l'article figurera **deux fois** dans le CSV.

Ni l'un ni l'autre n'est détecté aujourd'hui. Proposition simple (pas de refonte) : un
script de contrôle d'intégrité à lancer périodiquement — pour chaque média, comparer
`nb de lignes CSV` vs `nb d'etat=2 en base`, vérifier l'unicité des `id`, vérifier que la
dernière ligne est bien formée. C'est ~40 lignes dans `scraping/suivi.py` (nouvel
indicateur `integrite`), et ça transforme un risque silencieux en alerte visible.

**b) Les dates ne sont pas normalisées à l'écriture.**
Selon le média, la colonne `date` contient de l'ISO (`2026-07-06T08:00:00+02:00`) ou du
texte français (« Publié le 14 mars 2017 », francesoir). Tout l'aval (bases ngram, séries
temporelles) repose sur le groupement par jour : chaque format non parsé = articles
perdus en silence au moment du `groupby date`. Proposition : mesurer d'abord (taux de
dates non parsables par média), puis normaliser — plutôt à la construction des bases
ngram qu'en touchant les CSV (source de vérité, on ne les réécrit pas).

**c) La politique « articles tronqués » n'est appliquée qu'à moitié.**
Pour les médias sans bypass (marianne, midilibre…), la règle actée est de filtrer sur
`free`. Or `free` est vide pour une partie des pages (json-ld incomplet). Avant de
construire les ngram de ces médias, il faut décider : vide = gratuit ou vide = exclu ?
Et vérifier la décision sur échantillon. Sinon le corpus de ces médias mélangera
articles complets et tronqués, ce qui biaiserait les fréquences.

### P2 — Factoriser la tokenisation et les scripts ngram (avant l'extension à 29 médias)

La tokenisation (regex `(?<=[A-Z])\.` + lower + découpe en phrases + `findall`) existe en
**4 copies** : `ngram_lemonde.py`, `ngram_lefigaro.py`, `ngram_lesechos.py`, `api/app.py`
(`tokeniser`). Si une copie diverge un jour, les séries de l'API deviennent fausses sans
aucune erreur visible — le mot cherché ne matche plus les tokens en base. C'est le bug le
plus sournois possible pour un mémoire quantitatif.

Proposition : un module `scripts/tokenisation.py` (une fonction, ~15 lignes) importé
partout, avec un test unitaire qui fige le comportement. Puis fusionner les trois scripts
ngram en un seul paramétré (la seule vraie différence est la lecture du CSV source :
colonnes year/month/day vs date_published — deux petites fonctions de lecture suffisent).
À faire **avant** d'ajouter les ~26 médias restants, sinon ce sera 29 copies.

### P3 — Un peu de CI : lancer les tests à chaque push

La GitHub Action actuelle ne fait que déployer le site. Les tests existent mais rien ne
les lance automatiquement — or le déploiement serveur se fait par `git pull` sur main,
donc une régression poussée part directement en prod. Un workflow de ~15 lignes
(checkout + python + `python -m unittest`) suffit. Optionnel mais rentable : y ajouter
`ruff check` en mode léger.

Complément utile : des **fixtures HTML par média** (une vraie page archivée par média,
tronquée au nécessaire) pour tester les sélecteurs d'extraction. Aujourd'hui, un site qui
change de gabarit ne se voit qu'en prod, via la carte de contrôle. Les fixtures ne
remplacent pas ça (le site peut changer), mais elles protègent contre les régressions
*de notre côté* quand on retouche `extraction.py`.

### P4 — Tracer la cause des échecs

`traiter_url` écrase tout dans etat=1/4 : timeout, 404, page vide, paywall non contourné —
même valeur. Le tri etat=4 → 5 du 11-12/07 a demandé une inspection manuelle média par
média précisément parce que cette information manquait. Proposition : une table `echecs`
(media, url, date, cause) alimentée au moment de l'échec — quelques lignes dans le
pipeline, et les diagnostics futurs se font en SQL au lieu de rejouer des URLs.

Second point du même thème : les deux tentatives (0 → 1 → 4) peuvent être consommées par
un incident **transitoire** (panne réseau du serveur, média en rade une heure). Résultat :
des URLs saines partent en etat=4 définitif. Garde-fou simple : si un média enchaîne N
échecs consécutifs dans un run, suspendre ce média pour le run (ne plus consommer de
tentatives) plutôt que de continuer à griller des URLs.

### P5 — Reproductibilité (c'est un mémoire de recherche)

- `requirements.txt` est tout en `>=` : dans deux ans, impossible de recréer
  l'environnement exact qui a produit le corpus. Un `pip freeze > requirements.lock.txt`
  versionné (serveur et Mac) coûte une commande.
- Documenter dans le README le **flux de données de bout en bout** (sitemaps → CSV d'URLs
  → urls.db → scraping → CSV d'articles → bases ngram → API/fiches), avec pour chaque
  étape le script qui la produit. Tout existe dans le journal mais dispersé sur 800 lignes ;
  le jury (et Corto dans 6 mois) voudra le schéma en une page.

## 4. Petites corrections rapides (quick wins, < 10 min chacune)

- **lancer.sh, commentaires désynchronisés** : l'en-tête dit « s'auto-limite à 2h,
  timeout à 2h30 » et le commentaire du filet dit « le tue à 2h30 », alors que le code
  fait DUREE_MAX=4h et `timeout 270m` (= 4h30). Les valeurs sont bonnes, les commentaires
  mentent — dangereux pour un futur débogage.
- **batch.py, `new_batch`** : le `SELECT media, id, url … GROUP BY media` renvoie un
  (id, url) arbitraire par média (comportement SQLite non standard)… qui n'est jamais
  utilisé — le pipeline ne se sert que des clés. `SELECT DISTINCT media` dirait ce qu'on
  fait vraiment et éliminerait la bizarrerie.
- **pipeline.py** : la ligne morte `# charger_nouvelles_urls(conn)` (et la fonction) sont
  supplantées par `scripts.verser_nouveaux` — à supprimer pour éviter qu'un futur
  lecteur les réactive par erreur.
- **.gitignore** : `identifiants.json` n'est protégé que par la règle générale `*.json`.
  Or ce fichier a déjà des exceptions (`!site/package.json`). Ajouter une ligne explicite
  `identifiants.json` : si un jour quelqu'un ré-autorise les .json pour un besoin de
  config, les identifiants ne partiront pas avec.

## 5. Ce que je ne ferais PAS

- **Ne pas migrer les CSV d'articles vers une base ou du parquet** « parce que c'est plus
  propre » : le CSV-source-de-vérité est acté, tout l'outillage le lit, et le contrôle
  d'intégrité (P1a) couvre le vrai risque. Migration = des jours de travail pour zéro
  gain sur la question de recherche.
- **Ne pas introduire de framework** (scrapy, airflow, docker…) : le couple
  tmux + lancer.sh + cron fait le travail, est compris, et documenté.
- **Ne pas refondre `suivi.py`** (646 lignes) : il est long mais linéaire, chaque
  indicateur est une fonction indépendante. Le découper serait du rangement, pas une
  amélioration.
- **Ne pas viser une couverture de tests exhaustive** : le ratio actuel (cœur du dispatch
  et du pipeline mocké) est le bon pour un projet de recherche ; les fixtures HTML (P3)
  sont le seul ajout à vraie valeur.

## 6. Résumé en une phrase

Le pipeline est en meilleur état que la plupart des projets de recherche que j'ai vus ;
le travail des prochaines semaines doit porter sur la **fiabilité du corpus** (intégrité
CSV, dates, tronqués) et sur la **factorisation ngram/tokenisation** avant le passage de
3 à 29 médias — le reste est du confort.
