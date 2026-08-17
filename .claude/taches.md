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
4. Agent manager : croise les trois rapports et tranche : ajoutable en basic complet, ajoutable en gratuits seuls (filtre via la colonne free), ou écarté — règle absolue : jamais d'articles tronqués en base. Si ajoutable : faire écrire le mapping complet (fiche dans mapping/catalogue.py — 5 méthodes disponibles — + motif de contrôle dans mapping/verifier.py) et préparer l'entrée medias.py pour le branchement au pipeline — SANS brancher : présenter le dossier complet à Corto et attendre sa validation explicite.

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

## campagne-frequence-minimale — Ajouter la fréquence minimale comme hyperparamètre à part entière de la campagne PCA

- Ajoutée : 2026-08-05
- Branche : main

**Contexte** : `rupture/campagne.py` a déjà un paramètre CLI `--nettoie` (seuil N_t de tokens sous lequel un jour est jugé non fiable et interpolé — le nettoyage V2). Jusqu'ici, il n'a été utilisé qu'avec des valeurs fixes : `5000` sur les grilles journalières, `0` (désactivé) sur les grilles agrégées par blocs (3j/7j, où chaque point agrège déjà plusieurs jours). Dans `campagne_pca/configurations_A_C.qmd`, la colonne « Nettoyage » du tableau comparatif reflète ça : `n5000` ou `—`, un interrupteur binaire plutôt qu'un axe balayé comme média/grille/fenêtre/seuil de surprise/filtre grammatical.

**Piste envisagée** : traiter la fréquence minimale comme un axe de balayage à part entière — tester plusieurs valeurs (ex. 2000, 5000, 10000...) sur les grilles journalières et mesurer l'effet sur K50_frac et le nombre de fenêtres écartées (`n_centres_ecartes` dans la sortie de `campagne.py`). Vérifier aussi si ça vaut la peine de le balayer sur les grilles agrégées (les blocs ont déjà un total de tokens bien plus élevé qu'un jour seul, l'effet du seuil y est peut-être négligeable — à mesurer plutôt qu'à supposer).

**Prompt** :

```
Dans rupture/campagne.py, le paramètre --nettoie (seuil N_t de tokens sous lequel un jour est interpolé, nettoyage V2) existe déjà mais a toujours été utilisé avec une valeur fixe : 5000 sur les grilles journalières, 0 (désactivé) sur les grilles agrégées 3j/7j. Je veux le traiter comme un vrai axe de balayage de la campagne, au même titre que média/grille/fenêtre/seuil de surprise/filtre grammatical, pas comme un interrupteur binaire.

Contexte récent : campagne_pca/configurations_A_C.qmd compare plusieurs configurations (Le Monde, Le Figaro, Les Échos, Mediapart) avec une colonne "Nettoyage" qui vaut n5000 ou "—" selon la grille — ça montre bien que ce paramètre est traité à part, pas balayé.

À faire :
1. Sur les grilles journalières (lemonde, lesechos, mediapart), balayer --nettoie sur plusieurs valeurs (par exemple 2000, 5000, 10000, et éventuellement 0 pour comparer à l'absence de nettoyage) à demi/seuil fixés sur une config déjà connue (ex. reprendre les configs D/F de configurations_A_C.qmd), et mesurer l'effet sur K50_frac et sur le nombre de fenêtres réellement conservées (n_fenetres, n_centres_ecartes dans la sortie du runner).
2. Sur au moins une grille agrégée (3j ou 7j), vérifier si le seuil a un effet mesurable une fois qu'un point agrège déjà plusieurs jours de tokens (hypothèse à date : négligeable, mais à vérifier plutôt qu'à supposer) plutôt que de le laisser désactivé par défaut.
3. Présenter les résultats sous forme de tableau comparatif (comme les autres balayages de la campagne), avant de décider s'il faut l'intégrer aux configurations déjà retenues (A/C/D/F...) ou en proposer de nouvelles.

Pas de calcul sur le serveur sans me demander avant si ça implique de rapatrier de nouvelles données ou de lancer quoi que ce soit de long.
```

## cooccurrence-mots-archetypes — Afficher les mots associés au mot cible sur les graphes d'archétypes (idée Benoît)

- Ajoutée : 2026-08-05
- Branche : main

**Contexte** : suggestion de Benoît — une fois qu'on a un pic (mot cible détecté comme saut), chercher quels mots l'accompagnent le plus souvent pour aider à interpréter les archétypes des graphes PCA. Exemple donné : sur Le Figaro, l'archétype « zone » a mis longtemps à être compris avant de réaliser qu'il s'agissait en fait de « zone euro » — l'info était dans le texte mais invisible sur le graphe.

**Piste envisagée** : la version que Benoît préfère lui-même (« ça augmenterait de fou l'intelligibilité ») — sur chaque graphe d'archétype, afficher systématiquement les 4 mots qui apparaissent le plus souvent avec le mot cible, plutôt que la variante à seuil conditionnel (afficher seulement si >80 % des occurrences sont suivies du même syntagme). Nécessite de revenir au texte brut des articles (colonne `contenu` des CSV par média) pour calculer la co-occurrence autour de chaque pic — les matrices `vocab_series_*` déjà agrégées, utilisées dans `figures_config.py`/`figures_optimale.py`, ne suffisent pas. Idée neuve, pas encore explorée : pas de fichier ni de méthode de calcul déjà arrêtés.

**Prompt** :

```
Benoît a proposé une amélioration des graphes d'archétypes de la PCA (voir figures_config.py et figures_optimale.py, panneau "archétypes" : les 3 fenêtres réelles les plus alignées par composante) : afficher, sur chaque sous-graphe d'archétype, les mots qui accompagnent le plus souvent le mot cible autour de son pic. Exemple qui a motivé la demande : sur Le Figaro, l'archétype "zone" a été incompréhensible jusqu'à réaliser que c'était en fait "zone euro" — l'info était dans le texte de l'article mais invisible sur le graphe (qui ne montre qu'une courbe de fréquence).

Version retenue par Benoît (plus simple qu'une règle à seuil) : sur chaque sous-graphe d'archétype, afficher systématiquement les 4 mots qui co-occurrent le plus souvent avec le mot cible dans la fenêtre du pic.

Point important : les scripts de figures actuels (figures_config.py, figures_optimale.py) ne travaillent que sur les matrices vocab_series_<media>.npz déjà agrégées (comptes mot x jour) — pas de texte brut, donc pas de notion de "mots voisins dans le même article". Pour calculer une vraie co-occurrence, il faudra remonter aux CSV sources par média (data/csv/<media>.csv, colonne contenu) et, pour chaque pic archétype affiché, regarder les articles publiés dans sa fenêtre temporelle (ou contenant le mot cible) et compter les mots qui y apparaissent le plus souvent à ses côtés.

À faire, dans l'ordre :
1. Définir précisément ce qu'est "un mot qui accompagne" : co-occurrence dans le même article, ou dans les articles du même jour/bloc que le pic ? Trancher avec Corto avant de coder — ça change le calcul.
2. Prototyper le calcul de co-occurrence sur UN mot cible connu (ex. "zone" sur Le Figaro) pour vérifier qu'on retrouve bien "euro" en tête, avant de généraliser.
3. Intégrer l'affichage (4 mots en légende ou annotation sous chaque sous-graphe d'archétype) dans figures_config.py, en gardant le script lisible — pas de couplage fort avec le calcul de co-occurrence si ça peut rester une fonction séparée.
4. Vérifier le rendu sur une des configurations déjà produites (campagne_pca/configurations_A_C.qmd) avant de régénérer toutes les figures existantes.

Pas de piste de fichier ni de méthode déjà validée — c'est une idée neuve à explorer, pas un bug diagnostiqué. Me proposer une approche avant de coder.
```

## critere-frequence-archetypes — Ajouter un critère de fréquence minimale pour la sélection des archétypes

- Ajoutée : 2026-08-05
- Branche : main

**Contexte** : dans `figures_config.py` et `figures_optimale.py`, les archétypes affichés pour chaque composante sont choisis uniquement sur la valeur de projection (`np.argsort(proj[:, k])[-3:][::-1]` — les 3 fenêtres les plus « pures »/alignées sur la composante), sans aucun critère de fréquence du mot. Constaté (échange avec Benoît) : « pas hyper parlant tout ça » — un mot très rare (ex. « nettoyage », maximum de l'ordre de 100 occurrences) peut dominer un archétype juste parce que sa projection est extrême, alors que le z-score par fenêtre n'efface que l'échelle absolue, pas le bruit d'échantillonnage sur des comptages journaliers minuscules (0, 1, 2 occurrences → sauts relatifs énormes par hasard).

**Piste envisagée** : ajouter un plancher de fréquence en amont de la sélection des 3-4 meilleures fenêtres par composante, pour écarter les mots trop rares du choix des archétypes — reste à trancher la mesure exacte (fréquence max sur la fenêtre, total d'occurrences sur tout le corpus, ou occurrences au jour du pic) et la valeur du seuil. Documenter aussi, en commentaire ou dans le doc, comment les archétypes sont choisis aujourd'hui (mécanisme peu clair en l'état, d'où la confusion).

**Prompt** :

```
Aujourd'hui, dans figures_config.py et figures_optimale.py (panneau "archétypes"), les 3 (ou 4) fenêtres affichées par composante sont choisies uniquement par np.argsort(proj[:, k])[-3:][::-1] — les projections les plus fortes sur la composante k, sans aucun critère de fréquence du mot. Problème constaté (échange avec Benoît) : des mots très rares (ex. "nettoyage", ~100 occurrences max) peuvent dominer un archétype juste parce que leur z-score par fenêtre est bruité (comptages journaliers minuscules → sauts relatifs énormes par hasard), pas parce que la forme est un vrai motif éditorial représentatif.

À faire :
1. Écrire dans le script (commentaire clair, ou dans campagne_pca/configurations_A_C.qmd / rapport.qmd) une explication courte du mécanisme actuel de sélection des archétypes, pour que ce soit clair pour qui relit le code.
2. Ajouter un critère de fréquence minimale avant la sélection des archétypes : décider avec Corto de la mesure (fréquence max atteinte dans la fenêtre, total d'occurrences du mot dans tout le corpus, ou N_t au jour du pic) et du seuil (proposer une valeur en regardant la distribution réelle des fréquences des mots actuellement sélectionnés comme archétypes, pas une valeur arbitraire).
3. Comparer les archétypes avant/après sur une configuration déjà connue (ex. config D ou F de configurations_A_C.qmd) pour vérifier que le nouveau critère écarte bien les cas bruités type "nettoyage" sans perdre les archétypes réellement parlants (type "jaunes", "fermées"/"distance" pour le confinement).

Proposer l'approche à Corto avant de coder le critère de fréquence (le seuil exact n'est pas encore tranché).
```

## jours-semaine-stopwords — Ajouter les jours de la semaine aux mots outils du vocabulaire

- Ajoutée : 2026-08-06
- Branche : main

**Contexte** : les sept jours de la semaine (`lundi` … `dimanche`) passent le filtre des mots outils et occupent le haut du vocabulaire de tous les médias, Mediapart en tête (`mercredi` rang 133, `samedi` 185, puis jeudi/lundi/mardi/vendredi/dimanche entre les rangs 519 et 730 de `vocab_mediapart_top10000.csv`). Ce sont des marqueurs de calendrier, pas du contenu éditorial : leur série temporelle porte surtout une périodicité hebdomadaire de publication, qui pollue la PCA sans rien dire du sujet traité. `pics_mediapart_s3.csv` contient déjà 191 pics portés par ces mots. Deux filtres existent et les laissent passer : `MOTS_OUTILS` dans `scripts/tokenisation.py` (ligne 10, appliqué dans `rupture/masse.py:37`) ne les liste pas, et le filtre grammatical les classe `nom` dans `campagne_pca/vocab_categories.csv` — donc conservés.

**Piste envisagée** : ajouter les sept jours à `MOTS_OUTILS`, ce qui les exclut à la construction du vocabulaire. Les fichiers `vocab_*_top10000.csv` et `vocab_series_*.npz` déjà produits n'étant pas régénérables sans repasser `rupture/masse.py` sur gallica, prévoir un filtrage en aval côté campagne pour les données locales déjà en place, plutôt qu'une reconstruction. À vérifier aussi : le problème vaut pour les quatre médias (Le Monde, Le Figaro, Les Échos, Mediapart), pas seulement Mediapart.

**Prompt** :

```
Les sept jours de la semaine (lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche) polluent le vocabulaire des campagnes PCA : ce sont des marqueurs de calendrier, pas du contenu éditorial, et leur série porte surtout la périodicité hebdomadaire de publication du média.

Constat (06/08/2026), le plus marqué sur Mediapart : dans campagne_pca/data_local/vocab_mediapart_top10000.csv, « mercredi » est au rang 133 et « samedi » au 185, les cinq autres entre les rangs 519 et 730. Et campagne_pca/data_local/pics_mediapart_s3.csv contient 191 pics portés par ces mots. Le problème existe aussi sur lemonde, lefigaro et lesechos (les sept jours sont dans leurs top-10000) — à traiter pour les quatre, pas seulement Mediapart.

Pourquoi ils passent : les deux filtres existants les laissent tous les deux passer.
- scripts/tokenisation.py, liste MOTS_OUTILS (ligne 10), appliquée dans rupture/masse.py ligne 37 (v = v[~v["mot"].isin(set(MOTS_OUTILS))]) : les jours n'y sont pas.
- Le filtre grammatical : campagne_pca/vocab_categories.csv les classe « nom » (source lexique), donc conservés.

À faire :
1. Ajouter les sept jours à MOTS_OUTILS dans scripts/tokenisation.py. Vérifier avant de le faire que cette liste ne sert pas ailleurs à quelque chose qui casserait (elle est aussi utilisée côté tops n-grammes) — si l'exclusion ne doit pas être globale, prévoir plutôt une liste d'exclusion propre à la campagne PCA.
2. Pour les données locales déjà produites (campagne_pca/data_local/vocab_*_top10000.csv et les vocab_series_*.npz) : ne PAS reconstruire via rupture/masse.py sur gallica. Filtrer en aval, côté campagne, en écartant les colonnes correspondantes.
3. Rejouer une configuration déjà connue (config D ou F de campagne_pca/configurations_A_C.qmd) avant/après pour mesurer ce que le retrait change : K50_frac, et surtout les archétypes — vérifier si des archétypes actuels étaient portés par un jour de la semaine.
4. Regarder au passage s'il y a d'autres marqueurs de calendrier du même genre à traiter en même temps (mois : janvier, février... ; « hier », « aujourd'hui », « demain») et me proposer la liste avant de l'ajouter.

Me demander avant de lancer quoi que ce soit sur le serveur.
```

## saisonnalite-modele-nb — Introduire une saisonnalité dans les paramètres de la loi NB (lambda_t)

- Ajoutée : 2026-08-06
- Branche : main

**Contexte** : les χ² d'adéquation (`rupture/pics.py`, fonction `adequation`, exposée dans `/fiche` de `api/app.py`) sont mauvais même pour NB et BNB, pas seulement Poisson — le modèle actuel ajuste un paramètre constant dans le temps (`lam` pour Poisson, `mu`/`r` pour NB, `p0`/`mu_b`/`r_b` pour BNB, cf `ajuster()` ligne 54), normalisé seulement par l'exposition `N_t`. Une saisonnalité (hebdomadaire notamment, cf tâche [[jours-semaine-stopwords]] sur la périodicité de publication) n'est pas capturée par un paramètre constant, ce qui peut expliquer le mauvais ajustement.

**Piste envisagée** : faire évoluer le paramètre de la loi dans le temps plutôt que de le garder constant — fitter une Poisson (ou NB) de paramètre `lambda_t` avec `t` qui évolue doucement (lissage/tendance lente, pas un saut jour à jour), au lieu d'un `lam`/`mu` unique sur toute la période.

**Prompt** :

```
Les χ² d'adéquation du modèle probabiliste sont mauvais, y compris pour NB et BNB (pas seulement Poisson) — constaté via la route /fiche de api/app.py, qui affiche chi2/ddl/p-valeur pour les trois lois (ajoutés en 07/2026, cf tâche faite chi2-fit-fiche).

Le cœur du modèle est dans rupture/pics.py :
- ajuster() (ligne 54) fit un paramètre CONSTANT sur toute la période : lam pour poisson, mu/r pour nb, p0/mu_b/r_b pour bnb — normalisé seulement par l'exposition N_t (le volume de tokens du jour).
- adequation() (ligne 90) calcule le χ² de Pearson jour par jour à partir de ce paramètre constant.
- densite() (ligne 103) et pvaleurs() (ligne 40) utilisent aussi ce paramètre constant.

Objectif : introduire une saisonnalité dans le paramètre de la loi plutôt que de le garder constant — fitter un lambda_t (ou mu_t) qui évolue doucement dans le temps (tendance lente / lissage), pas un saut jour à jour. Exemple de départ : Poisson de paramètre lambda_t, X_t ~ P(lambda_t * N_t), avec lambda_t obtenu par un lissage (à définir : moyenne mobile, spline, GAM, ou modèle à effet saisonnier hebdomadaire + tendance lente — comparer plusieurs options avant de trancher).

À faire, dans l'ordre :
1. Vérifier d'abord l'hypothèse : sur un mot et un média connus (reprendre un cas déjà étudié dans une fiche existante), regarder si les résidus de Pearson (z dans adequation()) montrent un motif temporel (cycle hebdomadaire, dérive lente) plutôt que du bruit pur — ça confirme que la saisonnalité est bien le problème avant de recoder le fit.
2. Proposer à Corto 2-3 approches pour faire évoluer lambda_t dans le temps (lissage non paramétrique type moyenne mobile/spline, ou modèle paramétrique avec effet jour-de-semaine + tendance), avec les avantages/inconvénients de chacune (nombre de paramètres, risque de sur-ajustement, ddl restants pour le χ²), avant de coder.
3. Adapter ajuster()/pvaleurs()/adequation()/densite() dans rupture/pics.py pour un paramètre variable dans le temps — attention à K_PARAMS et ddl (le nombre de degrés de liberté du χ² doit refléter le nombre réel de paramètres estimés, potentiellement bien plus élevé qu'avec un paramètre constant).
4. Comparer les χ²/ddl avant/après sur plusieurs mots et médias déjà utilisés dans des fiches existantes, vérifier que l'ajustement s'améliore réellement et que /fiche (api/app.py) continue de fonctionner.

Pas de calcul long sur le serveur sans me demander avant.
```

## quantile-residuals-pca — Remplacer la normalisation z-score par des résidus quantiles (Dunn-Smyth) avant la PCA

- Ajoutée : 2026-08-06
- Branche : main

**Contexte** : idée de Benoît (échange du 31/07/2026) — la PCA (`rupture/pca.py`) travaille aujourd'hui sur des fenêtres normalisées par z-score le long de la fenêtre (`normaliser()`, ligne 44, option `"z"` par défaut), ou en variante minmax (`"01"`)/standardisation colonne (`"col"`, témoin). Ce sont des normalisations arbitraires (échelle et méthode choisies à la main). Benoît propose les résidus quantiles (Dunn-Smyth, quantile residuals) : une transformation qui, à partir d'un modèle statistique de la donnée (ici Poisson/NB/BNB déjà ajustés mot par mot dans `rupture/pics.py`), rend les résidus gaussiens — plus élégant et sans échelle arbitraire, à condition d'avoir un modèle stat derrière (qu'on a déjà).

**Piste envisagée** : calculer les résidus quantiles à partir des lois déjà ajustées (`ajuster()`/`pvaleurs()` dans `rupture/pics.py`, fonction de répartition inverse d'une gaussienne appliquée à la p-valeur PIT), et faire la PCA sur ces résidus plutôt que sur les fenêtres z-scorées — comparer aux 3 normalisations déjà en place (`z`/`01`/`col`) sur au moins une configuration connue avant de basculer.

**Prompt** :

```
Idée de Benoît (échange du 31/07/2026, capture d'écran + vocal) : remplacer la normalisation actuelle des fenêtres avant la PCA par des résidus quantiles (Dunn-Smyth / quantile residuals), plutôt que le z-score ou le minmax.

Contexte technique existant :
- rupture/pca.py, fonction normaliser() (ligne 44) : normalise chaque fenêtre en z-score ("z", option par défaut), minmax ("01"), ou standardisation colonne ("col", témoin réservé à la remarque de Benoît, pas une normalisation candidate).
- rupture/pics.py : ajuster() (ligne 54) fit déjà une loi de comptage (Poisson/NB/BNB) par mot, normalisée par l'exposition N_t ; pvaleurs() (ligne 40) calcule p_t = P(X >= X_t) sous la loi ajustée.

Principe des résidus quantiles (Dunn-Smyth) : pour une donnée discrète X_t avec un modèle stat ajusté, calculer la valeur de la fonction de répartition (PIT, en gérant l'aléatorisation pour les distributions discrètes — tirer uniformément entre F(X_t - 1) et F(X_t)), puis appliquer l'inverse de la fonction de répartition d'une gaussienne standard. Le résultat est gaussien si le modèle est correct, sans notion d'échelle arbitraire (contrairement au z-score sur une fenêtre ou au minmax) — commencer par lire une référence claire sur le calcul exact (l'article original de Dunn & Smyth 1996 est aride, préférer une source pédagogique récente ou vulgarisée) avant de coder.

À faire, dans l'ordre :
1. Étudier la méthode exacte de calcul des résidus quantiles aléatorisés pour des lois discrètes (Poisson, NB), et comment gérer le cas BNB (mélange avec masse en 0).
2. Prototyper le calcul sur UN mot déjà bien caractérisé (reprendre un cas connu d'une fiche existante), en réutilisant les lois déjà ajustées par rupture/pics.py — vérifier visuellement (QQ-plot) que les résidus obtenus sont bien approximativement gaussiens quand le modèle est bon.
3. Adapter rupture/pca.py pour ajouter une 4e option de normalisation (résidus quantiles) dans normaliser(), en gardant les 3 existantes pour comparaison.
4. Comparer la PCA obtenue (variance expliquée, composantes, archétypes) entre résidus quantiles et z-score sur une configuration déjà connue (campagne_pca/configurations_A_C.qmd), avant de basculer les configurations retenues.

Pas de calcul long sur le serveur sans me demander avant.
```

## resolution-detection-vs-classification — Séparer la résolution de détection des pics de celle de classification des fenêtres

- Ajoutée : 2026-08-06
- Branche : main

**Contexte** : échange avec Benoît (31/07/2026) sur la comparaison des configurations de `configurations_A_C.qmd` — remarque de Corto que les configs comparées n'ont pas le même taux de surprise/fenêtre, donc pas directement comparables. Benoît fait remarquer que c'est en partie une question de zoom : en résolution mensuelle, « covid » est un pic évident, alors qu'à résolution journalière il peut se diluer. Aujourd'hui, `rupture/campagne.py` utilise UNE seule largeur de fenêtre (`--demi`, portée `2*demi+1`) à la fois pour repérer les pics (seuil de surprise) et pour découper les fenêtres données à la PCA. Benoît propose de séparer les deux : détecter un pic à une résolution plus large (ex. mois anormal, critère généreux), mais ensuite classifier la forme de la série avec des fenêtres plus fines (ex. 3 jours) — l'idée sous-jacente étant que si le mois englobant n'est pas anormal, ce n'est probablement pas un vrai événement.

**Piste envisagée** : introduire deux paramètres de résolution distincts dans la chaîne pics → NMS → fenêtres → PCA : une résolution grossière pour la détection (marquer les mois/blocs anormaux), une résolution fine pour la fenêtre classifiée (ex. 3 jours autour du pic déjà détecté). À définir avec Corto : le critère exact du « mois anormal » (agrégation de la surprise ? nouveau test sur les comptes mensuels ?) et comment articuler les deux échelles sans dupliquer toute la chaîne.

**Prompt** :

```
Idée de Benoît (échange du 31/07/2026, à la suite d'une remarque sur configurations_A_C.qmd où les configs comparées n'avaient pas le même taux de surprise/fenêtre) : séparer la résolution utilisée pour DÉTECTER un pic de celle utilisée pour CLASSIFIER la forme de la série autour de ce pic.

Constat de Benoît : la détection de pic dépend beaucoup du zoom temporel — en résolution mensuelle, "covid" est un pic écrasant, ce qui peut se diluer en résolution journalière. Proposition : détecter d'abord à une résolution large (ex. un MOIS anormal, avec un critère éventuellement plus généreux qu'aujourd'hui), puis, seulement pour les pics ainsi validés, classifier la time series avec des fenêtres fines (ex. 3 jours) comme aujourd'hui. Intuition de Corto, à vérifier : si le mois englobant n'est pas anormal, le "pic" journalier n'est probablement pas un vrai événement — plutôt du bruit d'échantillonnage.

État actuel de la chaîne, dans rupture/campagne.py : les pics viennent de pics_<media>.csv (déjà détectés en amont, cf rupture/pics.py, à résolution journalière), filtrés par surprise >= --seuil, puis NMS (rupture/nms.py, portée 2*--demi+1) et découpés en fenêtres +/-  --demi pour la PCA (rupture/pca.py). Une seule résolution (--demi) sert donc aux deux usages : espacement des pics ET largeur de la fenêtre classifiée.

À faire, dans l'ordre :
1. Discuter avec Corto le critère exact du "mois anormal" : sur quelle grille agréger (mensuelle stricte, ou fenêtre glissante plus large que le --demi actuel), avec quel test (réutiliser le test de surprise déjà en place sur des comptes agrégés, ou un nouveau critère) et quel seuil ("éventuellement plus généreux" reste à quantifier).
2. Proposer une architecture à deux résolutions dans la chaîne pics → NMS → fenêtres → PCA, en réutilisant au maximum le code existant (rupture/pics.py, rupture/nms.py, rupture/campagne.py, rupture/pca.py) plutôt que de dupliquer la chaîne.
3. Prototyper sur UN média déjà connu (comparer avec une config existante de configurations_A_C.qmd) : combien de pics journaliers survivent au filtre "mois anormal", et si les archétypes obtenus sont plus propres/interprétables.
4. Si concluant, comparer proprement dans un tableau (comme les autres balayages de la campagne) avant de proposer une nouvelle configuration retenue.

Pas de calcul long sur le serveur sans me demander avant.
```

## orientation-composantes-pca — Fixer le signe des composantes (archétypes discordants avec le texte)

- Ajoutée : 2026-08-11
- Branche : main

**Contexte** : le cache PCA reconstruit le 11/08 (`campagne_pca/data/cache_pca/*.npz`) rend, pour la composante 3 d'`optimale`, des archétypes différents de ceux commentés dans `campagne_pca/rapport_qmd/configuration_optimale.qmd`. Le rapport parle de « fermées » et « distance » au 20/03/2020 (le confinement, un changement de niveau durable) ; la figure régénérée montre « lionel », « second », « chaleur ». Vérifié : « fermées »/« distance » sont les extrêmes NÉGATIFS de la composante — le signe du vecteur propre est simplement inversé par rapport au calcul d'origine. La SVD ne détermine pas l'orientation des vecteurs propres, et rien dans la chaîne ne la fixe : deux calculs de la même configuration peuvent donc donner des composantes opposées. Le calcul est identique, seule la lecture s'inverse (« avant → après » devient « après → avant »). Le filtre de volume n'est pas en cause (`vol_q=0, vol_min=0` pour `optimale` dans `scripts/configs.py`, vérifié : seuil 0, 8 764 fenêtres éligibles sur 8 764).

**Piste envisagée** : trois options, à trancher avec Corto — laisser tel quel (texte et figure discordants), adapter le texte du rapport aux nouveaux archétypes, ou fixer une convention de signe dans `figures_lib.charger()`. La troisième est la seule durable, mais c'est une modification des résultats : elle demande une validation explicite. Une convention naïve « bloc central positif » ne suffit pas — elle ne veut rien dire pour les composantes sans pic au centre (comp. 2 = montée puis chute), où elle a produit d'autres archétypes que ceux du rapport.

**Prompt** :

```
Les composantes de la PCA n'ont pas d'orientation fixée : la SVD ne détermine pas le signe des vecteurs propres, et rien dans campagne_pca/scripts/figures_lib.py (charger(), qui appelle rupture.pca.pca) ne le contraint. Conséquence constatée le 11/08 : le cache PCA reconstruit (campagne_pca/data/cache_pca/optimale.npz) donne pour la composante 3 les archétypes « lionel », « second », « chaleur », alors que campagne_pca/rapport_qmd/configuration_optimale.qmd commente « fermées » et « distance » au 20/03/2020 — le confinement. Vérifié : ces deux-là sont les extrêmes NÉGATIFS de la composante ; le signe est inversé par rapport au calcul qui avait servi aux figures d'origine. Le calcul est le même, seule la lecture s'inverse.

Le filtre de volume n'est PAS en cause : optimale a vol_q=0 et vol_min=0 dans campagne_pca/scripts/configs.py, et filtre_volume rend bien seuil 0 / 8 764 éligibles sur 8 764. (La question du filtre de fréquence est suivie à part, voir la tâche critere-frequence-archetypes.)

À faire :
1. Me présenter les trois options avant de coder : (a) laisser tel quel, (b) adapter le texte du rapport aux archétypes actuels, (c) fixer une convention de signe dans charger(). Recommander, mais me laisser trancher — (c) modifie les résultats affichés.
2. Si (c) est retenue : attention, une convention « coefficient du bloc central positif » ne marche pas. Testée le 11/08, elle rétablit bien les comp. 1, 3 et 4 d'optimale, mais change la comp. 2 (montée progressive puis chute, sans pic au centre) : on obtient « timbre », « orient », « golfe » au lieu de « organisé », « régionales », « ordonnance ». Chercher une convention qui vaille pour toutes les formes, et la vérifier composante par composante contre les figures d'origine.
3. Les figures d'origine sont récupérables dans l'historique git (commit 3a00f79, campagne_pca/rapport_qmd/figures/optimale_*.png) — s'en servir comme référence de comparaison.
4. Si la convention change les caches, ne pas les reconstruire sur le serveur sans me demander : l'orientation peut être appliquée à la lecture dans depuis_cache().

Vérifier à la fin en recompilant campagne_pca/rapport_qmd/configuration_optimale.qmd et en comparant les 4 panneaux d'archétypes aux figures du commit 3a00f79.
```

## auteur-ouest-france — Renseigner la colonne auteur du CSV Ouest-France

- Ajoutée : 2026-08-12
- Branche : main

**Contexte** : la récolte Ouest-France passe par l'API Algolia (index `articles_bydate_desc`, cf. `ouest_france/algolia.md`), qui donne `id`, `url`, `titre`, `date`, `section`, `free` et surtout le texte intégral — y compris pour les articles payants, donc sans scraping ni bypass. Seule la colonne `auteur` de `scraping/stockage.py:26` reste vide : l'index n'a aucun champ auteur. Vérifié sur 500 articles : `producteurs` et `proprietaires` ne comptent que 9 et 3 UUID distincts, ce sont des services de rédaction, pas des journalistes. Décision prise le 12/08 : ne pas bloquer la récolte pour ça, traiter l'auteur en second temps.

**Piste envisagée** : script séparé, lancé après la récolte, qui ouvre le HTML de chaque URL et lit l'auteur dans le JSON-LD (champ `author`, exactement comme `meta_json_ld()` dans `scraping/extraction.py`), puis met à jour la seule colonne `auteur` du CSV existant. Coût à mesurer d'abord sur un échantillon : c'est une requête HTTP par article, sur un corpus qui se compte en millions — un sous-ensemble (années ou zones utiles au mémoire) sera sans doute plus raisonnable que la totalité.

**Prompt** :

```
Le CSV Ouest-France est produit par la récolte Algolia (voir ouest_france/algolia.md et le script de récolte ouest_france/recolte.py). Toutes les colonnes de scraping/stockage.py:26 sont remplies sauf « auteur » : l'index Algolia n'a aucun champ auteur (vérifié sur 500 articles — producteurs/proprietaires ne sont que 9 et 3 UUID de services de rédaction, pas des journalistes).

À faire : un script séparé qui enrichit a posteriori la colonne auteur du CSV, sans retoucher les autres colonnes.

1. Prendre un échantillon d'une trentaine d'URLs du CSV et vérifier que l'auteur est bien dans le JSON-LD de la page (champ author) — la logique de meta_json_ld() dans scraping/extraction.py est directement réutilisable. Vérifier aussi sur des articles payants : si le JSON-LD n'est servi qu'aux abonnés, la piste tombe et il faut me le dire avant d'aller plus loin.
2. Mesurer sur cet échantillon le temps par article, et m'en donner l'extrapolation sur le corpus complet avant toute récolte en masse.
3. Écrire le script : lecture du CSV, requête par URL, mise à jour de la seule colonne auteur, reprise possible après interruption (ne pas refaire les lignes déjà renseignées), écriture progressive.
4. Me proposer le périmètre (toutes les lignes ou un sous-ensemble par années/zones) plutôt que de lancer sur la totalité.

Vérifier à la fin sur une centaine de lignes que l'auteur est cohérent avec ce qu'affiche la page, et que les autres colonnes sont inchangées.

Me demander avant de lancer quoi que ce soit sur le serveur.
```

## nms-suffixe-seuil — Découpler nms.py du seuil de surprise par défaut

- Ajoutée : 2026-08-17
- Branche : main

**Contexte** : `rupture/pics_masse.py` accepte un 4e argument (surprise minimale, défaut 4 = p < 1e-4) et écrit alors dans `pics_<media>_s<x>.csv` pour ne pas écraser les sorties livrées. `rupture/campagne.py` sait relire ces fichiers via `--pics _s3`, mais `rupture/nms.py` non : il lit `pics_<media>.csv` en dur (ligne 58) et sa constante `HAUTEUR = 4.0` (ligne 31) est écrite en dur avec le commentaire « = -log10(SEUIL de pics.py) ». Résultat : si on relance une campagne à un autre seuil, le NMS traite silencieusement l'ancien fichier au seuil 4 au lieu du nouveau. Rien n'est cassé aujourd'hui (tout tourne au défaut), c'est une désynchronisation qui n'apparaîtra qu'au moment où on fera varier le seuil.

**Piste envisagée** : donner à `nms.py` le même argument de suffixe que `campagne.py` (`--pics _s3`), l'appliquer au fichier lu et aux deux fichiers écrits, et déduire `HAUTEUR` du suffixe plutôt que de la coder en dur — c'est exactement `surprise_min`, la valeur passée à `pics_masse.py`.

**Prompt** :

```
Dans la chaîne de détection de pics, rupture/nms.py est couplé en dur au seuil de surprise par défaut, alors que les deux autres maillons sont paramétrables.

Constat :
- rupture/pics_masse.py prend un 4e argument « surprise » (défaut 4, soit p < 1e-4) et, s'il diffère de 4, suffixe ses sorties en pics_<media>_s<x>.csv.
- rupture/campagne.py sait relire ces fichiers via --pics _s3.
- rupture/nms.py, lui, lit pics_<media>.csv en dur (ligne 58), écrit pics_<media>_nms.csv et pics_<media>_nms_ecarts.txt sans suffixe, et sa constante HAUTEUR = 4.0 (ligne 31) est codée en dur alors qu'elle vaut -log10(seuil).

Conséquence : relancer une campagne à un autre seuil fait travailler le NMS sur l'ancien fichier au seuil 4, sans erreur ni avertissement.

À faire :
1. Ajouter à nms.py un argument optionnel de suffixe, sur le même modèle que --pics de campagne.py (garder la compatibilité : sans argument, comportement actuel inchangé).
2. Appliquer le suffixe au fichier lu ET aux deux fichiers écrits.
3. Déduire HAUTEUR du suffixe au lieu de la coder en dur (c'est la valeur « surprise » passée à pics_masse.py) ; garder 4.0 par défaut.
4. Vérifier que la contre-vérification find_peaks utilise bien la hauteur déduite, pas 4.0.

Rester minimal : pas de refonte de nms.py, juste le paramétrage. Vérifier à la fin que sans argument le script produit exactement la même chose qu'avant.

Me demander avant de lancer quoi que ce soit sur le serveur.
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
