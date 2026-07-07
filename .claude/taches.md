# Tâches en attente

Source de vérité de la section « Tâches en attente » du dashboard de suivi.
Une tâche est ajoutée par le skill `/task` (depuis une discussion Claude), et retirée quand elle est faite (elle passe alors dans la section « Faites » en bas). Le prompt de chaque tâche est repris tel quel derrière le bouton « Prompt » du dashboard.

## stopwords-tops — Corriger les stop words résiduels dans les tops

- Ajoutée : 2026-07-05
- Branche : n-grammes

**Contexte** : dans les tops n-grammes (route `/top` de l'API, onglets « Top » et « Avant / après » du front), des mots outils passent encore le filtre : « t il », « nc mpf », et probablement d'autres fragments du même genre.

**Piste envisagée** : compléter `MOTS_OUTILS` dans `scripts/top_ngram.py`, puis mettre à jour le drapeau `stop` dans les 3 bases `*_top.db` existantes par UPDATE ciblé — pas besoin de tout reconstruire.

**Prompt** :

```
Dans les tops n-grammes servis par l'API (route /top, onglets « Top » et « Avant / après » du front), des mots outils passent encore le filtre : « t il », « nc mpf », et probablement d'autres fragments du même genre (élisions et restes de tokenisation).

Le filtre vient de scripts/top_ngram.py : la liste MOTS_OUTILS (ligne ~24) sert à poser stop=1 sur les n-grammes dont tous les mots sont des mots outils ou des nombres (colonne stop de la table top), et l'API filtre là-dessus. Les 3 bases lefigaro_top.db, lesechos_top.db et lemonde_top.db sont déjà construites — on ne veut PAS les reconstruire.

À faire :
1. Repérer les fragments qui passent : regarder les n-grammes stop=0 à fort volume dans les *_top.db pour lister les candidats. Requêtes indexées seulement, pas de scan complet.
2. Compléter MOTS_OUTILS dans scripts/top_ngram.py (pour les futures constructions).
3. Mettre à jour le drapeau stop dans les 3 bases *_top.db existantes par UPDATE ciblé sur la table top, avec la même règle que le script (tous les mots dans la liste ou nombres).
4. Vérifier via l'API (/top) que les tops des 3 journaux sont propres.

Me demander avant de lancer quoi que ce soit sur le serveur.
```

## diagnostic-lemonde-pipeline — Diagnostiquer l'échec Le Monde dans le pipeline

- Ajoutée : 2026-07-05
- Branche : scraping

**Contexte** : Le Monde échoue à chaque vague du pipeline depuis plusieurs cycles (motif stable), alors que la plupart des autres médias passent. Repris de la Feuille de route (branche 1).

**Piste envisagée** : localiser l'étape qui casse — récupération des URLs (sitemap), chargement Firefox, extraction (`json_ld` / `.article__content`), ou détection paywall (bypass qui ne marche plus) — via `urls.db` et les logs, avant de proposer une correction.

**Prompt** :

```
Le Monde échoue à chaque vague du pipeline de scraping depuis plusieurs cycles (motif stable, visible dans les récapitulatifs de vagues de la session tmux scrapping), alors que la plupart des autres médias passent. Objectif : un diagnostic, pas encore la correction.

Configuration actuelle du média (scraping/medias.py, ligne 6) : moteur firefox, stratégie json_ld, corps ".article__content".

Dans l'ordre :
1. Regarder comment les échecs le_monde sont enregistrés dans urls.db sur gallica (statut / message d'erreur) — requêtes indexées + LIMIT seulement, jamais de scan complet.
2. Croiser avec les logs de la session tmux scrapping pour identifier l'étape qui casse : URLs (sitemap), chargement Firefox, extraction (json_ld / .article__content), ou détection paywall (phrases-signal du bypass_checker — le bypass ne marche peut-être plus pour Le Monde).
3. Si nécessaire, capturer UN article Le Monde à la main via navigateur.py sur le serveur et examiner le HTML réellement récupéré.

Livrable : le point exact où ça casse, la cause probable, et la correction proposée — sans la lancer.
Me demander avant de lancer quoi que ce soit sur le serveur.
```

## bases-ngram-13-medias — Construire les bases n-grammes des 13 autres médias

- Ajoutée : 2026-07-05
- Branche : n-grammes

**Contexte** : les 3 bases d'archives (Le Monde, Le Figaro, Les Échos) sont construites ; les 13 autres médias scrapés (CSV dans `data/csv/` sur gallica : Atlantico, Challenges, L'Opinion, La Dépêche, Capital, JDD, Le Nouvel Obs, Le Télégramme, Nice-Matin, Paris Match, Sud Ouest, Télérama, Valeurs actuelles) n'ont pas encore de base n-grammes. Repris de la Feuille de route (branche 2).

**Piste envisagée** : un script générique `scripts/ngram_media.py` calqué sur `scripts/ngram_lesechos.py`, adapté au schéma commun `titre / contenu / date` des CSV, testé sur un petit média avant d'enchaîner les autres.

**Prompt** :

```
Les 3 bases n-grammes d'archives (Le Monde, Le Figaro, Les Échos) sont construites ; il reste à construire celles des 13 autres médias à partir des CSV de data/csv/ sur gallica : Atlantico, Challenges, L'Opinion, La Dépêche, Capital, JDD, Le Nouvel Obs, Le Télégramme, Nice-Matin, Paris Match, Sud Ouest, Télérama, Valeurs actuelles.

Points établis :
- Ces CSV partagent un schéma commun titre / contenu / date, différent des 3 gros CSV d'archives.
- Modèle à imiter : scripts/ngram_lesechos.py (lecture par chunks pandas, tokenisation par phrases, date YYYYMMDD, tables staging puis finales, filtre n > 10, totaux journaliers en base) — mêmes choix de tokenisation, même schéma de base <media>_ngram.db.
- Écrire UN script générique scripts/ngram_media.py qui prend le média en argument (plutôt que 13 copies), en adaptant seulement la lecture du CSV au schéma commun.

Dans l'ordre :
1. Vérifier le schéma réel de 2-3 CSV de data/csv/ (noms de colonnes exacts, format de date) avant d'écrire du code.
2. Écrire le script générique et me le faire relire.
3. Tester sur UN petit média, vérifier la base produite (schéma, index, requêtes indexées seulement), puis enchaîner les 12 autres en série dans une session tmux dédiée.

Me demander avant de lancer quoi que ce soit sur le serveur.
```

## maj-quotidienne-ngram-top — Passer les bases ngram et top en MAJ quotidienne

- Ajoutée : 2026-07-05
- Branche : n-grammes

**Contexte** : les bases `*_ngram.db` et `*_top.db` sont construites en one-shot depuis des CSV figés. Dans le projet final, chaque média reçoit de nouveaux articles chaque jour : il faut une MAJ rapide des deux bases sans reconstruction (le rebuild top prend des heures), avec l'API qui continue de servir pendant l'écriture.

**Piste envisagée** (discutée le 05/07) : rester sur SQLite. MAJ quotidienne append-only des comptes du jour (sans filtre), tops exacts via tables cumulatives « mois courant » / « année courante » (index sur n), gel du top d'une période à sa clôture dans `top.db`. CSV = source de vérité. Filtre `> 10` non tranché : mesurer d'abord l'inflation en rebuidant Les Échos sans filtre.

**Prompt** :

```
Les bases *_ngram.db et *_top.db sur gallica sont construites en one-shot depuis des CSV figés ; il faut les passer en MAJ quotidienne (les CSV vont recevoir chaque jour les nouveaux articles de chaque média), sans reconstruction complète et avec l'API qui continue de servir pendant l'écriture.

Architecture discutée et retenue le 05/07/2026 (rester sur SQLite) :
- Les CSV par média restent la source de vérité ; les bases ngram/top sont des vues dérivées reconstructibles.
- MAJ quotidienne : tokeniser les nouveaux articles (mêmes choix que scripts/ngram_lemonde.py), insérer les comptes du jour dans unigram/bigram/trigram + totaux, en une transaction, SANS appliquer le filtre > 10. PRAGMA en WAL + synchronous=NORMAL (pas les PRAGMA OFF des scripts de build, réservés aux builds hors ligne). Tenir une trace des articles déjà traités pour ne jamais recompter.
- Tops : le top d'une période close ne change plus. Maintenir des tables cumulatives « mois courant » et « année courante » par taille de ngram (ngram -> n cumulé, index sur n) mises à jour par upsert quotidien ; top 500 = lecture d'index, exact. À la clôture d'une période, geler son top dans top.db et vider la table cumulative. Le top du jour se calcule depuis les comptes du jour.
- Filtre global > 10 (posé uniquement pour la taille) : non tranché. Première étape : construire lesechos_ngram sans filtre dans un fichier séparé, comparer les tailles, puis décider avec Corto (sans filtre / filtre trigrams seulement / filtre + rebuild mensuel qui rattrape).
- Si rebuild périodique : construire dans un NOUVEAU fichier puis renommer par-dessus, pour que l'API ne serve jamais une base à moitié construite.

Avant de coder, valider avec Corto le déroulé d'une journée type (ordre des opérations, rattrapage si le scraping d'un jour arrive en retard). Vérification finale : MAJ d'un jour de test en quelques minutes, requêtes API inchangées pendant l'écriture, tops des périodes ouvertes corrects.
Me demander avant de lancer quoi que ce soit sur le serveur.
```

## charger-urls-nouveaux-medias — Charger les URLs des nouveaux médias dans urls.db (prod)

- Ajoutée : 2026-07-06
- Branche : scrapping_v2 (à faire après le merge vers main)

**Contexte** : la v2 configure 30 médias dans `scraping/medias.py`, mais la base de prod `urls.db` ne contient les URLs que des anciens médias. Les 13 nouveaux médias basic (gala, voici, bfmtv, ouest_france, leparisien, la_croix, laprovence, francesoir, marianne, midilibre, paris_normandie, latribune, liberation) et mediapart (log) ont leurs CSV d'URLs sur le serveur mais ne sont pas encore en base : sans ce chargement, le pipeline prod ne les scrape pas. À faire une fois le merge scrapping_v2 → main effectué et la prod repartie.

**Piste envisagée** : réactiver / utiliser `charger_nouvelles_urls()` (déjà écrit dans `scraping/pipeline.py`, actuellement commenté) qui importe les `*_url.csv` non encore en base à etat=0. CSV nouveaux médias dans `exploration/` (colonne `url`), mediapart_url.csv dans `exploration/` aussi. Nettoyer au passage les ~6 % d'URLs poubelle de latribune (fragments Wayback : `width=`, `&` final).

**Prompt** :

```
Charger dans la base de prod urls.db (sur gallica, /data/elias/stage-mids/data/urls.db) les URLs des nouveaux médias configurés dans scraping/medias.py mais encore absents de la base : les 13 basic (gala, voici, bfmtv, ouest_france, leparisien, la_croix, laprovence, francesoir, marianne, midilibre, paris_normandie, latribune, liberation) et mediapart (moteur log). Sans ça, le pipeline prod ne les scrape pas.

Points établis :
- Les CSV d'URLs sont sur le serveur : exploration/<media>_url.csv (colonne url) pour les nouveaux médias, exploration/mediapart_url.csv (~34 000 URLs) pour mediapart.
- La fonction charger_nouvelles_urls() existe déjà dans scraping/pipeline.py (actuellement commentée dans main) : elle importe les *_url.csv non encore en base à etat=0. Vérifier qu'elle pointe le bon dossier de CSV et qu'elle ne recharge pas les médias déjà en base.
- Nettoyer les ~6 % d'URLs poubelle de latribune_url.csv (fragments Wayback : contiennent « width= » ou finissent par « & ») AVANT de charger.
- Ne PAS toucher aux URLs des médias déjà en base (ne pas remettre d'etat à 0).

Dans l'ordre :
1. Vérifier quels médias sont déjà en base (SELECT DISTINCT media, requête indexée) pour ne charger que les manquants.
2. Nettoyer le CSV latribune.
3. Charger les CSV manquants à etat=0, en comptant les lignes ajoutées par média.
4. Vérifier avec suivi.avancement que chaque nouveau média apparaît bien avec le bon nombre d'URLs à traiter.

Me demander avant de lancer quoi que ce soit sur le serveur.
```

## equipe-agents-nouveaux-medias — Enrichir la base de médias avec une équipe d'agents (priorité basic)

- Ajoutée : 2026-07-06
- Branche : scraping (scrapping_v2)

**Contexte** : le moteur « basic » (simple requête HTTP, sans navigateur — le moins coûteux et le plus rapide) est acté sur la branche scrapping_v2 et couvre déjà une quinzaine de médias. On veut continuer à enrichir le registre MEDIAS avec de nouveaux médias, en priorisant ceux qui passent en basic. Le processus d'ajout (échantillon d'URLs → HTML → repérage des métadonnées → mapping complet → branchement) est bien rodé mais manuel : on veut le confier à une équipe d'agents qui collaborent.

**Piste envisagée** : orchestrer 4 rôles d'agents par média candidat — mapping (récupère un échantillon d'URLs), scrapper (teste si le HTML en basic est satisfaisant), explorateur (localise les métadonnées dans le HTML), manager (synthétise, tranche ajoutable/écarté, lance le mapping complet et prépare l'entrée medias.py — validation de Corto obligatoire avant tout branchement au pipeline).

**Prompt** :

```
Objectif : enrichir le registre MEDIAS avec de nouveaux médias français, en priorisant ceux qui passent en moteur « basic » (simple requête HTTP, le moins coûteux et le plus rapide). Tout se passe sur la branche scrapping_v2 (scraping/medias.py, scraping/basic.py) — ne pas toucher main, et lire la branche via git show plutôt qu'en switchant le dépôt principal.

Organiser une équipe d'agents (outil Agent), un média candidat à la fois :
1. Agent mapping : trouve la source d'URLs du média (sitemap, archives, pagination — s'inspirer des exploration/mapping_*.py existants) et en tire un échantillon d'une dizaine d'URLs d'articles variées, gratuits ET payants.
2. Agent scrapper : récupère le HTML de l'échantillon en basic — sur gallica uniquement, jamais de curl/fetch sur le Mac — et juge le contenu : payants complets, gratuits seuls exploitables, ou tronqués.
3. Agent explorateur : fouille les HTML pour localiser titre/auteur/date/corps (stratégie json_ld en priorité, sinon balises — cf exploration/lister_balises.py et exploration/detail_metadonnees.md).
4. Agent manager : croise les trois rapports et tranche : ajoutable en basic complet, ajoutable en gratuits seuls (filtre via la colonne free), ou écarté — règle absolue : jamais d'articles tronqués en base. Si ajoutable : faire écrire le script de mapping complet (exploration/mapping_<media>.py + passage dans exploration/verifier_mappings.py) et préparer l'entrée medias.py pour le branchement au pipeline — SANS brancher : présenter le dossier complet à Corto et attendre sa validation explicite.

Commencer par proposer à Corto une liste de médias candidats (hors MEDIAS actuels de scrapping_v2 et hors écartés : lexpress, lepoint) et la faire valider avant de lancer les agents.
Me demander avant de lancer quoi que ce soit sur le serveur.
```

## Faites

(aucune pour l'instant)
