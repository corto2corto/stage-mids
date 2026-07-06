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

## Faites

(aucune pour l'instant)
