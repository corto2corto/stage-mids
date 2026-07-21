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

## equipe-agents-nouveaux-medias — Enrichir la base de médias avec une équipe d'agents (priorité basic)

- Ajoutée : 2026-07-06
- Branche : scraping (scrapping_v2)

**Contexte** : le moteur « basic » (simple requête HTTP, sans navigateur — le moins coûteux et le plus rapide) est acté sur la branche scrapping_v2 et couvre déjà une quinzaine de médias. On veut continuer à enrichir le registre MEDIAS avec de nouveaux médias, en priorisant ceux qui passent en basic. Le processus d'ajout (échantillon d'URLs → HTML → repérage des métadonnées → mapping complet → branchement) est bien rodé mais manuel : on veut le confier à une équipe d'agents qui collaborent.

**Piste envisagée** : orchestrer 4 rôles d'agents par média candidat — mapping (récupère un échantillon d'URLs), scrapper (teste si le HTML en basic est satisfaisant), explorateur (localise les métadonnées dans le HTML), manager (synthétise, tranche ajoutable/écarté, lance le mapping complet et prépare l'entrée medias.py — validation de Corto obligatoire avant tout branchement au pipeline).

**Prompt** :

```
Objectif : enrichir le registre MEDIAS avec de nouveaux médias français, en priorisant ceux qui passent en moteur « basic » (simple requête HTTP, le moins coûteux et le plus rapide). Tout se passe sur la branche scrapping_v2 (scraping/medias.py, scraping/basic.py) — ne pas toucher main, et lire la branche via git show plutôt qu'en switchant le dépôt principal.

Organiser une équipe d'agents (outil Agent), un média candidat à la fois :
1. Agent mapping : trouve la source d'URLs du média (sitemap, archives, pagination — s'inspirer du module mapping/ : generique.py + catalogue.py pour les cas standard, scripts par média pour les cas spéciaux) et en tire un échantillon d'une dizaine d'URLs d'articles variées, gratuits ET payants.
2. Agent scrapper : récupère le HTML de l'échantillon en basic — sur gallica uniquement, jamais de curl/fetch sur le Mac — et juge le contenu : payants complets, gratuits seuls exploitables, ou tronqués.
3. Agent explorateur : fouille les HTML pour localiser titre/auteur/date/corps (stratégie json_ld en priorité, sinon balises — cf exploration/lister_balises.py et exploration/detail_metadonnees.md).
4. Agent manager : croise les trois rapports et tranche : ajoutable en basic complet, ajoutable en gratuits seuls (filtre via la colonne free), ou écarté — règle absolue : jamais d'articles tronqués en base. Si ajoutable : faire écrire le mapping complet (fiche dans mapping/catalogue.py si standard, sinon mapping/<media>.py + passage dans mapping/verifier.py ou verifier_speciaux.py) et préparer l'entrée medias.py pour le branchement au pipeline — SANS brancher : présenter le dossier complet à Corto et attendre sa validation explicite.

Commencer par proposer à Corto une liste de médias candidats (hors MEDIAS actuels de scrapping_v2 et hors écartés : lexpress, lepoint) et la faire valider avant de lancer les agents.
Me demander avant de lancer quoi que ce soit sur le serveur.
```

## extracteur-francesoir — Corriger l'extracteur francesoir (date brute + pied de page promo)

- Ajoutée : 2026-07-11
- Branche : main

**Contexte** : constaté le 11/07/2026 lors du check des CSV — dans `data/csv/francesoir.csv` (435 Mo, sur gallica), le champ date est du texte brut français (« Publié le 30 septembre 2022 - 14:20 ») au lieu de l'ISO utilisé partout ailleurs, et chaque contenu se termine par un bloc promo France-Soir (« …France-Soir est un rendez-vous journalistique incontournable [...] Lire la suite »).

**Piste envisagée** : corriger l'extracteur (date depuis les métadonnées de la page, exclusion du bloc promo du corps), puis one-shot de nettoyage du CSV existant (dates → ISO, troncature du pied de page sur marqueur stable).

**Prompt** :

```
Deux défauts dans data/csv/francesoir.csv (435 Mo, sur gallica), constatés le 11/07/2026 :
1. Le champ date est du texte brut français « Publié le 30 septembre 2022 - 14:20 » au lieu de l'ISO des autres médias. Cause : scraping/medias.py ligne ~63, la date est lue sur le texte affiché (sélecteur div.field--name-field-date.me-3, stratégie balises) ; cf aussi le fallback texte brut dans scraping/extraction.py (~ligne 62).
2. Chaque contenu se termine par un bloc promo du site (« …France-Soir est un rendez-vous journalistique incontournable [...] Lire la suite ») embarqué par le sélecteur de corps div.field--name-body.

À faire, dans l'ordre :
1. Corriger l'extracteur pour les scrapes futurs : prendre la date ISO dans les métadonnées de la page (json-ld ou balise meta — vérifier sur 2-3 HTML réels ce que francesoir expose) et exclure le bloc promo du corps (identifier sa balise/classe dans le HTML pour l'écarter du sélecteur).
2. One-shot de nettoyage du CSV existant : conversion des dates françaises en ISO (motif fixe, mois français → mm ; logguer les lignes qui ne matchent pas au lieu de deviner) + troncature du contenu à la première occurrence d'un marqueur stable du début du bloc promo (vérifier d'abord sur quelques articles où le bloc commence exactement, et compter les occurrences avant de couper). Réécriture via fichier temporaire puis mv, scrapping en pause pendant l'opération.
3. Vérifier sur les 5 derniers articles : date ISO, plus de pied de page, contenu intact.

Me demander avant de lancer quoi que ce soit sur le serveur.
```

## exposer-api-publique — Rendre l'API ngram accessible depuis l'extérieur

- Ajoutée : 2026-07-21
- Branche : main

**Contexte** : le front React de Benoît (statique) pourrait être publié sur GitHub Pages, mais GitHub Pages ne sert que du statique et ne peut pas exécuter l'API Flask ni héberger les bases SQLite. Aujourd'hui l'API (`api/app.py`) n'est joignable que via un tunnel SSH privé (localhost:8501). Pour qu'un front public puisse l'appeler, il faut exposer l'API sur `gallica` derrière une URL publique et stable.

**Piste envisagée** : garder l'API + les bases sur `gallica` (les bases sont trop lourdes pour bouger, ça n'a pas de sens de séparer), et l'exposer publiquement — reverse proxy + HTTPS + éventuellement une authentification, à la place du tunnel SSH. Le front statique appelle alors cette URL publique depuis GitHub Pages.

**Prompt** :

```
Objectif : rendre l'API ngram (api/app.py, Flask) accessible depuis l'extérieur, pour qu'un front statique publié sur GitHub Pages (le front React de Benoît) puisse l'appeler.

Contrainte de fond : GitHub Pages ne sert que du statique — il ne peut ni exécuter Flask ni héberger les bases SQLite ngram. L'API et les bases doivent donc rester sur gallica ; seul le front part sur Pages. Aujourd'hui l'API n'est joignable que via un tunnel SSH privé (localhost:8501), ce qui ne convient pas à un front public.

À faire, dans l'ordre :
1. Regarder comment l'API est lancée et exposée aujourd'hui sur gallica (session tmux, port 8501, tunnel SSH) — cf mémoire API ngram et reference_serveur_ssh.
2. Choisir et décrire l'exposition publique : reverse proxy (nginx ?) devant Flask, HTTPS (nom de domaine ou service type Cloudflare Tunnel), et une authentification si l'API ne doit pas être ouverte à tous. Peser les options avec Corto avant d'installer quoi que ce soit — gallica est un serveur partagé (user ubuntu commun), ne rien toucher de partagé sans accord.
3. Adapter le front (URL de l'API en dur → URL publique) et gérer le CORS côté Flask pour autoriser l'origine GitHub Pages.
4. Vérifier de bout en bout : le front sur Pages interroge l'API publique et affiche les résultats.

Me demander avant de lancer ou d'installer quoi que ce soit sur le serveur.
```

## Faites

## inspection-urls-non-articles — Inspection par média des URLs non-articles + état dédié en base

- Ajoutée : 2026-07-11 · Faite : 2026-07-12
- Branche : main

**Contexte** : l'audit du 11/07/2026 avait repéré ~242 300 URLs non-articles dans `urls.db` (dont `video.lefigaro.fr` ~233 900), mais les filtres par mots-clés créaient des faux positifs massifs dans les slugs — d'où une inspection média par média pour établir des règles fiables (sous-domaine ou segment de chemin, jamais un mot seul).

**Résultat** : inspection des 29 médias terminée le 12/07 — 417 870 URLs marquées etat=5 (état « non-article » documenté dans `stockage.py`, commit e8e471a), règles par média dans `exploration/regles_non_articles.md`. Verdicts « on garde » : slugs à markup span du Télégramme (1,9 M de vrais articles) et pages `video-` de gala/voici. Filtre posé en amont au versement : `est_non_article` dans `collecte.py`, motifs sûrs seulement (commit e49c64f).

## diagnostic-lemonde-pipeline — Diagnostiquer l'échec Le Monde dans le pipeline

- Ajoutée : 2026-07-05 · Faite : 2026-07-12
- Branche : main

**Contexte** : Le Monde échouait à chaque vague du pipeline (motif stable), alors que la plupart des autres médias passaient.

**Résultat** : problème réglé le 11/07 (cf mémoire [[project_le_monde_etat4]]) — faux positif `est_bloque` sur les encarts « Lire aussi », corps repris sur `p.article__paragraph` (commit 5c9b590). Rejeu effectué : 21 082 articles réussis (+1 831), 34 résiduels en etat=4.

## latribune-urls-poubelle — Dédoublonner latribune.csv (URLs Wayback à fragments)

- Ajoutée : 2026-07-11 · Faite : 2026-07-11
- Branche : main

**Contexte** : les URLs Wayback à fragments de latribune (`width=1200`, `format=auto`, `height=675/...jpg`, `&` final, `&quot;`) n'avaient pas été nettoyées avant le chargement dans `urls.db`, et le site les résout vers l'article réel → doublons/triplons dans `latribune.csv` (~13 % du CSV).

**Résultat** (scrapping en pause pendant l'opération, relance à faire) : `latribune.csv` dédoublonné par identifiant d'article (15 899 lignes supprimées, 90 378 articles conservés, zéro identifiant en double — sauvegarde dans `data/backup/latribune_avant_dedup_20260711.csv`) ; 29 228 URLs à fragments passées en etat=4 dans `urls.db` (dont les 14 483 images `height=` qui étaient retentées en boucle) ; 29 228 lignes purgées de `exploration/latribune_url.csv` (111 786 URLs propres restantes).

## charger-urls-nouveaux-medias — Charger les URLs des nouveaux médias dans urls.db (prod)

- Ajoutée : 2026-07-06 · Faite : vérifiée en base le 2026-07-11
- Branche : scrapping_v2 (après merge vers main)

**Contexte** : la v2 configurait 30 médias dans `scraping/medias.py`, mais la base de prod `urls.db` ne contenait que les anciens médias.

**Résultat** : les 13 basic et mediapart sont chargés dans `urls.db` et traités par le pipeline (francesoir, marianne, voici et mediapart déjà entièrement passés au 11/07). `liberation` exclu volontairement (en pause depuis le 07/07, archives tronquées à ~240 mots). Le nettoyage des URLs poubelle de latribune n'avait pas été fait → repris dans la tâche [latribune-urls-poubelle].

## chi2-fit-fiche — Ajouter le chi-deux d'adéquation et sa p-value dans /fiche

- Ajoutée : 2026-07-10 · Faite : 2026-07-11 (commit `40d1ea0`)
- Branche : main

**Contexte** : demande du tuteur (« good practice ») — la route `/fiche` ajuste Poisson (`lam`) et binomiale négative (`mu`, `r`) mais ne renvoyait aucune mesure d'adéquation.

**Solution retenue** : χ² de Pearson **jour par jour** sur les résidus (`Σ (X_t − m_t)²/v_t`), chaque jour comparé à sa propre loi puisque l'exposition `N_t` varie — `m_t = lam*N_t` / `mu*N_t`, variance du modèle (`mu*N_t` Poisson, `mu*N_t + (mu*N_t)²/r` NB), `ddl = jours − params estimés` (1 Poisson, 2 NB), p-value via `chi2.sf`. Exposé sous `"adequation"` dans le JSON de `api/app.py`, affiché dans un tableau du front (`api/index.html`, onglet Fiche : χ², ddl, χ²/ddl, p-valeur, verdict compatible/rejetée).
