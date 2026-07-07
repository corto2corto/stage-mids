# Prospection Closer (closermag.fr) — dossier manager

Candidat #4 de `candidats.md` (★★★ machine à rachats, Reworld Media,
racheté à Mondadori en 2019). Croisement des rapports mapping / scrapper /
explorateur + smoke-test serveur. Rien n'est branché : ce dossier est prêt à
valider par Corto.

## Verdict

**Ajoutable en « basic complet »** techniquement — gratuit, HTML statique,
json-ld stable, extraction validée par exécution réelle (10/10 propres, zéro
mélange de légendes). **Mais réserve majeure sur le corpus** : un
re-templating Reworld de mai 2023 a vidé au moins les articles de 2009 (corps
remplacé par un diaporama répétant le titre, `wordCount:13`) — URL et titre
conservés, texte détruit. La frontière du vidage (entre 2009 et fin 2022,
~13 ans d'archive) est inconnue à ce stade : tant qu'elle n'est pas localisée,
impossible de savoir si la période pré-rachat (avant 2019) est exploitable
pour le mémoire ou majoritairement détruite. **Avant toute exploitation** :
sonde dédiée de ~20 articles étalés 2015-2022 (datePublished réel, pas le
lastmod du sitemap) pour localiser la frontière ; si le pré-2019 s'avère
mort, se rabattre sur des snapshots Wayback (CDX API) des pages archivées
avant mai 2023. Fait notable pour le mémoire : la destruction elle-même
(remplacement massif d'archives éditoriales par un template diaporama après
un rachat) est une donnée en soi, pas seulement un obstacle technique.

## Synthèse des 3 rapports

**Mapping.** Source : sitemaps Yoast WordPress, index
`https://www.closermag.fr/sitemap_index.xml`. L'index référence 8 types de
fichiers (post/page/category/author/...) ; seuls les `post-sitemap*.xml`
contiennent des articles : `post-sitemap.xml` + `post-sitemap2.xml` →
`post-sitemap220.xml` (dernier partiel), ~1000 URLs chacun, ~219 000 articles
au total. Format article :
`https://www.closermag.fr/<rubrique>/<slug>-<id>`. Profondeur réelle
2009 → 2026, **mais** le `<lastmod>` du sitemap est trompeur : une
réindexation massive a eu lieu en mai 2023 sur tout l'historique — seul le
`datePublished` json-ld dans la page fait foi pour dater un article. Pas de
`Crawl-delay` dans `robots.txt`, pas de blocage réseau constaté.

**Scrapper.** 10/10 URLs HTTP 200 sans redirection. Articles 2022-2026 :
**complets** (307-491 mots), gratuits, texte en HTML statique, aucun
marqueur de paywall. Articles 2009 : **vidés** — corps remplacé par un
diaporama qui répète uniquement le titre (`wordCount:13` dans le json-ld),
URL et titre conservés mais texte détruit par le re-templating Reworld de
mai 2023. La frontière exacte du vidage entre 2009 et fin 2022 n'a pas été
testée (échantillon actuel : seulement 2022-2026 et 2009). HTML sauvés côté
serveur dans
`/data/elias/stage-mids-v2/exploration/prospection_html/closermag/`.

**Explorateur.** Entrée validée par exécution réelle de `extraire()` sur les
10 HTML :
`"closermag": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-content"}}`.
Les pages vidées sortent `contenu` vide (le gabarit diaporama n'a aucun
`<p>`) → `est_bloque()` les détecte automatiquement comme bloquées (`etat=1`
dans `stockage.py`), pas besoin de filtre dédié. Les pages complètes sortent
propres, sans légendes ou éléments de navigation mélangés au texte.
`isAccessibleForFree` absent → colonne `free` vide (site sans paywall).
Alternatives testées et rejetées : `article_body_content` (absent en 2026),
corps json-ld brut (texte moins fidèle que `div.article-content`).

## Smoke-test (vérification manager, 3 requêtes : index + 2 post-sitemaps)

Script exécuté sur gallica via heredoc SSH (`cd /data/elias/stage-mids-v2 &&
PYTHONPATH=/data/elias/stage-mids-v2 .venv/bin/python
/tmp/mapping_closermag_smoke.py`), fichiers temporaires supprimés après
vérification (aucune branche git temporaire utilisée).

- **Index** (`sitemap_index.xml`) : HTTP 200, 29 361 caractères. 227 sitemaps
  au total (tous types confondus), dont **220 `post-sitemap*.xml`** — conforme
  au rapport mapping (`post-sitemap.xml` + `post-sitemap2..220.xml`).
  1er chunk : `post-sitemap.xml`. Dernier : `post-sitemap220.xml`. Les deux
  cibles du smoke-test (`post-sitemap2.xml`, `post-sitemap220.xml`) sont bien
  présentes dans l'index.
- **`post-sitemap2.xml`** : HTTP 200, 1 203 982 caractères, **1000 `<loc>`**
  — confirme le volume « ~1000 URLs par chunk » du rapport mapping.
- **`post-sitemap220.xml`** : HTTP 200, 22 168 caractères, **50 `<loc>`**
  seulement — confirme que 220 est bien le dernier chunk, partiel.
- **1050 URLs extraites** des 2 chunks (aucun doublon entre les deux).
  **1050/1050 (100 %) conformes** au format
  `https://www.closermag.fr/<rubrique(s)>/<slug>-<id>` (rubrique parfois sur
  2 segments, ex. `vecu/disparitions/...` — le format reste cohérent avec le
  rapport mapping une fois la regex de vérification élargie aux
  sous-rubriques).
- Échantillon de 3 URLs conformes :
  - `https://www.closermag.fr/royautes/prince-harry-l-evolution-physique-du-mari-de-meghan-markle-de-sa-jeunesse-au-cou-1712135`
  - `https://www.closermag.fr/vecu/disparitions/disparition-de-leana-15-ans-a-draveil-ces-details-sordides-sur-ce-qui-lui-serait-arrive-pendant-deux-semaines-1715939`
  - `https://www.closermag.fr/people/ca-marche-encore-!-danielle-moreau-donne-des-details-oses-sur-sa-vie-sexuelle-1718059`
- Extrapolation volume total : 219 chunks pleins (~1000) + 1 chunk partiel
  (50) ≈ **219 050 articles**, cohérent avec le « ~219 000 » du rapport
  mapping.
- Fichiers temporaires nettoyés sur le serveur après vérification
  (`/tmp/mapping_closermag_smoke.py`, `/tmp/prospect_closermag_smoke.csv`).

## Entrée medias.py prête à coller (NON appliquée)

```python
"closermag": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-content"}},
```

À insérer dans le bloc des médias `basic` de `scraping/medias.py` (proche de
`gala`/`voici`, même famille people/loisirs), avec un commentaire du type
`# closermag : validé prospection 07/07/2026, gratuit, MAIS re-templating
Reworld mai 2023 a vidé au moins 2009 -> sonder la frontière avant
d'exploiter le pré-2022 (cf exploration/prospection/closermag.md)`.
`attente` non précisé → `ATTENTE_BASIC` par défaut suffit.

## Plan de branchement (à exécuter uniquement sur validation explicite de Corto)

1. **Sonder la frontière du vidage AVANT tout.** Écrire un script dédié
   (hors périmètre de cette mission) qui récupère ~20 articles étalés sur
   2015-2022 et lit leur `datePublished` json-ld réel (pas le `lastmod` du
   sitemap, trompeur). Piste pratique : les `post-sitemap*.xml` Yoast sont
   généralement générés dans l'ordre chronologique de publication (le
   numéro de chunk croît avec le temps — **hypothèse à vérifier en tout
   début de sonde**, pas encore confirmée ici) ; si elle se confirme, on
   peut cibler des chunks espacés entre `post-sitemap.xml` (2009) et
   `post-sitemap220.xml` (2026) pour couvrir 2015-2022 sans avoir besoin du
   `lastmod`. Pour chaque article sondé : `datePublished` + `wordCount`
   json-ld + inspection du corps (diaporama vidé vs texte réel) →
   localise la frontière du re-templating de mai 2023.
   - Si le pré-2019 (rachat Mondadori→Reworld) s'avère majoritairement
     détruit : bascule sur les snapshots Wayback Machine (CDX API,
     `http://web.archive.org/cdx/search/cdx?url=closermag.fr/*&from=20090101&to=20230501`)
     pour récupérer le HTML des pages telles qu'archivées avant le
     re-templating de mai 2023.
2. Lancer `python -m exploration.mapping_closermag` sur gallica (~221
   requêtes, ~7 min). Produit `exploration/closermag_url.csv` (~219 000 URLs
   attendues).
3. Copier/déplacer `exploration/closermag_url.csv` vers `DATA_DIR` (par
   défaut `/data/elias/stage-mids/data/closermag_url.csv`, ou le
   `STAGE_DATA_DIR` de test si on valide d'abord sur base isolée).
4. Charger en base : `charger_nouvelles_urls(conn)` dans
   `scraping/pipeline.py` est actuellement **désactivé** (ligne commentée
   dans `main()`) — réactiver temporairement ou appeler manuellement, puis
   recommenter si elle doit rester désactivée par défaut.
5. Ajouter l'entrée `"closermag"` ci-dessus dans `scraping/medias.py`.
6. Relancer le pipeline pour que `closermag` entre dans le prochain
   `new_batch()` — `lancer.sh` est actuellement à l'arrêt depuis le 06/07
   (tests v2 en cours), donc ce point dépend de la reprise générale du
   scraping.
   - Note pipeline : les articles vidés (post-templating) sortiront
     automatiquement `etat=1` (bloqué) via `est_bloque()` sur `contenu`
     vide — aucun filtre supplémentaire à coder, mais cela veut dire qu'une
     bonne partie du corpus 2009-2022 (selon où se situe la frontière)
     atterrira en base comme « bloqué » plutôt que comme absent : à garder
     en tête pour l'interprétation des volumes exploitables.

## Volumes attendus

- ~219 000 URLs totales dans les sitemaps (220 chunks : 219 pleins × ~1000 +
  1 partiel à 50), confirmé par le smoke-test (`post-sitemap2.xml` = 1000
  `<loc>`, `post-sitemap220.xml` = 50 `<loc>`).
- Volume **réellement exploitable** (texte non vidé) : inconnu tant que la
  frontière du re-templating n'est pas localisée. Si le vidage touche
  l'essentiel de 2009-2022 (hypothèse pessimiste), le corpus utile se
  limiterait à ~2022-2026, soit une fraction mineure des ~219 000 URLs. Si le
  vidage est plus récent ou partiel, une part significative de la
  profondeur avant/après le rachat Mondadori→Reworld (2019) resterait
  exploitable. D'où la priorité à la sonde de l'étape 1 du plan de
  branchement.

## Intérêt pour le mémoire

Closer / Reworld Media est un cas doublement intéressant pour la question de
recherche (rachats de journaux français et couverture thématique). D'abord
comme candidat classique : rachat de Mondadori France par Reworld Media en
2019, avec une profondeur de sitemap qui couvre largement l'avant (2009-2019)
et l'après (2019-2026) — exactement la fenêtre voulue pour mesurer une
rupture sémantique autour du rachat. Ensuite, et c'est spécifique à ce
média, le re-templating de mai 2023 qui a vidé le corps de (au moins une
partie de) l'archive ancienne constitue **une donnée en soi pour le
mémoire** : une maison connue pour l'accumulation de titres people/femme
(Reworld possède aussi Gala, Voici, Marie-France, etc.) a purgé le contenu
éditorial de ses archives après rachat, ne conservant que l'URL et le titre
à des fins de référencement — une forme de destruction documentaire
post-rachat qui mérite d'être mentionnée même si elle limite l'exploitation
quantitative du corpus ancien.

## Fichiers produits par ce dossier

- `exploration/mapping_closermag.py` : script de mapping complet (~221
  requêtes, filtrage post-sitemap*.xml validé par smoke-test), prêt à
  lancer mais **non lancé** (mapping complet interdit dans le cadre de
  cette mission).
- `exploration/prospection/closermag.md` : ce dossier.

Aucun fichier de `scraping/` n'a été modifié ; `medias.py` n'a pas été
touché ; le mapping complet n'a pas été lancé. Budget réseau smoke-test :
3 requêtes vers closermag.fr (index + 2 post-sitemaps), fichiers temporaires
nettoyés sur le serveur.
