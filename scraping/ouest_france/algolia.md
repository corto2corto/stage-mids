# Accès Algolia Ouest-France

Ouest-France expose son contenu via Algolia (moteur de recherche SaaS), avec
**deux App ID distincts** qui donnent des données totalement différentes.
Les confondre fait perdre du temps.

| App ID | Index | Contenu |
|---|---|---|
| `76T47RYM6W` | `pages`, `pages_qual`, `pages_test` | 11,6 M pages, archives papier scannées OCR (~1955-2026) |
| `C8KP7JV01T` | `articles` (+ `articles_bydate_asc/desc`, `elections`, `programme_tv`, `videos`, `podcasts`, `cinema`…) | **39,2 M enregistrements, 1990-2026** |

Exploration : `python -m exploration.sonder_algolia_of` (clé via `OF_ALGOLIA_KEY`).

## Index `articles` (C8KP7JV01T)

8 titres du groupe SIPA séparables par le champ `source` — détail dans
[sources.md](sources.md). Volume : ~1,7-2,4 M/an de 2002 à 2016 (pic 2004),
~700 k/an depuis 2021.

**Champs** : `titre`, `chapeau` (résumé), `texte` (**le corps de l'article**,
voir ci-dessous), `article` (booléen, pas le contenu malgré son nom), `payant`,
`print`, `nbMots`, `categories`, `zonesGeo`, `datePublication`, `pagesVuesAT`,
`url`. `proprietaires`/`producteurs` = UUID interne (auteur/service), pas le
groupe propriétaire.

### Le texte intégral est dans `articles_bydate_desc`, pas dans `articles`

C'est **l'index** qui décide, pas l'endpoint : `articles` ne renvoie jamais le
champ `texte` (même avec `attributesToRetrieve: ["*"]` ou un `getObject`
direct), alors que le réplica `articles_bydate_desc` le renvoie systématiquement.

Le texte est **complet** (il se termine proprement, pas de coupure), et il est
servi **y compris pour les articles payants** — donc pas besoin de scraper ni
de contourner le paywall.

L'écart entre `nbMots` et le nombre de mots de `texte` (70-90 %) n'est pas une
troncature : `nbMots` compte en plus le titre, le chapô et les légendes photo.

Couverture du texte sur les articles web (`print=0`), échantillons de 300/an :

| Année | 2002 | 2006 | 2010 | 2014 | 2018 | 2021 | 2024 | 2026 |
|---|---|---|---|---|---|---|---|---|
| avec texte | 98 % | 96 % | 88 % | 87 % | 94 % | 97 % | 93 % | 100 % |

Les enregistrements papier (`print=1`) ont en revanche un `texte` vide ou
minuscule : ce sont des fragments d'édition papier (brèves, légendes, titres de
rubrique). Filtrer `print=0`.

## Index `pages` (76T47RYM6W)

Scans OCR de pages entières de journal, pas des articles isolés. Champs :
`texte` (plein texte OCR de la page), `folio`, `une`,
`url` = `/page/<objectID>` — ce chemin ne correspond **pas** à une page du
site web public (usage interne kiosque/archives).

## Requêtage

C'est un moteur de recherche, pas du SQL : il rend les *meilleurs* résultats,
pas *tous*. Trois leviers : `query` (mots), `filters`, `facets` (comptages).

Facettes déclarées, seules filtrables en `attribut:valeur` : `anneePublication`,
`moisPublication`, `jourPublication`, `source`, `categories`, `zonesGeo`, `type`.
`payant` et `print` se filtrent en numérique (`payant=1`, `print=0`) —
`payant:false` renvoie 0 sans lever d'erreur, piège classique.

Le header `Referer: https://www.ouest-france.fr/` est obligatoire sur les deux
App ID, sinon « Method not allowed with this referer ».

### Pièges mesurés

- `nbHits` est **approximatif** dès qu'un filtre porte sur un gros volume
  (`exhaustiveNbHits: False`) — il peut même dépasser le vrai total. Il est
  exact sur les petits ensembles. Les **comptes par facette sont toujours
  exacts** (`exhaustiveFacetsCount: True`) : passer par les facettes pour tout
  chiffre fiable.
- Plafond de **1000 résultats par requête**, `browse` refusé (403). Pour
  extraire un corpus, découper jour → source → `zonesGeo` jusqu'à passer sous
  1000 (une journée de 2004 = 8 116 articles, dont 7 063 pour `of` seul).

### Clés

Générées côté client avec un `validUntil` de **~24 h**. Une clé est signée pour
un App ID précis — une clé de `76T47RYM6W` ne marchera jamais avec
`C8KP7JV01T`. Pas d'accès permanent sans re-extraction.

Récupération automatique (remplace le relevé manuel dans l'onglet Réseau) :

    eval $(python scraping/ouest_france/recuperer_cle.py --export)   # OF_ALGOLIA_KEY + APP_ID
    python scraping/ouest_france/recuperer_cle.py                    # simple affichage

`recuperer_cle.py` ouvre `/recherche/` sous Firefox headless et lit les en-têtes
`x-algolia-api-key` / `x-algolia-application-id` dans le journal réseau du
navigateur (WebDriver BiDi, `before_request_sent`) — même source que l'onglet
Network.

Deux pièges que le script gère :

- **Il faut lancer une vraie recherche.** Au simple chargement de la page, le
  site ne demande qu'une clé restreinte à `restrictIndices=shopping`, qui est
  refusée sur `articles`. Le script tape une requête et valide Entrée.
- **Vérifier la portée avant d'utiliser la clé.** Elle est encodée en base64
  dans la clé elle-même (`restrictIndices=...&validUntil=...`) : le script
  décode et garde celle qui couvre `articles`.

À noter : sous Firefox, un script injecté via `add_preload_script` tourne dans
un contexte isolé de la page (il ne voit pas son `window`) — patcher `fetch`
pour intercepter les appels ne marche pas. Passer par le journal réseau.

## Limites pour le mémoire

**Une grande partie est du papier sans page web ni texte** (`print=True` ↔ URL
`/premium/?article_id=<uuid>`), échantillons de 1000/an :

| Année | 2004 | 2014 | 2020 | 2024 | 2026 |
|---|---|---|---|---|---|
| part papier | 87 % | 51 % | 12 % | 16 % | 0 % |

Filtrer `print=0` pour ne garder que le web. Trois formes d'`url` à normaliser :
absolue (récents), relative `/region/ville/slug-uuid` (2019-2024), et
`/premium/?article_id=` (papier, pas de page web).

**Piste à creuser** : `co`/`po`/`ml` sont des titres passés sous contrôle du
groupe SIPA-Ouest-France — cas de rachat potentiellement exploitable, avec des
corpus comparables dans le même index. Dates et modalités à vérifier (non fait).

## Récolte au format du pipeline

`python -m scraping.ouest_france.recolte <début> <fin> [--titre of]`, bornes en année
(`2024`) ou en date (`2024-03-10`). Sans `--titre`, les 8 titres sont récoltés
l'un après l'autre, un CSV chacun (voir [sources.md](sources.md) pour les noms).

**`ouest_france2.csv`, pas `ouest_france.csv`** : ce dernier appartient à l'autre
chaîne de scraping (4,5 Go, alimentée en continu) et ne doit jamais être touché.

Colonnes de `scraping/stockage.py` :

| Colonne | Champ Algolia | Transformation |
|---|---|---|
| `id` | `objectID` | — |
| `url` | `url` | relative → absolue |
| `titre` | `titre` | — |
| `auteur` | *aucun champ* | laissé vide, cf. tâche `auteur-ouest-france` |
| `date` | `datePublication` | timestamp → ISO, heure de Paris |
| `section` | `url` | premier segment du chemin (`/sciences/…` → `sciences`) |
| `free` | `payant` | inversé → `oui`/`non` |
| `contenu` | `texte` | — |

### Ce qui rend la récolte autonome

- **Découpage sans perte.** Une tranche est recoupée en deux tant qu'elle rend
  le plafond de résultats. Le critère est le nombre de hits rendus, pas
  `nbHits` : ce dernier est approximatif sur les gros volumes, et une
  sous-estimation ferait manquer des articles sans que ça se voie.
- **Renouvellement de clé.** Sur un 401/403, le script rappelle
  `recuperer_cle.py` et reprend la requête. Indispensable : une récolte complète
  dure plus longtemps que la validité d'une clé.
- **Reprise.** `recolte_avancement.json` note le dernier jour terminé par titre ;
  une relance repart de là sans relire les CSV (qui feront plusieurs Go). Si la
  récolte est coupée en plein jour, ce jour est refait en entier — quelques
  doublons possibles, à dédoublonner sur `id`.
- **Jours en échec rejoués.** Ils sont notés et repris en fin de titre, puis
  laissés dans le fichier d'avancement s'ils échouent encore. Sans ça le curseur
  passerait par-dessus et la journée serait perdue silencieusement.
- **Années vides sautées.** Les petits titres n'existent que sur quelques
  années : une requête par année évite d'en faire 365 pour rien (5 années vides
  en 6 s au lieu de 30 min).

Débit mesuré le 12/08 sur `of`, une journée : 1287 articles en 6 s (2026),
1656 en 8 s (2020), 741 en 2 s (2014). Les années antérieures à ~2010 sont
quasi vides côté web (1 article le 15/06/2004) mais coûtent quand même une
requête par jour. Ordre de grandeur pour les 8 titres sur 1990-2026 :
**environ une journée de collecte continue**, donc au moins une rotation de clé.

Vérifié le 12/08 : 1164 articles récoltés sur une journée à 1164 attendus, sans
doublon, découpage déclenché ; reprise testée (relance = 0 ajout, extension de
période = repart au bon jour).

## Corpus déjà collecté sur gallica

`/data/corpus/ouestfranceweb/` contient un corpus tiré de cette API en avril
2026 par `scraping_ouestfrance.py` : `ouest_france_articles_<annees>.jsonl`
de 1995 à 2026 (~6,8 Go) plus un CSV fusionné.

Le script utilise `articles_bydate_desc`, découpe par `numericFilters` sur
`datePublication` (un jour par requête, pagination interne), reprend où il en
était via les `objectID` déjà écrits, et respecte un délai entre appels.

**Attention à son périmètre** : ses `FACET_FILTERS` sont
`["source:of", "zonesGeo:Ille-et-Vilaine"]` — le corpus existant est donc
Ouest-France **Ille-et-Vilaine seulement** (vérifié : 100 % `of`, 100 %
Ille-et-Vilaine, 97 % avec texte). Pour couvrir d'autres départements ou
d'autres titres du groupe, vider ou modifier cette liste.
