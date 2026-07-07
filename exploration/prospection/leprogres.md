# Prospection Le Progrès (leprogres.fr) — dossier manager

Candidat #3 de `candidats.md` (★★★ EBRA/Crédit Mutuel, accès pressenti freemium).
Croisement des rapports mapping / scrapper / explorateur + smoke-test serveur.
Rien n'est branché : ce dossier est prêt à valider par Corto.

## Verdict

**Ajoutable en « gratuits seuls » (filtre `free`)**, comme la_depeche/midilibre :
6/10 articles d'échantillon complets (63-734 mots), 4/10 tronqués en teaser
(34-144 mots) mais `div.textComponent` absent sur les payants → contenu vide →
`est_bloque` automatique, donc **aucun code de filtrage à écrire**, les
tronqués n'entrent jamais en base (cf `stockage.ecriture_csv`). Point de
vigilance corpus : la part gratuit/payant n'est mesurée que sur un échantillon
de 10 URLs (60/40, mix 2018→2026) — **à quantifier par époque avant
d'exploiter le corpus pour le mémoire** : si le gratuit s'effondre sur
2018-2020, la couverture historique sera maigre malgré un volume mappé
important. Mesure proposée : compter `isAccessibleForFree` sur ~100
articles/année une fois branché (colonne `free` déjà alimentée par pipeline),
ou un sondage dédié avant branchement si on veut trancher plus tôt.

## Synthèse des 3 rapports

**Mapping.** Source : pages d'archives datées
`https://www.leprogres.fr/archives/YYYY/JJ-MM` (⚠️ format **jour-mois**, pas
mois-jour), une page par jour, sans pagination, profondeur 2018 → 2026
(~3 100 pages-jour ; pré-2018 : rien, anciennes URLs en 410). Liens articles
au motif `href="/<rubrique>/YYYY/MM/DD/<slug>"` (ordre YYYY/MM/DD, différent
de l'URL page-jour). Volume ~1,5-2M d'URLs mappées (330-1000 articles/jour
selon l'époque, nombreuses éditions locales). Sitemaps morts ou inutiles
(`sitemap-request.xml` = flux de dépublication, pas un index d'articles).
`robots.txt` : `/archives` autorisé pour `*`, pas de `Crawl-delay` déclaré
(politesse ≥1,5s gardée par prudence côté script). **`robots.txt` contient
aussi les blocs anti-IA standard (`anthropic-ai`/`Claude-Web` `Disallow: /`)**
— déjà le cas chez le_monde, le_figaro et ouest_france actuellement en
production, donc cohérent avec la pratique actuelle du projet, mais à noter
explicitement ici : **décision de branchement final à Corto**, ce dossier ne
tranche pas ce point. Tolérer les 410 (dépublications), pas de blocage
particulier repéré sinon.

**Scrapper.** 10/10 en HTTP 200 via curl_cffi (moteur basic), aucun blocage
CDN. 6 gratuits COMPLETS (63-734 mots) ; 4 premium TRONQUÉS (teaser 34-144
mots + blocs `.paywall-content`). `isAccessibleForFree` 100 % cohérent avec le
statut réel observé. Répartition échantillon : 60 % gratuit / 40 % premium,
mix à toutes les époques (2018 inclus — pas de rupture visible entre
« ancien » et « récent » sur ce petit échantillon, mais 10 URLs ne suffisent
pas à conclure par époque). HTML sauvés côté serveur dans
`/data/elias/stage-mids-v2/exploration/prospection_html/leprogres/`.

**Explorateur.** Entrée validée par exécution réelle de `extraire()` sur les
10 HTML :
`"leprogres": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.textComponent"}}`
— `articleBody` du json-ld jamais peuplé, sélecteur DOM `div.textComponent`
obligatoire. Gratuits : 6/6 complets, titre/auteur/date OK. Premium :
`div.textComponent` absent du HTML servi → contenu vide → `est_bloque=True`
automatiquement (aucune phrase-signal à ajouter à `scraping/paywall.py`,
contrairement à d'autres médias payants). Colonne `free` fiable 10/10.

## Smoke-test (vérification manager, 3 requêtes réseau)

Transfert du script de smoke-test via une branche git temporaire
(`smoke-leprogres-tmp`, poussée puis supprimée après usage — pas de scp, cf
la règle « déploiement serveur via git »), exécuté sur gallica
(`git show FETCH_HEAD:exploration/_smoke_leprogres_manager.py > /tmp/... &&
PYTHONPATH=. .venv/bin/python /tmp/...`), fichier temporaire et branche
supprimés après vérification. 3 requêtes au total, sous le budget de 6.

- `archives/2018` : HTTP 200, 470 703 car., **365 jours trouvés**, format
  confirmé `/archives/2018/JJ-MM` (3 premiers : `2018/01-01`, `2018/01-02`,
  `2018/01-03` — bien JJ-MM, pas MM-JJ).
- `archives/2018/01-06` (1er juin 2018, format JJ-MM) : HTTP 200, 1 691 863
  car., **1024 URLs article uniques** — dans la fourchette haute attendue
  (330-1000/jour), légèrement au-dessus, cohérent avec « nombreuses éditions
  locales » signalé par le rapport mapping.
- `archives/2026/06-07` (6 juillet 2026, format JJ-MM) : HTTP 200, 1 086 359
  car., **470 URLs article uniques** — dans la fourchette attendue.
- 3 URLs conformes au format `<rubrique>/YYYY/MM/DD/<slug>` :
  - `https://www.leprogres.fr/a-propos/2018/06/01/delize-italiane`
  - `https://www.leprogres.fr/actualite/2018/06/01/200-volailles-vivantes-derobees-dans-la-nuit`
  - `https://www.leprogres.fr/coupe-du-monde-de-football/2026/07/06/allo-gianni-c-est-donald-le-billet-d-humeur-de-notre-envoye-special`
- Note manager : la rubrique `a-propos` (2018) ressemble à du contenu
  sponsorisé/natif plutôt qu'à un article éditorial — conforme au format
  d'URL donc retenu par le mapping tel quel, à garder en tête pour un futur
  filtrage éditorial si besoin (hors scope de cette mission).
- Note manager : la page du 06/07/2026 contient aussi un article daté
  `2026/07/05` (la veille) — une page-jour mélange donc occasionnellement des
  articles d'un autre jour (mécanisme similaire à ce qui avait motivé un
  filtre par date pour 20minutes). Ici **pas de filtre nécessaire** : le
  script final déduplique globalement (pas de décompte strict par jour), donc
  ce mélange ne crée ni doublon ni erreur, juste un compteur de progression
  mensuel légèrement approximatif — sans conséquence sur le CSV final.

## Entrée medias.py prête à coller (NON appliquée)

```python
"leprogres": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.textComponent"}},
```

À insérer dans le bloc des médias `basic` de `scraping/medias.py`, dans la
section « payants non contournables → filtrer via la colonne `free` » (celle
de marianne/midilibre/paris_normandie/latribune/liberation), avec un
commentaire du type `# leprogres : validé prospection 07/07/2026, freemium
(échantillon 60/40 gratuit/payant, part à quantifier par époque), payants
tronqués → div.textComponent absent → échec propre automatique`. `attente`
non précisé → `ATTENTE_BASIC` par défaut suffit (aucun signe d'anti-bot en
basic, pas de `Crawl-delay` déclaré).

## Plan de branchement (à exécuter uniquement sur validation explicite de Corto)

1. **Quantifier la part de gratuit par époque** avant d'aller plus loin :
   soit un sondage dédié (~100 URLs/année sur 2018-2026, comptage
   `isAccessibleForFree`) avant branchement, soit lancer le pipeline puis
   mesurer sur la colonne `free` du CSV une fois ~100 articles/année
   accumulés — à trancher par Corto selon l'urgence d'avoir le chiffre
   avant vs. après branchement.
2. Statuer sur le point robots.txt anti-IA (blocs `anthropic-ai`/`Claude-Web`
   `Disallow: /`, déjà présents chez le_monde/le_figaro/ouest_france en
   production) — décision de branchement final à Corto, ce dossier ne
   tranche pas.
3. Lancer `python -m exploration.mapping_leprogres` sur gallica (~1h45,
   ~3 100 pages-jour à 1,5s de politesse). Produit
   `exploration/leprogres_url.csv` (~1,5-2M URLs brutes attendues, cf volumes
   ci-dessous — avant filtrage gratuit/payant qui se fait au scraping, pas au
   mapping). Relançable par année via la constante `ANNEES` en cas
   d'interruption — le CSV est complété par ajout, pas écrasé.
4. Copier/déplacer `exploration/leprogres_url.csv` vers `DATA_DIR` (par
   défaut `/data/elias/stage-mids/data/`, ou le `STAGE_DATA_DIR` de test si
   on valide d'abord sur base isolée) — c'est ce dossier que
   `scraping/pipeline.py` scrute (`DATA_DIR.glob("*_url.csv")`).
5. Charger en base : `charger_nouvelles_urls(conn)` dans
   `scraping/pipeline.py` est actuellement **désactivé** (ligne commentée
   dans `main()` : `# charger_nouvelles_urls(conn)  # désactivé : pas de
   nouveaux CSV pour l'instant`) — il faudra soit la réactiver le temps du
   chargement, soit l'appeler manuellement une fois, puis la recommenter
   si elle doit rester désactivée par défaut.
6. Ajouter l'entrée `"leprogres"` ci-dessus dans `scraping/medias.py`.
7. Relancer le pipeline pour que `leprogres` entre dans le prochain
   `new_batch()` — note : `lancer.sh` est actuellement à l'arrêt depuis le
   06/07 (tests v2 en cours, cf `project_lancer_en_pause`), donc ce point
   dépend de la reprise générale du scraping, pas seulement de Le Progrès.

## Volumes attendus

- ~3 100 pages-jour sur 2018-2026 (365/366 jours × 9 ans, dont 2026
  partielle).
- 330-1000 articles/jour selon le rapport mapping (nombreuses éditions
  locales) → **~1,5-2 000 000 URLs brutes** attendues dans
  `leprogres_url.csv`, cohérent avec les comptes du smoke-test (470-1024
  URLs/jour observés, 2018 et 2026 confondus).
- Ce volume brut n'est **pas** le volume utile pour le mémoire : ~60 % serait
  gratuit sur l'échantillon (10 URLs), soit un ordre de grandeur de
  900 000-1 200 000 articles exploitables **si** le taux est stable dans le
  temps — hypothèse non vérifiée par époque, d'où le point 1 du plan de
  branchement.

## Intérêt pour le mémoire

Le Progrès (Lyon) appartient au groupe EBRA, filiale du Crédit Mutuel,
constitué par rachats successifs de la presse régionale de l'Est et du
Sud-Est entre 2007 et 2010 (Le Progrès, Dernières Nouvelles d'Alsace,
L'Est Républicain, Le Républicain Lorrain, Vosges Matin, Le Bien Public,
Le Journal de Saône-et-Loire...). Ce mouvement de concentration bancaire
sur la presse régionale est un cas différent de CNews (rachat par un groupe
médiatique) ou 20minutes (recomposition actionnariale entre éditeurs) : ici
c'est un acteur financier qui devient propriétaire de presse quotidienne
régionale, avec une mutualisation éditoriale documentée entre titres EBRA
depuis. Profondeur d'archive 2018-2026 : le rachat (2007-2010) est **avant**
le début de l'archive disponible, donc pas de mesure directe de la rupture
initiale ; l'intérêt porte plutôt sur la mutualisation éditoriale
inter-titres EBRA (contenu partagé entre Le Progrès et les autres quotidiens
du groupe) sur la période observable, si le corpus gratuit s'avère
suffisant après quantification (point de vigilance ci-dessus).

## Fichiers produits par ce dossier

- `exploration/mapping_leprogres.py` : script de mapping complet
  (2018-2026, structure page-année → page-jour validée par smoke-test),
  prêt à lancer mais **non lancé** (mapping complet interdit dans le cadre
  de cette mission).
- `exploration/prospection/leprogres.md` : ce dossier.

Aucun fichier de `scraping/` n'a été modifié ; `medias.py` n'a pas été
touché ; le mapping complet n'a pas été lancé. Le script de smoke-test et la
branche git temporaire utilisés pour le valider ont été supprimés après
vérification (aucune trace dans l'historique de `scrapping_v2`).
