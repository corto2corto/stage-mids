---
title: "Moissonnage MIDS"
author: "Corto"
date: "2026-05-05"
engine: markdown
format:
  html:
    toc: true
    code-fold: true
---

## Contexte

Analyse de l'impact des rachats de journaux français sur le contenu éditorial.

Les rachats de journaux français modifient-ils la couverture thématique des articles ?

## Création répertoire GitHub, identification des journaux

Répertoire Github : https://github.com/corto2corto/stage-mids

Liste des journaux cibles :

- JDD : Cible d'un rachat médiatisé par le groupe Bolloré en 2021, puis d'une "prise de contrôle" en 2023. Sur le site web, on a seulement accès aux articles récents. Reste à voir comment trouver les années précédentes. Une partie présente sur Gallica (1864-1899).

- Le Monde : Rachat par Niel, Bergé, Pigasse en 2010, puis montée de Niel à partir de 2023. Facilement récupérable, complètement disponible sur Gallica.

- Le Figaro : Rachat par Serge Dassault en 2004. À première vue, le scraping a l'air complexe : pas de système de recherche propre, présence d'un paywall. Une partie présente sur Gallica.

- Libération : Rachat par Drahi en 2014, puis reprise de l'indépendance. Présence d'archives propres depuis 1998 jusqu'à aujourd'hui. Paywall éventuel.

- Les Échos : Rachat par Bernard Arnault en 2007. Présence d'archives propres depuis 1991 jusqu'à 2020. Paywall éventuel.

- La Provence : Rachat par Saadé en 2023. Pas de système de recherche propre, site web plutôt dense.

- Paris Match : Rachat par LVMH en 2024. Moyennement scrappable mais faisable.

- L'Express : Rachat par Drahi en 2015. Présence d'archives propres depuis 1953 jusqu'à 2026. Paywall éventuels.

- Le Nouvel Obs : Rachat par Niel, Bergé, Pigasse en 2014, 4 ans après le Monde. Système de recherche opérationnel, mais uniquement par mot et correspondance de mots.

- Valeurs actuelles : Rachat par un trio d'investisseurs, dont Stérin.

**[MAJ 22/07/2026]** La liste de départ a beaucoup grossi : **32 journaux** sont
aujourd'hui configurés dans le pipeline, contre 10 ici. Les ajouts et leurs
motifs sont détaillés dans « Médias ajoutés » (Atlantico, La Dépêche,
L'Opinion, Sud Ouest, Challenges, Le Télégramme), « Batch de 15 nouveaux médias
(06/07/2026) » (Ouest-France, Midi Libre, Le Parisien, Libération, BFMTV,
La Provence, La Croix, Gala, Voici, Paris-Normandie, La Tribune, France-Soir,
Marianne…) et « Branchement de cnews et 20minutes (2026-07-15) ». Deux titres
ont été mappés puis écartés (L'Express, Le Point), cf. « Moteur par média ».

## Premier test de scrapping

### JDD

On souhaite scrapper l'article du JDD suivant : <https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226>.

#### v0.0.0 - Via Request

```{python}
import requests
from bs4 import BeautifulSoup

response = requests.get("https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226")
soup = BeautifulSoup(response.text, "html.parser")

paragraphes = soup.find_all("p")

print(response.text[:2000])

# Protection par Cloudflare 
```

En utilisant le module `request`, on ne peut pas récupérer le HTML directement à cause de la protection Cloudflare.

#### v0.1.0 - Via Playwright

Plutôt qu'utiliser `request`, on émule un navigateur Chrome via la bibliothèque `playwright` ([lien](https://playwright.dev/python/)) qui va chercher à récupérer le html de la page.

```{python}
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226")
    page.wait_for_load_state()
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")
paragraphes = soup.find_all("p")

print(len(paragraphes))
```

La protection Cloudflare arrive à bloquer le navigateur, et le html n'est pas récupéré.

#### v0.1.1 - Via Playwright Stealth

Playwright propose une version furtive (*stealth*) de son API, et celle-ci va nous permettre de récupérer le HTML.

```{python}
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False = navigateur visible
    page = browser.new_page()
    stealth_sync(page)  # masque les traces d'automatisation
    page.goto("https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226")
    page.wait_for_load_state("domcontentloaded")
    
    html = page.content()
    browser.close()
    
    # On télécharge le html dans un fichier, qu'on passera à BS4 ensuite

with open("173226.html", "w", encoding="utf-8") as f:
    f.write(html)
```

#### v0.2.0 - Version Paywall

En utilisant le dépôt <https://gitflic.ru/project/magnolia1234/bypass-paywalls-firefox-clean>, il est possible d'accéder aux articles protégés par un paywall.

On a d'abord téléchargé le fichier bypass.xpi, et configuré Firefox avec l'extension Bypass + UBlock Origin (configuration avec les filtres `EasyList Cookies` et `I don't care about cookie`, afin que les bannières de consentement ne bloquent pas le bypass).

Grâce à cette configuration, on arrive bien à accéder à n'importe quel article.

Le problème est que Playwright émule un navigateur classique, et on voudrait plutôt utiliser notre navigateur avec la configuration anti-paywall spécifique.

L'option la plus simple à première vue, est d'utiliser `Selenium` ([lien](https://selenium-python.readthedocs.io/)), qui permet non pas d'émuler un navigateur, mais plutôt de contrôler un navigateur local. L'idée est d'utiliser le combo Selenium + Firefox Bypass.

```{python}
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    html = driver.page_source

with open("test.html", "w", encoding="utf-8") as f:
    f.write(html)
```

### Le Monde et Le Figaro

Le même script fonctionne, en ajoutant un `time.sleep(2)` après le chargement de la page pour laisser le bypass s'effectuer (il est un peu plus lent sur Le Monde). Le Figaro passe avec exactement le même code.

### Libération

Ici il faut vider les cookies pour que le bypass fonctionne : on charge la page une première fois, on appelle `driver.delete_all_cookies()`, puis on recharge la page avant de récupérer le HTML.

### Bilan du scrapping

Problème restant : des phrases génériques propres à chaque journal apparaissent ponctuellement. Deux pistes :

- Construire une BDD de ces phrases et les filtrer dans le script de parsing.
- Utiliser un prompt LLM : « Voici un article, élimine les phrases génériques de pub qui ne sont pas propres à l'article. » (à éviter, trop long)

### Actuellement :

| Journal           | Chrome | Firefox | Commentaires                              |
|-------------|-------------|-------------|---------------------------------|
| JDD               | —      | OK      |                                           |
| Le Monde          | —      | OK      | `sleep(2)` nécessaire                     |
| Le Figaro         | —      | OK      | Même script que Le Monde                  |
| Libération        | —      | OK      | Suppression des cookies + `sleep(2)`      |
| Paris Match       | —      | OK      | Même script que Le Monde                  |
| Les Échos         | OK     | KO      |                                           |
| Nouvel Obs        | OK     | \~      | Bypass irrégulier sous Firefox            |
| Valeurs Actuelles | OK     | —       |                                           |
| Capital           | OK     | —       |                                           |
| Nice Matin        | OK     | —       | Pas de paywall, archives 2015–2026        |
| Télérama          | OK     | —       |                                           |
| L'Express         | \~     | \~      | Bypass irrégulier sur les deux extensions |
| La Provence       | KO     | KO      | Paywall résistant, à étudier              |

**[MAJ 22/07/2026]** Chrome a été abandonné : Selenium ne sait pas y injecter
d'extension proprement (il faut un profil préparé à la main, qui ne se charge
pas en `--headless`), alors que Firefox installe le `.xpi` au démarrage. Tout
le pipeline tourne donc sous Firefox, et la colonne « Chrome » de ce tableau
n'a plus d'objet. La question « quel navigateur pour quel journal » a elle
aussi disparu : elle est devenue « quel moteur », cf. « Moteur par média ».

## Pagination :

Le but de cette section est de "cartographier" les sites web de chaque journal. L'objectif est d'obtenir l'URL de chaque article disponible en ligne (donc un grand nombre).

En général, le sitemap est indiqué dans le fichier `robots.txt`.

La seconde approche est d'inspecter la page à la main quand on a des rubriques avec une pagination explicite (ex : politique/page2). Comme une page contient dans son HTML une liste de liens vers les articles, on peut alors parcourir chaque page et récupérer les liens.

Après exploration des sitemap, on a en résumé :

| Journal | Sitemap | Commentaire |
|---------------------|---------------------|------------------------------|
| JDD | [lejdd.fr/sitemap.xml](https://www.lejdd.fr/sitemap.xml) | Rien avant 2022 |
| Le Monde | [lemonde.fr/sitemap_index.xml](https://www.lemonde.fr/sitemap_index.xml) | Un sous-sitemap par jour depuis 1945 ; caractères de contrôle invalides à nettoyer (regex avant parsing) |
| Figaro | [sitemaps.lefigaro.fr/.../articles.xml](https://sitemaps.lefigaro.fr/lefigaro.fr/articles.xml) | Index simple, 7572 sous-sitemaps (2006–2026) |
| Libération |  | Sur Arc XP, pagination plafonnée à 10 000 articles + protection DataDome → abandon, on se limite au sitemap public |
| Paris Match | [parismatch.com/sitemap.xml](https://www.parismatch.com/sitemap.xml) | Sitemap limité (2022–2026) ; anciens sitemaps via la CDX API Wayback (format `id_` pour le XML brut) |
| Les Echos | [sitemap.lesechos.fr/sitemap_index.xml](https://sitemap.lesechos.fr/sitemap_index.xml) | Sous-sitemaps gzippés (`.xml.gz`) → décompression `gzip` (détection magic number `\x1f\x8b`) |
| Nouvel Obs | [nouvelobs.com/.../sitemap-index-articles.xml](https://www.nouvelobs.com/sitemap/sitemap-index-articles.xml) | Articles depuis 2000 |
| Valeurs Actuelles | [valeursactuelles.com/sitemap_index.xml](https://www.valeursactuelles.com/sitemap_index.xml) | Sitemap-index Yoast/WordPress ; sous-sitemaps listés à la main (4 catégories) |
| Capital | [capital.fr/sitemap/articles.xml](https://www.capital.fr/sitemap/articles.xml) | Sous-catégories numérotées (1–500) |
| Nice Matin | [nicematin.com/sitemap.xml](https://www.nicematin.com/sitemap.xml) | RAS |
| Télérama | [telerama.fr/sitemaps/sitemap_index.php](https://www.telerama.fr/sitemaps/sitemap_index.php) | URL en `.php` mais XML standard (1992–2026) |

### [MAJ 22/07/2026] Pagination des nouveaux médias

Les journaux ajoutés depuis (cf. « Médias ajoutés », « Batch de 15 nouveaux
médias », « Branchement de cnews et 20minutes ») ont été cartographiés de la
même façon. Le sitemap reste la source par défaut ; quand il est absent ou
plafonné, on retombe sur la pagination HTML ou sur les archives de la Wayback
Machine. Toutes ces particularités sont désormais des fiches de configuration
dans [`mapping/catalogue.py`](mapping/catalogue.py) (cf. « Le mapping regroupé
en un module »).

| Journal | Sitemap | Commentaire |
|---------------------|---------------------|------------------------------|
| Atlantico | [atlantico.fr/sitemap-index.xml](https://atlantico.fr/sitemap-index.xml) | Sous-sitemaps mensuels (domaine sans `www`) |
| La Dépêche | [ladepeche.fr/sitemap.xml](https://www.ladepeche.fr/sitemap.xml) | Mensuel découpé en parts, sous-sitemaps gzippés |
| L'Opinion | [lopinion.fr/sitemap.xml](https://www.lopinion.fr/sitemap.xml) | Mensuel `sitemap-AAAAMM.xml` |
| Challenges | [challenges.fr/sitemap.xml](https://www.challenges.fr/sitemap.xml) | Mensuel, gzippé |
| Sud Ouest | [sudouest.fr/sitemap.xml](https://www.sudouest.fr/sitemap.xml) | Mensuel daté ; anti-bot strict → empreinte Chrome (`curl_cffi`) |
| Le Télégramme | [letelegramme.fr/sitemaps/sitemap.xml](https://www.letelegramme.fr/sitemaps/sitemap.xml) | Mensuel gzippé ; le CDN bloque l'empreinte TLS de `requests` → `curl` |
| Gala | [gala.fr/sitemaps/articles.xml](https://www.gala.fr/sitemaps/articles.xml) | Index → sous-sitemaps mensuels |
| Voici | [voici.fr/sitemap/articles.xml](https://www.voici.fr/sitemap/articles.xml) | Index → sous-sitemaps paginés |
| La Croix | [la-croix.com/feeds/sitemaps/sitemaps_articles.xml](https://www.la-croix.com/feeds/sitemaps/sitemaps_articles.xml) | Index → sous-sitemaps mensuels |
| BFMTV | [bfmtv.com/sitemap_index_arbo_contenu.xml](https://www.bfmtv.com/sitemap_index_arbo_contenu.xml) | Sous-sitemaps `.xml.gz` ; replays et podcasts écartés du corpus |
| Midi Libre | [midilibre.fr/sitemap.xml](https://www.midilibre.fr/sitemap.xml) | Mensuel en parts, `.xml.gz` |
| Ouest-France | [ouest-france.fr/sitemap.xml](https://www.ouest-france.fr/sitemap.xml) | DataDome : les ~179 sous-sitemaps ne sont servis qu'à un vrai navigateur → Firefox headless |
| Paris-Normandie | [sitemapindex.xml](https://www.paris-normandie.fr/sites/default/files/sitemaps/www_paris_normandie_fr/sitemapindex.xml) | Akamai : passe avec l'UA académique + `curl`, filtre `/article/` |
| France-Soir | [francesoir.fr/sitemap.xml](https://www.francesoir.fr/sitemap.xml) | Sitemap paginé (`?page=N`) |
| cnews | [cnews.fr/sitemap.xml](https://www.cnews.fr/sitemap.xml) | Paginé, ~215 pages ; `crawl-delay` 10 s imposé, empreinte Chrome |
| Libération | [liberation.fr/arc/outboundfeeds/sitemap/](https://www.liberation.fr/arc/outboundfeeds/sitemap/) | Arc XP, plafonné à ~10 000 articles récents → historique complété par la Wayback |
| Le Parisien | — | Pas de sitemap d'archives : pagination des pages d'archives, une par jour (depuis 2010) |
| 20 Minutes | — | Pas de sitemap d'archives : pages `/archives/AAAA/MM-JJ` (depuis 2006) |
| Marianne | — | Pas de sitemap d'articles : pagination des 7 rubriques |
| Mediapart | — | Pagination des rubriques (le sitemap par rubrique ne couvre que les news) |
| La Provence | — | Pagination limitée à ~5-7 pages par rubrique → historique via la Wayback |
| La Tribune | — | Refonte Next.js rendue côté client → Wayback (API CDX) |

Mappés puis écartés : **L'Express** (deux sitemaps hebdomadaires, 2010-2020 et
2020-2026) et **Le Point** (aucun sitemap, DataDome bloque tout → Wayback
seule) — raisons dans « Moteur par média ».

### Détail des sitemap

Les sites de presse exposent des fichiers `sitemap.xml` destinés aux moteurs de recherche, qui listent toutes les pages indexables du site. C'est un format en deux niveaux : un `sitemap-index` qui pointe vers des sous-sitemaps, et chaque sous-sitemap qui contient les URLs d'articles. C'est ce mécanisme qu'on exploite : on télécharge l'index, on parcourt chaque sous-sitemap, on en extrait les URL des articles qui sont dans des balises `<loc>`.

Comme certains serveurs renvoient ponctuellement des réponses vides (avec un code HTTP 200) ou limitent le débit, chaque téléchargement est entouré d'un `try/except` et espacé par un `time.sleep`, pour ne pas perdre la progression sur un échec passager.

### Choix du format de stockage

Migration de JSON vers JSONL (JSON Lines). Une ligne par sitemap traité, ajoutée en mode append. Avantages : écriture instantanée quelle que soit la taille du fichier, robustesse aux crashs (un crash corrompt au pire la dernière ligne), structure de récupération naturelle.

Format final adopté pour chaque ligne :

``` json
{"type": "ok", "sitemap": "https://...", "urls": ["url1", "url2", ...]}
{"type": "echec", "sitemap": "https://..."}
```

Résultat de cette époque : un fichier JSONL par journal, stocké dans Google
Drive — pour chaque ligne, l'information complète sur un sitemap (succès ou
échec, liste des URLs si succès).

**[MAJ 22/07/2026]** Le JSONL a disparu avec le passage sur serveur. Le
mapping écrit maintenant directement **un CSV d'URLs par journal** (une
colonne `url`), en **ajout + déduplication** : on ne réécrit jamais
l'existant, on ajoute au fil de l'eau les URLs manquantes (`Sortie` dans
[`mapping/generique.py`](mapping/generique.py)). Deux conséquences : une
reprise après interruption ne perd rien, et deux mappings peuvent nourrir le
même fichier (Libération récent par son sitemap + ses archives par la
Wayback). Le suivi des sitemaps échoués n'est plus stocké, il est simplement
journalisé à l'écran : le re-balayage étant idempotent, un échec se rattrape
en relançant.

Ces CSV sont ensuite versés dans la base `urls.db` (SQLite) par
[`verser_nouveaux.py`](scripts/verser_nouveaux.py), en `INSERT OR IGNORE` sur
l'index unique `(media, url)` — c'est elle qui pilote le scraping (cf.
« La base urls.db »). Plus rien ne passe par Google Drive.

### Mécanisme de reprise après interruption

Vu les volumes (jusqu'à plusieurs heures de scraping par journal) et les contraintes de Colab (timeout après 90 min d'inactivité, 12h maximum par session), un mécanisme de reprise était nécessaire. Au démarrage du script, le fichier JSONL existant est relu ligne par ligne pour reconstruire un `set` des sitemaps déjà traités. La boucle principale teste `if page in deja_traites` avant chaque téléchargement, sautant immédiatement ceux qui ont déjà été faits. Ce système permet de scraper sur plusieurs sessions étalées sans aucune perte de progression.

**[MAJ 22/07/2026]** Colab a disparu du projet : tout tourne sur le serveur,
dans des sessions `tmux` qu'on peut laisser des jours. La contrainte de départ
(une session coupée toutes les 12 h) n'existe donc plus, mais l'idée a été
gardée telle quelle, parce qu'un run long finit toujours par être interrompu
(plantage, coupure réseau, relance après correction). Le principe a juste
changé de support : ce n'est plus un `set` de sitemaps déjà traités relu dans
un JSONL, mais le CSV d'URLs lui-même qui est relu au démarrage — on ne
réécrit que ce qui manque (`Sortie`, cf. « Choix du format de stockage »).
Côté scraping, le même rôle est tenu par la colonne `etat` de `urls.db`.

### Articles actuels :

**[MAJ 22/07/2026]** URLs collectées par le mapping, comptées dans les CSV
d'URLs sur le serveur. Le corpus n'est plus un instantané : il grossit chaque
jour avec la collecte des sitemaps *news* (cf. « Collecte quotidienne des
sitemaps »).

| Journal | URLs collectées |
|---|---:|
| Ouest-France | 7 756 909 |
| Le Télégramme | 4 595 789 |
| La Dépêche | 4 340 152 |
| Le Monde | 4 094 518 |
| Le Figaro | 2 766 644 |
| Midi Libre | 1 370 140 |
| Le Parisien | 1 289 350 |
| Sud Ouest | 1 277 587 |
| Les Échos | 1 183 641 |
| La Provence | 906 681 |
| 20 Minutes | 840 678 |
| BFMTV | 772 114 |
| Nice-Matin | 650 583 |
| La Croix | 535 362 |
| Le Nouvel Observateur | 525 335 |
| cnews | 358 616 |
| Paris Match | 260 533 |
| Gala | 253 598 |
| Challenges | 181 898 |
| Paris-Normandie | 177 772 |
| Voici | 177 611 |
| Le Journal du Dimanche | 164 854 |
| Atlantico | 162 715 |
| L'Opinion | 144 762 |
| Capital | 137 565 |
| Télérama | 132 417 |
| La Tribune | 112 154 |
| Valeurs Actuelles | 103 246 |
| France-Soir | 85 494 |
| Mediapart | 53 032 |
| Marianne | 47 505 |
| **Total (31 médias branchés)** | **35 459 255** |

Mappés mais hors production : Libération (1 266 923 URLs, média en pause,
archives tronquées côté serveur), Le Point (1 094 630) et L'Express (342 887),
tous deux écartés.

## Pipeline de scraping

On a maintenant la liste des URLs (≈ 10 millions à l'époque, 35,5 millions au 22/07/2026). Reste à aller chercher le contenu de chaque article. L'idée : garder toutes les URLs dans une petite base, et les traiter par batchs jusqu'à épuisement. À chaque batch, une URL par journal, scrapée en parallèle.

```
urls.db
   ↓  batch.new_batch()
batch 
   ↓  navigateur.scraper()
html
   ↓  extraction.extraire()
   ↓  paywall.est_bloque()
résultats
   ↓  stockage
<media>.csv
urls.db
```

Chaque étape est un module séparé. Les sections suivantes les reprennent un par un, dans l'ordre du trajet.

| Module | Rôle |
|---|---|
| [`batch.py`](scraping/batch.py) | génère une URL non traitée par média |
| [`navigateur.py`](scraping/navigateur.py) | ouvre un Firefox pour chaque URL (un Firefox = un média), récupère le HTML |
| [`extraction.py`](scraping/extraction.py) | extrait métadonnées + article (titre, auteur, date, section, corps) |
| [`paywall.py`](scraping/paywall.py) | rejette les articles tronqués ou vides |
| [`stockage.py`](scraping/stockage.py) | écrit les métadonnées dans `<media>.csv`, met à jour l'état en base (1 échec / 2 succès) |
| [`pipeline.py`](scraping/pipeline.py) | enchaîne le tout, batch après batch |

**[MAJ 22/07/2026]** Ce chapitre décrit le pipeline v1 (batchs synchronisés,
un seul moteur Firefox, 10 médias). Il a été refondu depuis : **le pipeline
tourne aujourd'hui en une boucle indépendante par média, avec quatre moteurs
de scraping, sur 32 médias** — voir « Pipeline v2 : un rythme par média
(2026-07-07) » pour l'architecture actuelle et « Moteur par média » pour la
répartition. Trois modules se sont ajoutés au tableau ci-dessus :
[`moteurs.py`](scraping/moteurs.py) (choix du moteur par média),
[`basic.py`](scraping/basic.py) (requête HTTP sans navigateur) et
[`connexion.py`](scraping/connexion.py) (ouverture d'une session abonné).
Les sections qui suivent gardent la description d'origine, chacune suivie de
sa mise à jour.

### 0 . La base urls.db 

Une seule table SQLite, quatre colonnes : `id`, `media`, `url`, `etat`. Chaque URL a un état :

| `etat` | signification |
|---|---|
| `0` | à scraper |
| `1` | échec (page vide ou contenu tronqué) |
| `2` | succès (article écrit dans le CSV) |
| `3` | déjà disponible via regicid |

La base ne stocke pas les articles, juste leur état d'avancement. *(Table d'époque : les états 4 et 5, ajoutés depuis, sont décrits dans « Les états d'une URL » de la section Pipeline v2.)*

Avant de scraper, on retire ce qui existe déjà ailleurs. Une bonne partie de nos URLs sont déjà publiées, métadonnées comprises, dans un jeu de données public : [`regicid/press_metadata`](https://huggingface.co/datasets/regicid/press_metadata) (~11,17 M d'URLs de presse française). 
On a un petit script qui met tous les articles déjà scrapés à l'état 3 :
[`scripts/4_marquer_doublons.py`](scripts/4_marquer_doublons.py). Résultat : **7 273 332 doublons écartés**.

**[MAJ 22/07/2026]** Deux états ont été ajoutés depuis : `4` (échec confirmé,
l'URL a eu ses deux tentatives) et `5` (URL corrompue / non-article) —
détaillés dans « Les états d'une URL dans `urls.db` » et « Inspection des URLs
non-articles ». La base est passée en mode WAL pour supporter les écritures
concurrentes du pipeline v2, et elle est alimentée en continu par la collecte
quotidienne des sitemaps.

### 1. `batch.py` : Constituer un batch

La première étape est de sélectionner dans la BDD un article non traité par média, c'est le rôle de [`batch.py`](scraping/batch.py). Il interroge la base avec la commande SQL :

```sql
SELECT media, id, url FROM urls WHERE etat=0 GROUP BY media
```

On obtient un dictionnaire `{media: (id, url)}`, par exemple la première ligne du dictionnaire sera :
{"le_monde": (3, www.url_d_un_article.fr)}
Cela va nous permettre d'ouvrir un Firefox par média, où chaque Firefox ouvre l'article associé à son média.

**[MAJ 22/07/2026]** La notion de batch a disparu avec le pipeline v2 : chaque
média a son propre thread, qui tire sa prochaine URL tout seul sans attendre
les autres. La requête sélectionne désormais `WHERE etat IN (0,1)` — un média
qui n'a plus de nouveautés (état 0) passe automatiquement à la seconde chance
sur ses échecs (état 1), au lieu de sortir de la file (angle mort corrigé le
09/07 sur le_monde).

### 2. `navigateur.py` : Lancer des Firefox pré-configurés bypass

Pour récupérer le html des articles couverts par un paywall (cela fonctionne aussi sans paywall), on a besoin d'installer deux extensions sur Firefox qui travaillent en collaboration : bpc & ublock (parfois les cookies empêchent bpc de fonctionner, c'est alors à ublock de les désactiver).
On utilise **Firefox plutôt que Chrome** car Selenium permet d'y injecter facilement des extensions : on lance un Firefox vierge, puis `install_addon` installe au démarrage les fichiers `.xpi` (le format des extensions). bpc & uBlock deviennent alors actives.
Le module va permettre d'effectuer cette action via 3 fonctions.

Trois fonctions :

- `configurer_ublock()` — appelée une fois. uBlock ne marche pas tel quel : il faut activer des listes de filtres qui permettent de filtrer les cookies. On lit un fichier JSON au démarrage qui indique à uBlock quelles listes il doit activer.
- `ouvrir_firefox()` — ouvre un Firefox headless, installe les extensions, attend ~20 s qu'uBlock télécharge ses listes (une fois par session).
- `scraper(driver, url)` — vide les cookies (pour la reproductibilité), charge la page, attend ~8 s que le bypass agisse, lit le HTML.

P.S : La configuration d'uBlock et des extensions n'a lieu qu'une fois : les Firefox restent ouverts toute la durée du run. À chaque nouveau batch, on réutilise le même navigateur et on se contente de vider ses cookies, pour repartir d'un état propre. On désactive aussi les images, pour accélérer le chargement.

**[MAJ 22/07/2026]** Firefox n'est plus le passage obligé : il y a maintenant
**quatre moteurs**, choisis média par média dans
[`moteurs.py`](scraping/moteurs.py) — `basic` (simple requête HTTP, 20
médias), `firefox` (Selenium + bypass, 9), `log` (Firefox connecté à un compte
abonné, 2) et `hybride` (HTTP d'abord, Firefox en secours si l'article est
payant, telerama). Côté réglages Firefox : `pageLoadStrategy: eager`
(chargement médian 3,4 s → 0,8 s), `page_load_timeout` de 30 s, profils
temporaires en RAM (`/dev/shm`, ouverture ×3,5) et attente de 4 s au lieu de
8 (vérifié : 0 article bloqué). Détail dans « Pipeline v2 ».


### 3. `extraction.py` : Extraire les métadonnées et l'article du HTML

À l'étape précédente, on a obtenu le HTML brut de chaque article ; reste à en extraire le **titre, l'auteur, la date, la rubrique, l'accès libre/payant** et le **corps**. Problème : chaque journal range ça différemment.

Pour les métadonnées, la plupart des sites possèdent un JSON-LD (9/10) : un petit document qui contient la majeure partie des métadonnées, mais pas le corps de l'article. Dès qu'il est présent, il nous donne directement les métadonnées — c'est le cas idéal.

Sans JSON-LD, on doit explorer le corps du html, et dans ce cas on fait du cas par cas.

**Corps → HTML.** Le JSON-LD ne contient pas le texte complet ; on va le chercher dans la page via un sélecteur CSS propre à chaque journal. Trois familles :

| Famille | Médias | Conteneur |
|---|---|---|
| Classe sémantique propre | le_capital, le_figaro, le_monde, telerama, valeurs_actuelles, les_echos | `div`/`section` dédié |
| CMS « lmnr » partagé | le_journal_du_dimanche, paris_match | `div.rte` (règle commune) |
| Sans conteneur clair | nice_matin, le_nouvel_observateur | `<p>` dispersés, au cas par cas |

On réutilise encore le mécanisme de dictionnaire : comme chaque média peut avoir ses métadonnées et son article à un endroit différent, on fournit **un dictionnaire qui route chaque média**, en indiquant où lire les métadonnées et où trouver le corps. Par exemple pour Le Monde, on aura une ligne du genre :

```python
"le_monde": {"meta": "json_ld", "corps": ".article__content"}
```

`extraire(media, html)` lit ces deux indications et applique la bonne méthode ; seules les deux valeurs changent d'un média à l'autre. Seul le JDD fait exception : sans JSON-LD, ses métadonnées sont lues dans le HTML (`meta: corps`). Le sélecteur de chaque média est dans [`detail_metadonnees.md`](exploration/detail_metadonnees.md) (le fichier a suivi le ménage de `exploration/`).

**[MAJ 22/07/2026]** Le dictionnaire de routage compte aujourd'hui 32 médias
([`medias.py`](scraping/medias.py)), et le JSON-LD s'est confirmé comme la
règle : deux médias seulement (JDD, France-Soir) lisent leurs métadonnées dans
les balises. Deux ajouts au format des fiches : `corps: "json_ld"` quand le
JSON-LD contient aussi le texte de l'article (une dizaine de médias, plus
besoin de sélecteur CSS), et `secours` — des sélecteurs de repli titre/date
utilisés quand le JSON-LD laisse un champ vide (bfmtv, atlantico : ~8 % des
pages). Un sélecteur mal borné coûte cher : sur Le Monde, un corps trop large
attrapait les encarts « Lire aussi » et faisait échouer ~13 % des articles à
tort (corrigé le 11/07 en se limitant à `p.article__paragraph`).

### 4. `paywall.py` : Vérifier que le bypass a réussi

Une fois le corps de l'article extrait, il est temps d'analyser si l'article est complet, car le bypass ne marche pas à tous les coups. [`est_bloque(contenu)`](scraping/paywall.py) renvoie `True` si le contenu est vide, ou si une phrase-signal de troncature apparaît dans les **300 derniers caractères** (« il vous reste X % à découvrir », « réservé aux abonnés »…) — c'est là que ces messages se logent. Un article bloqué reçoit `etat=1` et n'est pas écrit.

Pour calibrer les signaux, on a comparé les pages avec et sans bypass. Trois comportements :

| Comportement | Médias |
|---|---|
| Bypass réussi | le_figaro, le_monde, telerama, les_echos |
| Paywall mou (texte déjà complet sans bypass) | le_journal_du_dimanche, le_capital, nice_matin, paris_match |
| Bypass échoué | le_nouvel_observateur *(non résolu)* |

**[MAJ 22/07/2026]** Le tableau ci-dessus est celui des 10 premiers médias. La
règle qui s'est imposée depuis, en re-sondant tout le monde : **on n'accepte
jamais un article tronqué**. Un média dont le paywall ne cède pas est soit
limité à ses articles gratuits (colonne `free`), soit scrapé avec un compte
abonné (le_monde, mediapart), soit écarté (L'Express, Le Point). Le
nouvel_observateur, lui, est repassé en bypass efficace. Un cas à retenir :
liberation est en pause parce que ses archives sont tronquées *côté serveur*
(~240 mots), donc invisibles pour `est_bloque` — le contenu manque sans qu'un
message de paywall l'annonce.

### 5. `stockage.py` : Écrire les résultats

[`stockage.py`](scraping/stockage.py) fait deux choses :

- `ecriture_csv(...)` extrait les métadonnées, passe le corps à `est_bloque`, et — si l'article est complet — ajoute une ligne au CSV du journal (`id, url, titre, auteur, date, section, free, contenu`). Renvoie l'état : `2` si écrit, `1` si bloqué.
- `maj_bdd(...)` met à jour l'`etat` de l'URL. (passage à 2 ou 1)

**[MAJ 22/07/2026]** `maj_bdd` pose aussi les états ajoutés depuis : `4` quand
une URL déjà en échec re-échoue (fin de parcours, deux tentatives maximum) et
`5` pour les URLs corrompues / non-articles, marquées à la main hors pipeline.
Les états 3 et 5 sont invisibles pour le pipeline comme pour le suivi.

### 6. `pipeline.py` : Orchestrer les batchs

[`pipeline.py`](scraping/pipeline.py) assemble le tout. Conçu pour tourner plusieurs jours sans surveillance :

1. **Ouverture** d'un Firefox par journal (en parallèle), gardés ouverts toute la durée du run.
2. **Boucle de batchs**, tant qu'il reste des `etat=0` : `new_batch()` → scraping parallèle → extraction, contrôle, écriture CSV, mise à jour des états → **un seul `commit` en fin de batch** (un batch = une transaction).
3. **Fin** quand il n'y a plus d'`etat=0` : on ferme les navigateurs.

Le commit par batch rend le run **reprenable** : si le script meurt, les URLs non commitées restent à `0` et sont reprises au lancement suivant. Une URL qui échoue finit à `etat=1`, sans faire tomber le batch.

**[MAJ 22/07/2026]** Cette boucle a été remplacée par le pipeline v2 : plus de
batch synchronisé (où tout le monde attendait le média le plus lent), mais un
thread par média qui prend son URL, la scrape, écrit, respecte son délai de
politesse et recommence. Le débit est passé de ~60 à **~280 URLs/min**. La
propriété de reprise est conservée (chaque URL est commitée à son terme), et
un média peut être mis en pause individuellement (`pause: True` dans sa
fiche) sans arrêter le run.

### Suivi du run

[`scraping/suivi.py`](scraping/suivi.py) lit la base et les CSV (en lecture seule) et expose des indicateurs en ligne de commande :

```bash
python -m scraping.suivi                    # vue d'ensemble
python -m scraping.suivi avancement         # URLs traitées par média
python -m scraping.suivi contenu le_monde   # longueur des articles
python -m scraping.suivi tendance           # page HTML du taux de réussite
```

Pour visualiser les données depuis le serveur, la sous-commande `tendance` écrit une page Plotly dans `data/tendance.html`. On la sert ensuite via un serveur HTTP local :

```bash
ssh gallica 'cd /data/elias/stage-mids && source .venv/bin/activate && python -m scraping.suivi tendance' \
  && scp gallica:/data/elias/stage-mids/data/tendance.html /tmp/tendance.html \
  && open /tmp/tendance.html
```

Puis ouvrir <http://IP_DU_SERVEUR:8000/tendance.html> dans un navigateur.

**[MAJ 22/07/2026]** `suivi.py` reste l'outil en ligne de commande, mais le
suivi au quotidien se fait maintenant par deux canaux plus confortables : le
**site de suivi** (chiffres régénérés chaque nuit par cron, cf. « Site de
suivi ») et le **dashboard local** `site/static/dashboard.html`, une page HTML
rafraîchie à la demande qui résume l'état des runs, des bases et des tâches en
cours. `suivi.py` a gagné `exporter_avancement()`, qui écrit le CSV
d'avancement lu par le site.

### Ajouter un nouveau média

1. Déposer `data/<nom_media>_articles.csv` (colonne `url`) sur le serveur.
2. Ajouter une entrée dans [`scraping/medias.py`](scraping/medias.py) :

```python
"nom_media": {"moteur": "firefox", "meta": {"strategie": "json_ld", "corps": "div.article-body"}},
```

`pipeline.py` charge les URLs au démarrage ; `3_creer_csv.py` crée le fichier de sortie. Pour trouver le bon sélecteur CSS, utiliser `exploration/recuperer_html.py`.

**[MAJ 22/07/2026]** La recette complète tient maintenant en quatre fiches de
configuration, sans écrire un script :

1. une fiche de **mapping** dans [`mapping/catalogue.py`](mapping/catalogue.py)
   (quelle méthode, quel motif d'URL) → produit le CSV d'URLs ;
2. `python -m scripts.verser_nouveaux <media>` verse ces URLs dans `urls.db` ;
3. une fiche de **scraping** dans [`medias.py`](scraping/medias.py) (moteur,
   attente, sélecteurs) ;
4. une fiche de **collecte news** dans
   [`sitemap_news.py`](scripts/sitemap_news.py) pour que le média continue de
   recevoir ses nouveaux articles chaque jour.

### Médias ajoutés

On a ajouté six nouveaux journaux au pipeline : Atlantico, La Dépêche, L'Opinion, Sud Ouest, Challenges et Le Télégramme. Tous ont un JSON-LD pour les métadonnées, et tous se cartographient via leur sitemap.

Nouveaux médias potentiels :
- Le Parisien (Wayback)
- L'Express (Ok, suffit de taper année/mois dans le sidebar)
- Marianne (Wayback)
- Atlantico (Ok) — MAJ : ✅ Ajouté
- L'Opinion (Ok) — MAJ : ✅ Ajouté
- La Tribune (Wayback)
- Challenges (Ok) — MAJ : ✅ Ajouté
- UsineNouvelle (Wayback)
- Le Nouvel Economiste (à l'air ok, mais présentation un peu spécial, à travailler)
- Journal Du Net (Ok, un peu spécial)
- Les Inrocks (Ok, un peu spécial)
- Charlie Hebdo (Ok, un peu spécial)
- Causeur (ok, mais la sitemap est ici :  https://www.causeur.fr/sitemap_index.xml)
- Esprit (Ok)
- Elle (Wayback)
- Connaissance des arts (Wayback)
- Science et Vie (Ok, un peu spécial)
- Sciences et Avenir (Ok)
- L'Equipe (Wayback)
- La nouvelle république (Ok, mais deux parties différentes sur les xml)
- Le Telegramme (Ok) — MAJ : ✅ Ajouté
- DNA (Wayback)
- L'Alsace (Wayback)
- EstRepublicain (Wayback)
- La Depeche (Ok) — MAJ : ✅ Ajouté
- SudOuest (Ok) — MAJ : ✅ Ajouté
- La voix du nord (Ok)
- Courrier Picard (à voir)
- L'Union (2023)

**[MAJ 22/07/2026]** Cette liste de repérage a été en partie consommée :

- **branchés depuis** : Le Parisien, Marianne et La Tribune (batch du
  06/07/2026), plus cnews et 20 Minutes issus de la prospection du 07/07 ;
  s'y ajoutent des titres qui n'étaient pas dans cette liste (Ouest-France,
  Midi Libre, BFMTV, La Croix, La Provence, Gala, Voici, Paris-Normandie,
  France-Soir, Mediapart) ;
- **écarté** : L'Express — le repérage disait « suffit de taper année/mois
  dans le sidebar », ce qui était vrai pour les URLs, mais 9 articles sur 10
  sont payants et sans corps récupérable ;
- **fiche de mapping écrite, pas branchés** : Le Progrès et Closer, évalués
  lors de la prospection du 07/07 ;
- **toujours des pistes** : Usine Nouvelle, Le Nouvel Économiste, Journal du
  Net, Les Inrocks, Charlie Hebdo, Causeur, Esprit, Elle, Connaissance des
  arts, Science et Vie, Sciences et Avenir, L'Équipe, La Nouvelle République,
  DNA, L'Alsace, L'Est Républicain, La Voix du Nord, Courrier Picard, L'Union.

La mention « (Wayback) » de plusieurs lignes est devenue moins dissuasive : la
méthode `CdxWayback` est maintenant une des cinq méthodes du catalogue de
mapping, donc un site sans sitemap exploitable ne demande plus de travail
spécifique.

### Batch de 15 nouveaux médias (06/07/2026)

Le mapping des 15 nouveaux médias est terminé : on a la liste complète des URLs
d'articles pour **Ouest-France, Midi Libre, Le Parisien, Libération, Le Point,
BFMTV, La Provence, La Croix, L'Express, Gala, Voici, Paris-Normandie,
La Tribune, France-Soir et Marianne** — environ 16,3 millions d'URLs au total.
Selon les sites, les URLs viennent des sitemaps, de la pagination des rubriques
ou des archives Wayback (La Provence, Le Point, La Tribune, Libération).

Sur ces 15, on sait déjà récupérer les articles de **8 médias**, validés sur du
HTML réel et couverts par des tests : Gala, Voici, BFMTV, Ouest-France,
Le Parisien, La Croix, La Provence et France-Soir. Tous passent par le moteur
basic (simple requête HTTP, sans navigateur), donc rapides à scraper.

Reste à configurer les 7 autres : Marianne, L'Express, Libération,
Paris-Normandie, Le Point, La Tribune et Midi Libre. Point notable : pour
La Tribune et Midi Libre, le bypass paywall ne débloque rien de plus que la
requête simple — leurs articles premium resteront tronqués.

### Moteur par média (06/07/2026)

Après avoir re-sondé aussi les anciens médias, on a fixé le moteur de chacun des
30 journaux configurés. Trois moteurs : **basic** (simple requête HTTP, la plus
rapide), **firefox** (Selenium + extension bypass paywall, pour les payants
contournables), **log** (Firefox connecté à un compte abonné). Le champ
`attente` fixe le temps par article : 6 s de chargement pour firefox, 1 s pour
log (validé : 1 s ne tronque pas), et 1 s de politesse pour basic (la requête
est instantanée, on temporise juste pour ne pas marteler le site).

| Moteur | Attente | Médias |
|---|---|---|
| basic | 1 s (politesse) | le_capital, challenges, l_opinion, la_depeche, le_journal_du_dimanche, gala, voici, bfmtv, ouest_france, leparisien, la_croix, laprovence, francesoir, marianne, midilibre, paris_normandie, latribune, liberation |
| firefox (bypass) | 6 s (chargement) | le_figaro, telerama, valeurs_actuelles, les_echos, paris_match, le_nouvel_observateur, nice_matin, atlantico, sud_ouest, le_telegramme |
| log (compte abonné) | 1 s (chargement) | le_monde, mediapart |

Soit 18 médias en basic, 10 en firefox et 2 en log.

On a mis de côté **L'Express** et **Le Point** : L'Express est quasi entièrement
payant sans corps d'article récupérable, et Le Point a trop d'URLs mortes (issues
des archives Wayback) et un article rendu en JavaScript, invisible sans navigateur.

**[MAJ 22/07/2026]** La répartition a bougé avec le pipeline v2 : un quatrième
moteur, **hybride** (requête HTTP d'abord, Firefox bypass seulement si
l'article sort tronqué), a récupéré telerama, dont la lenteur venait d'un
ralentissement ciblant l'empreinte Firefox. Les attentes ont été retestées :
4 s pour firefox (au lieu de 6, sans perte), 3 s pour log, 1 s de politesse
pour basic sauf latribune (2 s, rate-limit constaté). État actuel — 32 médias :

| Moteur | Attente | Médias |
|---|---|---|
| basic (20) | 1 s (latribune 2 s) | le_capital, la_depeche, l_opinion, challenges, le_journal_du_dimanche, gala, voici, bfmtv, ouest_france, leparisien, la_croix, laprovence, francesoir, marianne, midilibre, paris_normandie, latribune, liberation *(en pause)*, cnews, 20minutes |
| firefox (9) | 4 s | le_figaro, valeurs_actuelles, les_echos, paris_match, le_nouvel_observateur, nice_matin, atlantico, sud_ouest, le_telegramme |
| log (2) | 3 s | le_monde, mediapart |
| hybride (1) | 2 s | telerama |

*(Les pistes d'analyse notées ici — prénoms, TF-IDF, BERT, sauts intrinsèques
et extrinsèques… — ont été déplacées dans
[`paper/to_do.md`](paper/to_do.md), section « Pistes d'analyse notées en
juin-juillet 2026 », qui est devenu le seul endroit où vivent les tâches.)*

## Site de suivi

Mise en place d'un site de suivi du scraping avec **Evidence.dev** (dossier `site/`) : on écrit des pages en Markdown + SQL, Evidence en fait un site statique propre. Trois rubriques (menu latéral) : **Avancement** (URLs restantes par média, source `urls.db`), **Taux de réussite** (tableau + classement), **Évolution du taux de réussite** (graphe temporel avec sélecteur de médias), plus une page détail par média.

Hébergé sur **GitHub Pages** en mode *GitHub Actions* (build automatique à chaque push sur `main`, plus de branche `gh-pages`). Les données viennent de deux CSV versionnés dans `site/sources/suivi/` : `suivi_journal.csv` (copié depuis `data/`) et `avancement.csv` (généré par `exporter_avancement()` depuis `urls.db`). Un **cron quotidien** (`scripts/maj_csv_suivi.sh`, 4h) rafraîchit ces CSV et pousse sur `main` → le site se reconstruit seul.

Site : <https://corto2corto.github.io/stage-mids/>

**[MAJ 22/07/2026]** Le site a gagné deux rubriques et un compagnon local :

- une page **Collecte des sitemaps** (11/07), qui trace les nouvelles URLs
  trouvées à chaque passage du cron — détail dans « Suivi de la collecte des
  sitemaps sur le site » ;
- la page d'accueil **Avancement** est désormais alimentée par
  `avancement.csv`, généré depuis `urls.db` par `exporter_avancement()` ; le
  cron de 4h régénère les deux CSV (journal + avancement) et ne pousse que
  s'ils ont changé. Le site couvre les 31 médias branchés, contre 16 au
  départ ;
- un **dashboard local** `site/static/dashboard.html` (12/07, sorti du suivi
  git le 19/07 : il n'est plus publié) : une page HTML unique, mise à jour à
  la demande, qui rassemble ce que le site ne montre pas — avancement du
  mémoire, runs serveur en cours, état des bases, tâches en attente.

## Bases de données n-grammes

Une fois un corpus scrapé, on veut pouvoir suivre l'évolution de l'usage des mots dans le temps (livrable de la Phase 1, avant les modèles de rupture). Pour chaque journal, on construit donc une base de comptage n-grammes (uni/bi/trigrammes) par jour, à partir de son corpus d'articles.

### Tokenisation

Avant de compter, chaque article est découpé en phrases, pour qu'un bigramme ou un trigramme ne chevauche jamais deux phrases. On fait attention à ne pas couper les abréviations comme « M. » ou « U.S.A. » — un vrai point final après un mot d'une seule lettre majuscule reste un cas limite, accepté tel quel.

### Structure

Chaque journal a sa propre base : un comptage des uni/bi/trigrammes par jour, accompagné du total de mots du jour pour pouvoir calculer des fréquences relatives. Un filtre écarte les n-grammes trop rares (vus moins de 10 fois sur tout le corpus), pour garder des bases plus légères.

### Résultat (02/07/2026)

| Base | Taille | Couverture |
|---|---|---|
| Le Figaro | 11 Go | 2004-12-17 → 2024-03-01 |
| Les Échos | 8,3 Go | 1991-01-02 → 2024-10-20 |
| Le Monde | 30 Go | reconstruction en cours |

**[MAJ 22/07/2026]** La base Le Monde est terminée, et c'est elle qui porte
toute la suite du mémoire (phases 2 et 3). État actuel :

| Base | Taille | Couverture | Jours de parution |
|---|---|---|---:|
| Le Monde | 59 Go | 1944-12-19 → 2025-12-31 | 26 917 |
| Les Échos *(sans filtre)* | 12,6 Go | 1991-01-02 → 2025-04-02 | 10 395 |
| Le Figaro | 10 Go | 2004-12-17 → 2024-03-01 | 6 764 |
| Les Échos *(filtrée, ancienne)* | 8,2 Go | 1991-01-02 → 2024-10-20 | 10 381 |

Deux évolutions par rapport à la description ci-dessus :

- **le filtre « vu moins de 10 fois » est abandonné**. Il faisait disparaître
  précisément les mots rares qui nous intéressent pour la détection de
  ruptures. Coût mesuré sur Les Échos, reconstruits sans filtre : ×1,5 sur la
  taille (8,2 → 12,6 Go), ce qui est supportable ;
- chaque corpus a en plus une **base de tops** (`<corpus>_top.db`, reconstruite
  d'un bloc) : les 500 premiers uni/bi/trigrammes par jour, mois et année, avec
  un drapeau `stop` sur les mots outils — c'est ce que sert l'API.

La **mise à jour quotidienne** ([`maj_ngram.py`](scripts/maj_ngram.py)) est
écrite et validée — elle ne recompte que les articles nouveaux du CSV du média,
par paquets validés en une transaction, l'API continuant de servir pendant
l'écriture — mais elle n'est pas encore branchée en cron : restent à trancher
la mise à jour incrémentale des tops et le rattrapage de l'existant.

### Étape suivante

- Normalisation : famille de mots via Spacy (lemmatisation/REN), garder les 50K unigrammes les plus intéressants

## Détection de spikes et histogrammes

Pour repérer les moments où un mot apparaît anormalement souvent, on utilise
`exploration/detecter_spike.py`. Le principe : toutes les fréquences passées du
mot forment sa distribution « habituelle », et une fenêtre qui dépasse le
quantile haut (99 % par défaut) est considérée comme un extrême. Sur le
serveur, depuis la racine du projet :

```bash
python -m exploration.detecter_spike lemonde inflation
python -m exploration.detecter_spike lemonde inflation 0.995 2,3,4
```

Les arguments, dans l'ordre : le corpus (`lemonde`, `lefigaro`, `lesechos`),
le mot, puis en option le quantile et les tailles de fenêtres en jours. Le
script liste les fenêtres au-dessus du seuil et enregistre une figure par
échelle dans `exploration/figures/` : à gauche, la fréquence du mot au fil du
temps avec les spikes en rouge ; à droite, l'histogramme de ces fréquences —
la densité empirique du mot — avec le seuil en pointillé qui sépare le régime
habituel des extrêmes.

**[MAJ 22/07/2026]** Ce script est un brouillon dépassé : le seuil par
quantile empirique (« les 1 % de jours les plus chargés ») dit seulement qu'un
jour est dans le haut du panier, pas qu'il est *surprenant*. Il a été remplacé
par le module [`rupture/`](rupture/), qui ajuste une loi au mot et donne une
p-valeur à chaque jour — cf. « Fiche statistique d'un mot » puis « Phase 2 ».
Le dossier `exploration/figures/` n'existe plus : les figures sont produites à
la demande par le skill `/fiche-mot` et par les rapports de
`paper/donnees_maths/`.

## Pipeline v2 : un rythme par média (07/07/2026)

Le pipeline en batchs synchronisés (chaque batch attendait le média le plus lent
avant de repartir) est remplacé par **une boucle indépendante par média** : un
thread par média — prendre sa prochaine URL en base, scraper, écrire, respecter
son attente, recommencer. Un site lent ne ralentit plus que lui-même. Débit
mesuré : **~280 URLs/min** contre ~60 avant (serveur chargé), jusqu'à ×10 sur
les médias à problème.

Réglages actés après tests A/B :

- `pageLoadStrategy: eager` (page « prête » au DOM, sans attendre pubs et
  traqueurs) : chargement médian firefox 3,4 s → 0,8 s ;
- `page_load_timeout` 30 s (couper plus court fait perdre des articles, testé
  à 6/10/14 s) ;
- politesse basic 1 s (latribune 2 s : rate-limit constaté), firefox 4 s
  (bypass BPC vérifié : 0 bloqué à 4 s), log 3 s ;
- `urls.db` en WAL : plus aucun « database is locked » entre threads, coût
  base ~2 ms par URL ;
- logins le_monde/mediapart ouverts **avant** le lancement groupé des Firefox :
  une seule tentative de connexion par run ;
- profils temporaires Firefox en RAM (`/dev/shm`) : ouverture ×3,5 ;
- nouveau moteur **hybride** (requête HTTP d'abord, Firefox bypass si payant),
  pour les sites qui ne ralentissent que les navigateurs — prototype telerama :
  2-3 → ~12-15 URLs/min, politesse 2 s.

### Les états d'une URL dans `urls.db`

Chaque URL de la base porte un état, qui raconte sa vie dans le pipeline :

| État | Sens | Qui le pose |
|---|---|---|
| 0 | à scraper | le chargement des corpus |
| 1 | échec, **retentable** | le pipeline |
| 2 | scrapée avec succès | le pipeline |
| 3 | déjà couverte par le corpus historique | le script de dédup (hors pipeline) — 6,5 M d'URLs pour le_monde/le_figaro/les_echos |
| 4 | échec **confirmé** (retentée, re-échouée) | le pipeline |
| 5 | **corrompue / non-article** (vidéo, galerie, artefact, page de service) | à la main |

Le pipeline sert chaque média dans cet ordre : d'abord toutes les nouveautés
(état 0), puis — quand il n'y en a plus — une **seconde chance** aux échecs
(état 1). Un échec qui re-échoue passe en état 4 et n'est plus jamais repris :
chaque URL a droit à deux tentatives au maximum, ce qui évite de marteler à
l'infini les payants et les pages mortes. Les états 3 et 5 sont invisibles
pour le pipeline comme pour le suivi (ni succès, ni échec : hors périmètre).

### Run de validation (nuit du 6 au 7 juillet 2026)

2 h sur 48 500 URLs tirées au hasard, 30 médias : **29 236 articles**, 0 blocage
base, 0 thread mort, cohérence CSV↔base parfaite, reprise propre après un
`kill -9` (au plus 1 doublon par média, absorbé par le marquage des doublons).
Le rapport détaillé (`exploration/rapport_test_nuit.md`) a été supprimé au
ménage de `exploration/` : ses conclusions sont celles résumées ici et dans
« Décisions médias ».

### Décisions médias

- **liberation en pause** : les archives sont tronquées côté serveur (~240
  mots), y compris dans le JSON interne des pages — reprise prévue avec un
  compte abonné.
- **bfmtv** : 159 601 replays/podcasts retirés du corpus d'URLs (17 %, ce ne
  sont pas des articles) ; repli titre/date sur les balises quand le json-ld
  est incomplet (idem atlantico).
- telerama, le_figaro, nouvel_obs : leur lenteur venait d'un ralentissement
  ciblant l'empreinte Firefox (servis en <1 s en HTTP simple) — d'où le moteur
  hybride.
- **le_monde en pause (09/07)** : le login abonné passe mais le contenu reste
  inaccessible (~99,6 % d'échec, mesuré sur ~500 reprises) ; ses 53 874 URLs
  retentables (état 1) ont été basculées en état 4 pour ne plus les marteler.
  Corrige au passage un angle mort de [`batch.py`](scraping/batch.py) : un média
  sans aucun état 0 sortait de `new_batch`, ses états 1 n'étaient donc jamais
  retentés (désormais `WHERE etat IN (0,1)`). Reste un filet de news du jour à
  écarter côté `medias.py` pour une pause complète.

**[MAJ 22/07/2026 — le_monde débloqué]** La pause a été levée le 11/07. Le
scraping du Monde passe par un **compte abonné** (moteur `log` : Firefox
ouvre une session connectée avant le run, cf.
[`connexion.py`](scraping/connexion.py)), et non plus par l'extension de
bypass, qui échouait systématiquement sur ce site. Le login fonctionnait
d'ailleurs déjà lors du diagnostic du 09/07 : les ~99,6 % d'échec ne venaient
pas de l'accès mais de la lecture — le sélecteur de corps ramassait les
encarts « Lire aussi » et leur mention « Article réservé aux abonnés », que
`est_bloque` prenait pour un paywall. Corps restreint aux vrais paragraphes
(`p.article__paragraph`), puis rejeu des échecs : **21 852 articles récupérés,
37 échecs résiduels, plus aucune URL en attente**. Le Monde est le corpus sur
lequel s'appuient les phases 2 et 3 du mémoire.

### Prospection de nouveaux médias

Quatre candidats évalués par équipes d'agents (dossiers de prospection dans
`exploration/prospection/`, scripts de mapping écrits et testés, **rien de
branché** — validation à venir ; ces dossiers ont depuis été supprimés, leurs
conclusions tenant dans le tableau ci-dessous et leurs scripts étant devenus
des fiches de [`mapping/catalogue.py`](mapping/catalogue.py)) :

| Média | Verdict | Profondeur |
|---|---|---|
| cnews (Bolloré) | basic complet | 2012→2026, ~195 000 articles |
| 20minutes (Rossel/Ouest-France) | basic complet | 2006→2026, ~500-800 000 |
| leprogres (EBRA) | gratuits seuls (filtre `free`) | 2018→2026, part de gratuit à sonder |
| closermag (Reworld) | sous réserve | 2009→2026, texte des vieux articles effacé par le site en 2023 — frontière à sonder |

À noter pour le mémoire : le cas closermag documente une **destruction
d'archives éditoriales après rachat** (Reworld a vidé le corps des anciens
articles en gardant URL et titre).

## Collecte quotidienne des sitemaps (08/07/2026)

Jusqu'ici le corpus d'URLs était figé : chaque média avait été cartographié une
fois (section « Pagination »), puis plus rien. Or les journaux publient tous les
jours. On branche donc une collecte quotidienne qui alimente `urls.db` toute
seule, sans reconstruction. Deux briques, chacune réexécutable sans risque
(déduplication, jamais de réécriture) :

- [`sitemap_news.py`](scripts/sitemap_news.py) : chaque média expose un
  *sitemap news* qui ne liste que ses articles récents (fenêtre ~48 h). On le
  lit et on ajoute au CSV d'URLs du média les liens qui y manquent. La config
  vient de la reco des `robots.txt` des médias (07/07) ; quelques cas
  particuliers : sous-sitemaps à développer (ouest_france, leparisien), CDN qui
  bloque l'empreinte TLS de `requests` → `curl` (les_echos, le_telegramme),
  anti-bots stricts → empreinte Chrome de `curl_cffi` (nice_matin, jdd,
  sud_ouest).
- [`verser_nouveaux.py`](scripts/verser_nouveaux.py) : verse ces URLs en
  base en `INSERT OR IGNORE`, l'index unique `(media, url)` écartant les déjà
  connues. Idempotent : reverser deux fois ne crée aucun doublon.

Le tout est enchaîné par [`cron_sitemaps.sh`](scripts/cron_sitemaps.sh), lancé
2×/jour (07 h 40 et 19 h 40). Un `flock` empêche deux cycles concurrents ; comme
la fenêtre news fait ~48 h, un cycle raté est rattrapé le lendemain.

### Rattrapage des anciens médias

Les médias cartographiés en mai-juin puis mis en pause avaient un trou entre la
fin de leur mapping et le branchement de la collecte news.
[`rattrapage_sitemaps.py`](scripts/rattrapage_sitemaps.py) le comble en
one-shot : il reparcourt les sitemaps d'articles de chaque média mais ne
télécharge que les sous-sitemaps susceptibles de couvrir mars 2026 →
aujourd'hui (via le `lastmod` de l'index, sinon la date dans l'URL du
sous-sitemap), puis ajoute au CSV les URLs manquantes. Même garantie :
réexécutable, base intacte.

Bilan : le corpus de scraping n'est plus un instantané, il grossit chaque jour.

## Fiche statistique d'un mot : Poisson vs binomiale négative (10/07/2026)

Premier livrable « maths » du mémoire, demandé par le tuteur : avant les modèles
de rupture, poser proprement le modèle de comptage d'un mot au fil du temps.
Support : [`paper/donnees_maths/rapport.qmd`](paper/donnees_maths/rapport.qmd)
(→ `rapport.pdf`), sur six mots dans Le Monde, 2020-2024 (grille complète de
1 827 jours, un jour sans occurrence compte 0). Cela prolonge la section
« Détection de spikes et histogrammes » en lui donnant un modèle explicite.

### Modèle

Pour chaque jour $t$ : $X_t$ occurrences du mot, $N_t$ mots publiés ce jour-là,
fréquence $f_t = 10^5 \cdot X_t / N_t$. On modélise le comptage $X_t$ en
normalisant la moyenne par l'exposition $N_t$ :

- **Poisson** $X_t \sim \mathcal{P}(\lambda N_t)$ — un seul paramètre,
  moyenne = variance ;
- **binomiale négative** $X_t \sim \mathrm{NB}(\mu N_t,\ r)$ — un paramètre de
  forme $r$ en plus, qui autorise la surdispersion (variance > moyenne).

$\lambda$ a une forme fermée au maximum de vraisemblance ; $\mu$ et $r$ sont
estimés par `statsmodels`. Résultat net : $\hat\lambda \approx \hat\mu$ partout,
mais la NB colle bien mieux aux histogrammes — les séries de mots sont
sur-dispersées, Poisson sous-estime les gros jours.

### Jours anormaux

Sous la NB ajustée, chaque jour a une p-valeur (probabilité d'observer au moins
$X_t$ occurrences). Au seuil $p_t < 10^{-4}$, dix jours ressortent sur les six
mots, tous rattachables à un événement : second tour de la présidentielle 2022,
assaut du Capitole, COP26/27, annonce de l'« indemnité inflation », invasion de
l'Ukraine, discours et censures des gouvernements Borne et Barnier.

### Ce qu'on en retient

Les six mots couvrent trois régimes ; on propose d'en garder un par régime pour
la suite :

| Mot | Régime | Intérêt |
|---|---|---|
| *président* | fréquent, quasi-Poisson ($\hat r \approx 18$) | cas de référence, pics nets et interprétables |
| *inflation* | rare, très surdispersé ($\hat r \approx 1$) | Poisson échoue ; niveau qui change durablement → *outlier* vs rupture |
| *guerre* | rupture brutale (février 2022, $\hat r \approx 3{,}6$) | la fréquence change d'échelle sans jamais redescendre |

Point important pour la suite : *guerre* ne déclenche que deux jours anormaux
alors que sa série change complètement d'échelle en février 2022. La rupture
durable « élargit » la NB ajustée, qui absorbe le choc au lieu de le signaler.
**La détection de pics jour par jour ne voit pas les changements de régime** —
c'est précisément ce qui motive le passage aux modèles de rupture (breakpoints),
cœur de la phase suivante. *économie* et *climat* sont des régimes
intermédiaires, redondants avec les trois retenus.

### Outillage

- Route API [`/fiche`](api/app.py) (`?mot=&corpus=&from=&to=`) : renvoie les
  ajustements, les p-valeurs, les pics et les moments d'un mot ; nouvel onglet
  « Fiche d'un mot » dans le front.
- Skill `/fiche-mot` : génère à la demande la page PDF d'un nouveau mot (série +
  pics, histogramme vs lois, p-valeurs, moments), sur le modèle du rapport.

## Nettoyage des URLs non-articles (11/07/2026)

Le chargement des nouveaux médias a embarqué des URLs qui ne sont pas des
articles. Découvert sur latribune : ~29 000 fragments Wayback
(`width=1200`, `format=auto`, images `height=675/…jpg`, `&` final) que le site
**résout vers l'article réel** — chaque fragment capturé écrivait donc un
doublon dans le CSV (~13 % du fichier, certains articles en triple).

- **latribune** : CSV dédoublonné par identifiant d'article (15 899 lignes
  supprimées, 90 378 articles conservés, sauvegarde dans `data/backup/`) ;
  29 228 URLs à fragments passées en état 4, purgées aussi du CSV d'URLs.
- **Audit des 29 médias** (agent, lecture seule) : ~242 300 URLs non-articles,
  toutes en état 0/1 — rien n'avait encore pollué les CSV. Le gros du stock :
  le sous-domaine `video.lefigaro.fr` (~234 000 pages vidéo) et les
  `/galeries-photos/` du Nouvel Obs (~8 150).
- **le_figaro** : les 233 946 URLs `video.lefigaro.fr` passées en **état 5**,
  dont le sens est précisé : *URL corrompue / non-article*, corpus de référence
  pour construire les futurs filtres en amont du mapping.
- Leçon de l'audit : les mots `video`, `podcast`, `rss`, `auteur`… abondent
  dans des slugs d'articles légitimes (« jeu-video », « urssaf », « l-auteur »).
  Un filtre fiable porte sur un **sous-domaine, un segment de chemin ou une
  extension** — jamais sur la présence d'un mot. L'inspection média par média
  qui en tirera une règle par média est notée dans les tâches en attente.

## Suivi de la collecte des sitemaps sur le site (11/07/2026)

Le site de suivi gagne une page **Collecte des sitemaps** : une barre par
jour (bleu = passage du matin 5h40 UTC, orange = après-midi 17h40, empilés)
des nouvelles URLs trouvées, et un tableau du détail par passage.

- [`sitemap_news.py`](scripts/sitemap_news.py) consigne désormais chaque
  passage dans `data/suivi_sitemaps.csv` (un relevé par média : URLs vues,
  ajoutées) ;
- [`maj_csv_suivi.sh`](scripts/maj_csv_suivi.sh) copie ce journal vers les
  sources du site (`sitemaps_journal.csv`), publié par le commit quotidien
  de 4h — la page se complète donc chaque matin avec la veille ;
- historique reconstruit depuis le log du cron (7 passages depuis le
  08/07/2026, totaux vérifiés contre les lignes « Terminé » du log), versé
  dans le CSV du site et dans `data/suivi_sitemaps.csv` sur le serveur pour
  que les prochains passages s'y ajoutent à la suite.

Vocabulaire de la page : « URLs listées » = tout ce que les sitemaps news
affichent au passage (fenêtre glissante ~48 h, les mêmes articles
réapparaissent d'un passage à l'autre) ; « Nouvelles » = les URLs jamais
vues, celles qui rejoignent la file de scraping — c'est ce que trace le
graphique.

## Inspection des URLs non-articles : règles par média (12/07/2026)

L'inspection média par média annoncée le 11/07 est faite. Chaque règle a été
validée sur échantillons (requêtes indexées + sondes HTTP avec la vraie chaîne
d'extraction) avant tout marquage, avec le principe convenu : au moindre doute
on garde — un faux article ne coûte qu'un échec de scraping, un vrai article
écarté ne se rattrape pas.

- **417 870 URLs passées en état 5** (non-articles) sur 11 médias : pages vidéo
  (`video.lefigaro.fr` 233 946, `/internal/` des Échos 2 024), résultats
  d'élections/podcasts/lives du Monde (107 708), artefacts Wayback latribune
  (29 228, migrés de l'état 4), diaporamas et fiches challenges (21 903),
  pages de navigation et corps perdus côté site l_opinion (14 556), galeries
  photos nouvelobs (8 157), sommaires JDD (220), artefacts laprovence (123),
  URLs malformées telerama/ouest_france (5).
- **Tout est réversible** : chaque marquage a sa sauvegarde (media, id, url)
  dans `data/backup/` — `etat4_vers_5_20260711.csv`,
  `non_articles_vers_5_20260712.csv`, `le_monde_etat4_avant_tri_20260711.csv`.
  Un UPDATE depuis ces fichiers remet tout en l'état.
- **Gardés après test** (ne pas re-proposer) : les 1 885 871 slugs à markup
  `span` du Télégramme — zéro doublon par ID d'article sur les 4,6 M d'URLs du
  média, 48 763 déjà scrapés avec succès, donc vrais articles uniques ; les
  pages `video-` de gala/voici/valeurs_actuelles/francesoir (vrais articles,
  gala sondé à ~262 mots) ; les slugs `http--` d'atlantico (motif non fiable).
- Référence : [`exploration/regles_non_articles.md`](exploration/regles_non_articles.md)
  (règles appliquées, règles écartées, motifs à bloquer en amont) ; l'état 5
  est documenté dans [`scraping/stockage.py`](scraping/stockage.py).

## Branchement de cnews et 20minutes (15/07/2026)

Deux médias de la prospection du 07/07 entrent en production, tous deux 100 %
gratuits en moteur basic : **cnews** (json-ld, corps `div.article-body`) et
**20minutes** (corps json-ld).

- **Rattrapage avant versement** — les mappings sont désormais relançables :
  `mapping_cnews.py` passe en append+dédup (re-balayage obligatoire, sitemap
  non trié par date) et `mapping_20minutes.py` prend les années
  en argument. *(Ces deux scripts n'existent plus : ils ont été absorbés le
  21/07 par [`mapping/catalogue.py`](mapping/catalogue.py), où ils sont
  devenus une fiche `SitemapPagine` et une fiche `ArchivesParJour`.)* cnews : +562 URLs (fenêtre 07→14/07) → **357 990**. 20minutes :
  +18 996 URLs 2026, puis un **trou 2022-2025 découvert par l'audit** (le
  mapping du 07/07 s'était interrompu à 2021 sans le signaler) et comblé dans
  la foulée (+140 560) → **839 923**, corpus continu 2006-2026.
- **Audits par agents avant versement** (lecture seule) : 0 doublon et 100 %
  au format article des deux côtés ; aucune fuite des exclusions
  vidéo/podcast/émission/diaporama de cnews ; les rubriques d'apparence
  douteuse (podcast, tv, guide-achat, horoscope, `videos` de 20minutes) sont
  de vrais articles sondés (json-ld + corps). Reste un choix éditorial à
  trancher un jour : le publi-rédactionnel (`le-corner-partenaires` cnews,
  756 URLs ; `publicommunique` 20minutes, ~31) — gardé pour l'instant, même
  logique que le `a-propos` du Progrès. ~1 700 `/index/` 2006-2007 de
  20minutes sont mortes (redirection accueil) : échecs propres à prévoir.
- **Extraction validée sur articles frais** : cnews 3/3 (362-488 mots),
  20minutes 2/3 + 1 « direct » (`LiveBlogPosting`) vide → échec propre attendu.
- **Versement** : sauvegarde `urls.db.bak-20260714-225135` (13,2 Go, VACUUM
  INTO), puis `verser_nouveaux cnews 20minutes` : **1 197 913 URLs insérées**
  (357 990 + 839 923, zéro écartée), scrapping mis en pause pendant
  l'opération puis relancé.
- Les deux rejoignent la collecte news quotidienne
  ([`sitemap_news.py`](scripts/sitemap_news.py)) : 20minutes via son
  `sitemap-news.xml` (~48 h), cnews via le `googlenews.xml` déclaré dans son
  robots.txt (~5 jours, via_cffi car Cloudflare bloque curl — la reco du
  07/07 l'avait raté pour ça, `/videos/` exclues). Plus aucun média branché
  sans source de nouvelles URLs, sauf francesoir.

## Phase 2 — détection des pics revue : mélange Bernoulli × NB (20/07/2026)

La phase 2 du mémoire (classification des sauts) demande un gros dataset de
pics : pour chaque couple (mot, jour anormal), une fenêtre de la série sur
±15 jours, destinée à une PCA (« modèle zéro »). Nouvelles briques dans
`rupture/` (série → pics → fenêtres), testées d'abord sur quelques mots
2020-2024, puis sur 10 mots sur toute la profondeur de la base Le Monde
(1944-2025, 26 917 jours de parution).

### Ce que les tests ont montré

- La période longue démultiplie les pics : chômage passe de 2 pics
  (2020-2024) à 21, guerre de 2 à 148. Le volume visé (~100 000 fenêtres sur
  10 000 mots) est atteignable sans toucher au seuil.
- Le nombre de pics varie fortement selon les mots (guerre 148, chirac 25).
  Arbitrage de Simon : c'est *by design*, le seuil fixe $10^{-4}$ est
  objectif ; pas de règle de proportion, Benjamini-Hochberg noté pour plus
  tard, double fit (retirer les outliers évidents puis réajuster) validé.
- **Le vrai problème : les zéros structurels.** covid a 92 % de jours à
  zéro (le mot n'existe pas avant 2020). Une NB unique doit couvrir à la
  fois les zéros et les explosions ; son seul bouton est de gonfler sa
  variance ($\hat r = 0{,}02$) : elle devient une « loterie » qui s'attend à
  tout, plus rien n'est surprenant, zéro pic détecté. Piège de diagnostic :
  cette loi n'est pas rejetée par le χ² (χ²/ddl = 0,49 — loi *trop large*,
  invisible pour un test unilatéral).

### La réponse : le mélange Bernoulli × NB décalée (décision Simon, vocal du 20/07)

Deux questions séparées au lieu d'une loi unique : « le mot apparaît-il
aujourd'hui ? » (Bernoulli, probabilité $p_0$ d'un jour à zéro) et
« sachant qu'il apparaît, combien de fois ? » (NB ajustée sur $X_t - 1$,
jours actifs seulement). La raison profonde du succès : **l'estimation se
sépare** — les jours à zéro n'informent que $p_0$, les jours actifs
n'informent que la loi de comptage. Les décennies de silence ne contaminent
plus le fit, et la surprise redevient « surprenant par rapport aux jours où
le mot vit », pas par rapport à une moyenne diluée par l'absence.

### Validation sur 20 mots (`paper/donnees_maths/fiches_bnb.pdf`)

Trois lois comparées (Poisson, NB, Bern-NB) sur la série complète : χ² de
Pearson jour par jour, résidus, moments, histogrammes.

- Mots sans zéros (guerre, gouvernement, président…) : Bern-NB ≈ NB, rien
  ne change — la nouvelle loi ne coûte rien.
- Mots à zéros (ukraine 74 %, sida 70 %, cancer 52 %…) : χ²/ddl s'améliore
  nettement (ukraine 1,63 → 1,25).
- **internet, le cas démonstratif** : la NB dégénérée ne voyait que 4 pics ;
  Bern-NB en trouve 24, qui dessinent la bulle internet 1999-2001. La
  détection sur les néologismes à vie stable est débloquée.
- **covid : réparé à moitié.** Le fit devient sain (χ²/ddl 0,49 → 1,04,
  quasi idéal) mais toujours 0 pic : sa période active est elle-même une
  vague géante (2020-21 puis décrue), jamais un régime stable. Limite
  restante et identifiée : ces mots-là relèvent de l'étape 4 (modèle
  autorégressif — un « normal » qui bouge avec le temps).
- **Piège méthodologique découvert** : le test du χ² est unilatéral, il ne
  rejette que les lois trop étroites. La NB-loterie de covid (χ²/ddl = 0,49)
  ou d'internet (0,65) ressortait « non rejetée » tout en étant fausse — une
  loi trop *large* passe entre les mailles. Juger sur le ratio (≈ 1 idéal),
  jamais sur le verdict seul.
- **Angle mort restant** : Chirac et Mitterrand sont mal ajustés sous les
  trois lois (χ²/ddl ≈ 2,4-2,8). Leur problème n'est pas les zéros mais la
  dérive séculaire de leur fréquence (carrière politique), et leurs zéros
  sont concentrés dans les époques creuses alors que la Bernoulli suppose
  $p_0$ constante. Deuxième argument pour l'étape 4.
- Total des pics sur les 20 mots : 905 (NB) → 781 (Bern-NB). Baisse saine :
  les pics perdus ne devaient leur surprise qu'à la dilution par les zéros,
  les pics gagnés (internet) sont réels.
- Reste à trancher avec Simon : la convention de p-valeur sous le mélange
  (plafonnée à $1-p_0$ pour les jours actifs) ou conditionnelle aux jours
  actifs — ça change les comptages des mots très zéro-inflatés.

### Outillage

- Route [`/fiche`](api/app.py) : troisième ajustement ajouté, purement
  additif ($p_0$, $\mu_b$, $r_b$, p-valeurs `p_bnb`, `pics_bnb`,
  `adequation.bnb`, densité et moments) — le front existant est intact.
- [`fiches_bnb.py`](paper/donnees_maths/fiches_bnb.py) → `fiches_bnb.pdf`
  (synthèse + une page par mot) + CSV récapitulatif machine.
- Prochaine étape : câbler la Bern-NB dans les briques `rupture/`, puis la
  NMS (dédoublonnage des fenêtres qui se recouvrent).

## Double fit Bern-NB : purger les outliers avant de réestimer le bruit (20/07/2026)

Suite du mélange Bernoulli × NB : la loi de fond reste estimée sur *tous* les
jours actifs, y compris les pics eux-mêmes, qui la tirent vers le haut et la
rendent trop tolérante — des pics plus modestes mais réels passent alors
inaperçus. Le double fit (validé par Simon) corrige ça : ajuster la Bern-NB,
retirer les jours « évidents » ($p_t$ sous un seuil très strict), réajuster la
NB sur le reste (le bulk), recalculer toutes les p-valeurs sous cette loi
purifiée. Testé sur 20 mots, 26 917 jours (1944-2025) —
[`paper/donnees_maths/double_fit.qmd`](paper/donnees_maths/double_fit.qmd).

- Le double fit **ajoute toujours** des pics (+4 % à +13 % selon le seuil),
  n'en retire jamais, et laisse intacts les mots sans jours extrêmes. Les
  pics gagnés correspondent à de vrais événements (réforme des retraites,
  fin de la Seconde Guerre mondiale, mort de Chirac…) — pas un artefact.
- Une version itérée (retirer/réajuster en boucle jusqu'à convergence)
  gagne peu par rapport à un seul tour : retenu pour la suite, **un tour au
  seuil $10^{-6}$**.
- Limite confirmée : covid reste à 0 pic, ses outliers formant une ère
  entière plutôt que des jours isolés — hors de portée du double fit,
  toujours du ressort de l'étape 4 (modèle autorégressif).

## Le mapping regroupé en un module (21/07/2026)

Le *mapping*, c'est l'étape qui dresse, pour chaque journal, la liste de
toutes les URLs de ses articles — le point de départ, avant de les scrapper.
Comme chaque site a sa structure, cette étape avait accumulé une quinzaine de
scripts éparpillés dans `exploration/`, un par journal, qui se ressemblaient
beaucoup : même plomberie, seule la façon de dénicher les URLs changeait.

Tout est désormais réuni dans un module [`mapping/`](mapping/), bâti comme
[`scraping/`](scraping/) : d'un côté **les méthodes** (le code commun, dans
[`generique.py`](mapping/generique.py)), de l'autre **la configuration** (une
fiche par journal dans [`catalogue.py`](mapping/catalogue.py)). Ajouter un
journal revient à écrire une fiche, plus un script à maintenir.

- **Cinq méthodes** couvrent tous les cas rencontrés : sitemap indexé,
  sitemap paginé, pagination HTML, archives jour par jour, et l'API
  d'archives de la Wayback Machine (pour les sites verrouillés, type
  DataDome, inaccessibles autrement). Les dix scripts par journal se sont
  résorbés dans ces cinq méthodes, chaque particularité devenant une option
  de fiche.
- **Sécurité des données** : la sortie passe en *ajout + déduplication* — on
  n'ajoute au CSV que les URLs manquantes, sans jamais réécrire l'existant.
  Une reprise après interruption ne perd rien, et deux mappings peuvent
  nourrir le même fichier (ex. Libération récent via son sitemap + ses
  archives via la Wayback).
- Bilan : 18 fichiers ramenés à 6, validés par 52 tests rapides sur le
  serveur (chacun écrivant dans un dossier temporaire) ; les 34 CSV de
  production sont restés intacts à l'octet près.

Au passage, le pipeline quotidien (collecte des sitemaps *news*) a quitté
`exploration/` pour [`scripts/`](scripts/) : ces fichiers tournent tous les
jours par cron, ils n'avaient pas leur place dans un dossier d'essais.

## Phase 3 — gros vocabulaire : règle d'absorption des graphies (21/07/2026)

Le dataset de sauts démarre sur les unigrammes du Monde : recensement complet
de la base (441 081 mots, 3 min 20 — `exploration/scan_vocab_lemonde.py`),
exclusions (mots outils, tokens numériques ou d'une seule lettre), puis
**top-10 000 par jours actifs** — la coupe tombe vers 7 200 jours actifs sur
~26 900 jours de parution. La variante « seuil ≥ 1 000 jours » (39 316 mots)
est notée au to_do pour comparaison ultérieure.

La fusion des graphies avec/sans accents, pensée pour les doublons OCR,
fusionnait aussi de vrais mots distincts (« retraite + retraité »,
« côte + côté »…) : sur 20 000 clés candidates, 2 330 avaient des graphies
secondaires pesant plus de 1 % du total. **Choix acté : l'unité de vocabulaire
est la graphie**, et une graphie n'est absorbée par la dominante de sa clé
désaccentuée que si elle pèse **moins de 1 %** de celle-ci — les doublons OCR
(« chomâge », « chomage » des années mal numérisées) sont sommés dans le mot,
les paires réelles restent deux mots. Extraction en masse : `rupture/masse.py`,
une passe sur `unigram`, matrice dense 10 000 mots × 26 917 jours dans
`data/vocab_series_lemonde.npz` (~10 min sur gallica).

## Phase 3 — NMS : un représentant par événement (2026-07-22)

La campagne `pics_masse` a rendu **164 254 pics** sur le top-10 000 (9 817
mots avec au moins un pic, 11 échecs de fit). Beaucoup se suivent à quelques
jours d'écart : leurs fenêtres ±15 jours se recouvriraient dans la matrice,
et la PCA compterait plusieurs fois le même événement. L'étape 4 ne garde
qu'un représentant par événement — une *non-maximal suppression* (NMS),
implémentée dans [`rupture/nms.py`](rupture/nms.py).

L'idée naïve — fusionner de proche en proche les pics dont les fenêtres se
recouvrent, puis garder le meilleur de chaque groupe — a été **écartée** :
c'est du single-linkage, et son effet de chaînage est un défaut documenté
depuis les années 70 (Jain & Dubes 1988). Il suffit d'un pont de pics
espacés de moins de 31 jours pour souder des mois entiers en un « groupe
géant » réduit à un seul datapoint. Mesuré sur nos données : 164 groupes
s'étendant sur plus de 90 jours de parution, dont « syrienne » (203 pics sur
760 jours, 2012-2014) ou « jaunes » (177 pics sur 325 jours, 2018-2019) —
autant d'événements distincts écrasés en un seul.

Trois choix à justifier explicitement dans la partie méthode :

1. **L'algorithme est glouton et non-transitif** — le vrai point
   différenciant. On trie les pics d'un mot par surprise décroissante ; le
   plus fort est retenu et supprime ses voisins **directs** (à moins de 31
   jours de lui) ; un pic supprimé ne supprime personne ; on répète sur les
   survivants. La suppression ne se propage jamais de proche en proche,
   donc pas de groupe géant : « syrienne » donne 18 représentants au lieu
   d'un, « jaunes » 8. C'est le NMS canonique de la détection d'objets
   (R-CNN ; Soft-NMS, Bodla et al. 2017), qui n'est *pas* un « max par
   composante connexe » — la différence est exactement la non-transitivité.
2. **Distance de suppression : 31 jours de parution** (= la largeur d'une
   fenêtre, 1 + 2×15). Choisie pour garantir par construction qu'aucune
   paire de fenêtres gardées ne se chevauche jamais dans la matrice. En
   jours de parution et non calendaires, car les fenêtres de
   `fenetres.py` sont des lignes de la série (la base saute les jours sans
   journal).
3. **Critère de conservation : la surprise maximale** (p-valeur minimale),
   décidé dès la formulation de l'étape — le jour le plus anormal représente
   l'événement.

Note pour le mémoire (bas de page) : la sismologie a eu exactement ce débat
pour ses répliques. Gardner-Knopoff (1974) = fenêtres centrées sur le choc
principal (notre glouton) ; Reasenberg (1985) = chaînage transitif adaptatif
(l'approche écartée) ; sur un même catalogue, le déclustering par chaînage
échoue au test de Poisson là où les fenêtres le passent (GJI 2021).

**Contre-vérification** : `scipy.signal.find_peaks(height=4, distance=31)`
sur le signal surprise — son paramètre `distance` est un NMS glouton 1D de
référence, implémentation indépendante de la nôtre. Résultat : accord sur
**9 771 mots sur 9 817** ; les 46 écarts sont compris — 45 égalités de
surprise (le CSV arrondit à 2 décimales) départagées différemment, 1 pic
gardé par nous car à exactement 31 jours du maximum (fenêtres disjointes,
conforme) mais « dans l'ombre » d'un voisin supprimé plus haut, donc jamais
candidat chez scipy. Aucun bug.

**Bilan** (test local sur les données du serveur) : 123 465 pics gardés sur
164 254 (75,2 %), médiane 10 représentants par mot ; 84 % des pics gardés
sont solo (`n_absorbes` = 0) — le NMS ne mord que sur les périodes denses,
comme voulu. Record d'absorption : « francisco », 58 pics absorbés autour du
26/04/1945 — la conférence de San Francisco, fondation de l'ONU.

Sorties officielles produites sur gallica dans la foulée : le NMS (7 s, même
bilan qu'en local), puis l'**extraction des fenêtres** ±15 jours de parution
autour de chaque pic gardé ([`rupture/fenetres_masse.py`](rupture/fenetres_masse.py),
vectorisée sur la matrice du npz, 4 s) : **matrice 123 310 × 31** de $f_t$
pour $10^5$ dans `data/fenetres_lemonde.npz`, métadonnées alignées (mot,
date, $X_t$, $N_t$, $f_t$, $p_t$, surprise, `n_absorbes`), 155 pics à moins
de 15 jours d'un bord écartés. Le dataset de sauts de l'étape 3 est prêt —
prochaine étape : la normalisation des fenêtres, puis la PCA du modèle zéro.
