# Détail des métadonnées par média

Pour chaque média, inspection du HTML réel (post-bypass, via `exploration/<media>.html`) pour identifier les balises BeautifulSoup à cibler. Métadonnées recherchées : titre, auteur, date, corps de l'article.

## Le Capital

| Métadonnée | Tag | Classe |
|---|---|---|
| Titre | `h1` | `article-headTitle` |
| Chapô | `div > p` | `article-headLead` |
| Auteur | `span` (ou `a`) | `articleSignature-authorName` / `articleSignature-authorNameLink` |
| Date | `time` dans `span` | `articleSignature-publishedAt` |
| Corps | `div` | `articleBody defaultStyleContentTags` |

Note : cibler les `<p>` à l'intérieur de `articleBody` plutôt que tous les `<p>` de la page pour éviter le bruit (menus, pubs, recommandations).

## Le Figaro

| Métadonnée | Tag | Classe / attribut |
|---|---|---|
| Titre | `h1` | `fig-headline fig-pagination__hidden` |
| Chapô | `p` | `fig-standfirst` |
| Auteur | `a` dans `p` | `fig-content-metas__author` (dans `fig-content-metas__authors-container`) |
| Date | `time` dans `p` | `fig-content-metas__pub-date` |
| Corps | `div` | `fig-content-body` (paragraphes : `p.fig-paragraph` à l'intérieur) |

## Le Journal du Dimanche

| Métadonnée | Tag | Classe / attribut |
|---|---|---|
| Titre | `h1` | `main-title` |
| Description | `meta` | `property="og:description"` (ou `name="description"`) |
| Headline | `meta` | `property="og:title"` |
| Auteur | `a` | `author` |
| Date | `time` | (pas de classe, directement sous `div.date-author`) |
| Image | `meta` | `property="og:image"` |
| Corps | `div` | `rte` |
| Intro/chapô | `p` | `intro` |
| Read also | `div` | `readtoo` |

Note : pas de section ni de keywords dans les `<meta>`. L'article dumpé est un live (format différent d'un article standard) — structure à re-vérifier sur un article classique.

## Le Monde

Métadonnées standardisées dans les `<meta>` (Open Graph, très complètes) :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` / `property="og:description"` |
| Section | `property="og:article:section"` (aussi `name="ad:rub"`) |
| Keywords | `name="ad:keywords"` |
| Auteur | `property="og:article:author"` |
| Date publiée | `property="og:article:published_time"` |
| Image | `property="og:image"` |
| Free/locked | `property="og:article:content_tier"` (`locked` = payant) |
| article_id | `name="ad:article_id"` |

Métadonnées dans le corps :

| Métadonnée | Tag | Classe |
|---|---|---|
| Titre | `h1` | `ds-title` |
| Chapô | `span` | `ds-chapo` (dans `div.ds-description`) |
| Auteur | `span` | `meta__author` |
| Date | `span` | `meta__date` |
| Corps | `div` | `article__content` (paragraphes : `p.article__paragraph`) |
| Paywall | `section` | `paywall js-paywall` (présence = article premium) |

**Constat clé** : les `<meta>` `og:article:*` suivent la norme Open Graph (`content_tier`, `published_time`, `author`, `section`). Si plusieurs médias les exposent, on aura un socle commun extractible de façon uniforme — seul le corps de l'article demandera une règle par média.

## Le Nouvel Obs

Métadonnées dans les `<meta>` (Open Graph, le plus complet observé) :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` / `property="og:description"` |
| Auteur | `property="og:article:author"` |
| Date publiée | `property="og:article:published_time"` |
| Date modifiée | `property="og:article:modified_time"` |
| Section | `property="og:article:section"` |
| Tags | `property="og:article:tag"` (**plusieurs** balises → `find_all`) |
| Image | `property="og:image"` |
| Free/locked | `property="og:article:content_tier"` (ici `free`) |
| article_id | `name="ad:article_id"` |

Métadonnées dans le corps :

| Métadonnée | Tag | Classe |
|---|---|---|
| Titre | `h1` | (classes typo `antonia-*` peu stables → cibler le `h1` seul) |
| Chapô | `p` | `article__description` |
| Auteur | `p` | `authors` |
| Date | `time` | (dans `header.highlights`) |
| Corps | `p` | `node__paragraphe` (paragraphes directs, pas de div conteneur claire) |
| Read also | `div` | `article__related-also-read-articles` |

Note : l'article dumpé est `content_tier=free` → pas tronqué, cohérent. Le bypass du Nobs reste non résolu pour les articles premium (cf. section bypass).

## Les Échos

**Cas particulier** : site React/styled-components → classes CSS **hashées et instables** (`sc-1s859o0-0`, `gFYkRd`…), inutilisables pour le parsing. Les `<meta>` sont donc le socle fiable.

Métadonnées dans les `<meta>` :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` / `property="og:description"` |
| Date publiée | `property="article:published_time"` |
| Date modifiée | `property="article:modified_time"` |
| Section | `property="article:section"` |
| Free/paywall | `name="ad:postAccess"` (ici `paywall`) |
| article_id | `name="ad:articleId"` |

Métadonnées dans le corps :

| Métadonnée | Tag | Repère |
|---|---|---|
| Titre | `h1` | classe instable → cibler le `h1` seul |
| Corps | `div` | **`post-paywall`** (seule classe stable et sémantique au milieu des hashes → point d'ancrage du contenu, prendre les `<p>` à l'intérieur) |

Note : pas d'`og:article:author` ni de classe d'auteur stable → l'auteur sera difficile à récupérer pour ce média (à abandonner ?). `ad:postAccess=paywall` confirme l'article premium ; le bypass a fonctionné puisque `post-paywall` est présent.

## Nice Matin

Métadonnées dans les `<meta>` (complets, auteur inclus) :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` |
| Auteur | `property="article:author"` |
| Date publiée | `property="article:published_time"` |
| Date modifiée | `property="article:modified_time"` |
| Section | `property="article:section"` |
| Tags | `property="article:tag"` (**plusieurs** → `find_all`) |
| Image | `property="og:image"` |
| Free/paywall | `name="pbstck_context:paywall"` (ici `no`) |
| article_id | `name="ad:article_id"` |
| Rubrique détaillée | `name="ad:GrNM_rubrique"` / `ad:GrNM_locale` |

Métadonnées dans le corps :

| Métadonnée | Tag | Repère |
|---|---|---|
| Titre | `h1` | classes Bootstrap → cibler le `h1` seul |
| Sous-titre | `h2` | premier `h2` (`text-secondary`) |
| Corps | — | **point faible** : pas de conteneur sémantique unique, `<p>` dispersés (classes Bootstrap `fs-5`/`fs-6`). Piste : prendre les `<p>` du `<article>` en excluant la sidebar `col-lg-sidebar`. À creuser à l'écriture de la fonction. |

Note : `pbstck_context:paywall=no` → gratuit (cohérent, Nice Matin sans paywall). Classes Bootstrap utilitaires partout → s'appuyer sur les `<meta>` + structure `<article>`.

## Paris Match

`<meta>` pauvres (pas de date/auteur/section/content_tier) :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` / `property="og:description"` |
| Image | `property="og:image"` |

Métadonnées dans le corps :

| Métadonnée | Tag | Classe |
|---|---|---|
| Titre | `h1` | `main-title` |
| Surtitre | `a` | `surtitle` |
| Auteur | `span` | `author no-link` (dans `div.date-author`) |
| Date | `time` | (dans `div.date-author`) |
| Intro/chapô | `p` | `intro` |
| Corps | `div` | `rte` |
| Premium | `div` | `premium` (encart abonné) |

**Constat clé** : Paris Match et le JDD partagent le **même CMS** (« lmnr » dans les URLs, classes `main-title`/`rte`/`date-author`/`intro` identiques) → **une seule règle d'extraction commune** pour ces deux médias.

## Télérama

`<meta>` Open Graph complets :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` / `property="og:description"` |
| Auteur | `property="og:article:author"` |
| Date publiée | `property="og:article:published_time"` |
| Section | `property="og:article:section"` |
| Free/locked | `property="og:article:content_tier"` (ici `free`) |
| Opinion | `property="article:opinion"` (`true` = critique/avis) |
| article_id | `name="ad:article_id"` |

Métadonnées dans le corps (classes sémantiques propres) :

| Métadonnée | Tag | Classe |
|---|---|---|
| Titre | `h1` | `article__page-title` |
| Chapô | `p` | `article__chapeau` |
| Auteur | `p`/`a` | `author author--simple` / `author author--link` |
| Date | `p` | `publication__date` |
| Date MAJ | `p` | `publication__update` |
| Corps | `section` | `article__page-content` (paragraphes : `p.paragraph`) |
| Tags | `ul` | `tag__list` |

Note : un des médias les mieux structurés (meta + classes sémantiques). Appartient au groupe Le Monde (cf. footer) — d'où la proximité possible avec les conventions Open Graph du Monde/Nobs.

## Valeurs Actuelles

Site **WordPress** (classes `post__`, `gutenberg`, `wp-`) → classes très stables.

`<meta>` :

| Métadonnée | Source meta |
|---|---|
| Headline | `property="og:title"` |
| Description | `name="description"` / `property="og:description"` |
| Auteur | `name="twitter:data1"` (le `name="author"` vaut « admin », trompeur) |
| Date publiée | `property="article:published_time"` |
| Date modifiée | `property="article:modified_time"` |
| Image | `name="msapplication-TileImage"` |
| Durée lecture | `name="twitter:data2"` |

Métadonnées dans le corps (WordPress, classes stables) :

| Métadonnée | Tag | Classe |
|---|---|---|
| Titre | `h1` | `post__title h1` |
| Chapô | `div` | `post__excerpt gutenberg` |
| Catégorie | `div` | `post__category` |
| Auteur | `div` | `post__author` |
| Date | `time` | `post__date` |
| Corps | `div` | `post__content gutenberg` (les `<p>` à l'intérieur) |

Note : pas de section/content_tier dans les meta, mais présence d'un `<script id="yoast-schema-graph">` (JSON-LD Yoast) contenant souvent auteur/date/section structurés → piste alternative fiable si besoin.

## JSON-LD : cas difficiles

Pour les médias où l'extraction classique coince, on a inspecté le `<script type="application/ld+json">` (schema.org `NewsArticle`), en localisant le texte connu dans le HTML (script `situer_texte.py`) et en parsant le JSON-LD.

**Les Échos** (classes hashées) → le **JSON-LD est le meilleur socle**, plus fiable que les `<meta>` :

| Métadonnée | Champ JSON-LD |
|---|---|
| Headline | `headline` |
| Description | `description` |
| Date publiée | `datePublished` |
| Date modifiée | `dateModified` |
| Free/locked | `isAccessibleForFree` |
| Auteur | `author.name` (`null` sur l'article testé — voir note ci-dessous) |

**Auteur des archives Échos** : sur les vieux articles (ex. archive 1991), il n'y a **aucune balise dédiée** à l'auteur — ni `<meta>`, ni JSON-LD (`author.name = null`). L'autrice (« Annie Coppermann ») n'apparaît que **dans le corps**, en gras : c'est le **dernier `<strong>`** de `div.post-paywall`. Piste de récupération notée mais **non retenue en V0** : trop fragile (rien ne garantit que la signature soit toujours le dernier `<strong>`, et un article sans signature donnerait un faux auteur silencieux). On laisse donc l'auteur vide pour Les Échos pour l'instant ; à ré-évaluer sur des articles récents qui ont peut-être une vraie balise auteur.

**Valeurs Actuelles** → le JSON-LD (Yoast) ajoute `articleSection` (« Politique ») et `wordCount`, absents des `<meta>`. **Mais** l'`author` du JSON-LD vaut « admin » (compte technique) : l'auteur réel n'est fiable que dans le **corps** → `div.post__author > a` (vérifié : « Laurent Dandrieu »).

**Enseignement transversal** : le JSON-LD `NewsArticle` est une source normalisée précieuse, surtout quand les classes CSS sont instables (Les Échos). Pour l'auteur, attention aux comptes techniques (« admin ») — préférer le corps quand le JSON-LD/meta renvoie une valeur générique. À envisager comme **3e source** dans la fonction d'extraction (meta → JSON-LD → corps, par ordre de fiabilité selon le média).

## Inventaire du JSON-LD sur les 10 médias

Extraction du `NewsArticle`/`Article` (champs schema.org) de chaque dump :

| Média | JSON-LD | Auteur | Section | `articleBody` | Note |
|---|---|---|---|---|---|
| le_capital | ✅ | ✅ | ✅ | ✅ 2006c | complet |
| le_figaro | ✅ | ✅ | ✅ | ⚠️ 490c | body tronqué (chapô seul) |
| le_journal_du_dimanche | ❌ | — | — | — | **aucun JSON-LD** |
| le_monde | ✅ | ⚠️ « Le Monde » | ✅ | ❌ | auteur générique, pas de body |
| le_nouvel_observateur | ✅ | ✅ | ✅ | ✅ 4441c | complet |
| les_echos | ✅ | ❌ null | ❌ | ❌ | minimal (archive) |
| nice_matin | ✅ | ✅ | ✅ | ✅ 4797c | complet |
| paris_match | ✅ | ✅ | ✅ | ❌ | méta riche, pas de body |
| telerama | ✅ | ✅ | ✅ | ✅ 5895c | complet |
| valeurs_actuelles | ✅ | ⚠️ « admin » | ✅ | ✅ 11383c | auteur générique |

**Verdict** : le JSON-LD est un **excellent socle commun pour les métadonnées** (titre, date(s), section, keywords, `isAccessibleForFree` = free/locked). 9/10 l'exposent, et il est souvent **plus complet que les `<meta>`** (le_capital, paris_match, les_echos avaient des meta pauvres mais un JSON-LD riche). À combiner avec les `<meta>` pour les 3 trous : JDD (pas de JSON-LD), auteur générique (le_monde, VA → corps), Les Échos (auteur null, abandonné).

En revanche `articleBody` est **inutilisable comme source du corps** : absent (le_monde, paris_match, les_echos) ou tronqué (le_figaro = 490c). Le corps reste extrait du HTML via les conteneurs repérés par média.

**Trouvaille — `hasPart` / `cssSelector` (Le Monde)** : le JSON-LD du Monde documente lui-même sa zone de paywall :
```json
"isAccessibleForFree": "False",
"hasPart": { "isAccessibleForFree": "False", "cssSelector": ".paywall" }
```
Le site indique que la partie payante est l'élément `.paywall`. Piste pour `bypass_reussi` : au lieu d'une regex de phrase-signal, s'appuyer sur ce sélecteur CSS officiel quand il est présent. À explorer sur les autres médias.

## Métadonnées disponibles par média (récapitulatif)

Synthèse, toutes sources confondues (JSON-LD + `<meta>` + corps), des métadonnées récupérables pour chaque média :

| Média | Métadonnées disponibles |
|---|---|
| le_capital | titre, chapô, description, auteur, date publiée, date modifiée, section, keywords, free/locked, image, corps |
| le_figaro | titre, chapô, description, auteur, date publiée, date modifiée, section, keywords, free/locked, corps |
| le_journal_du_dimanche | titre, headline, description, auteur, date, image, intro/chapô, corps, read also (pas de JSON-LD ; pas de section/keywords) |
| le_monde | titre, chapô, description, auteur (corps ; générique en meta/JSON-LD), date publiée/modifiée/créée, section, keywords, free/locked, image, paywall (`.paywall`), corps |
| le_nouvel_observateur | titre, chapô, description, auteur, date publiée, date modifiée, section, tags, keywords, free/locked, image, corps, read also |
| les_echos | titre, description, date publiée, date modifiée, section, free/locked, corps (auteur : absent — archives sans signature) |
| nice_matin | titre, sous-titre, description, auteur, date publiée, date modifiée, section, tags, rubrique détaillée, free/locked, image, corps |
| paris_match | titre, surtitre, description, auteur, date publiée, date modifiée, section, keywords, image, intro/chapô, free/locked, corps |
| telerama | titre, chapô, description, auteur, date publiée, date modifiée, section, keywords, tags, free/locked, opinion, corps |
| valeurs_actuelles | titre, chapô, description, auteur (corps ; « admin » en meta/JSON-LD), catégorie, date publiée, date modifiée, section, durée lecture, image, corps |
