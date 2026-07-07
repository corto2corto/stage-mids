# Prospection CNews (cnews.fr) — dossier manager

Candidat #1 de `candidats.md` (★★★ cas d'école ligne éditoriale, Bolloré/Canal+).
Croisement des rapports mapping / scrapper / explorateur + smoke-test serveur.
Rien n'est branché : ce dossier est prêt à valider par Corto.

## Verdict

**Ajoutable en « basic complet ».** Aucun tronqué sur l'échantillon (10/10 texte
intégral, 209-837 mots, fins de phrases ponctuées, zéro marqueur de paywall) ;
site 100 % gratuit sur toute la profondeur testée (2012→2026), donc pas de
filtre `free` à prévoir. Structure json-ld `NewsArticle` stable sur 15 ans,
extraction validée par exécution réelle de `extraire()` sur les 10 HTML. Fort
intérêt mémoire (rachat Bolloré, bascule iTélé→CNews) et aucun red flag
technique (pas de blocage anti-bot en basic, Crawl-delay 10s respectable).

## Synthèse des 3 rapports

**Mapping.** Source : `https://www.cnews.fr/sitemap.xml`, index paginé
`?page=1..215` (~2000 URLs/page), ~430 000 URLs au total dont ~45 % d'articles
texte (~190-200k). Format article :
`https://www.cnews.fr/{rubrique}/{YYYY-MM-DD}/{slug}[-ID]`. À exclure :
`videos/`, `podcast/`, `emission/`, `diaporamas/` + pages statiques sans date.
Profondeur 2012-02-17 → aujourd'hui. `robots.txt` déclare le sitemap,
`Crawl-delay: 10` (à respecter), le format article n'est pas `Disallow`.
Ordre non chronologique dans le sitemap.

**Scrapper.** 10/10 URLs d'échantillon (2012→2026, rubriques variées) en
HTTP 200 via curl_cffi (moteur basic), zéro redirection, texte intégral
partout, aucun marqueur de paywall. Site 100 % gratuit sur l'échantillon.
HTML sauvés côté serveur dans
`/data/elias/stage-mids-v2/exploration/prospection_html/cnews/`.

**Explorateur.** json-ld `NewsArticle` 10/10, structure constante 2012→2026
(`headline`, `author`, `datePublished` ISO, `articleBody` remplis). Entrée
validée par exécution réelle de `extraire()` sur les 10 HTML :
`"cnews": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-body"}}`.
`isAccessibleForFree` absent partout (site sans paywall → colonne `free`
vide). `articleSection` vide avant 2016, mais rubrique déductible du 1er
segment d'URL (10/10) — sans incidence puisqu'on route par `moteur: basic`
et non par rubrique.

## Smoke-test (vérification manager, pages 1-2 du sitemap)

Script testé : copie temporaire de `mapping_cnews.py` limitée aux pages 1 et
2, exécutée sur gallica (`cd /data/elias/stage-mids-v2 && PYTHONPATH=... 
.venv/bin/python /tmp/mapping_cnews_smoke.py`), fichiers temporaires
supprimés après vérification.

- Page 1 : HTTP 200, 2000 `<loc>`. Page 2 : HTTP 200, 2000 `<loc>`.
- **1er passage** (motif rubrique obligatoire) : 3926 retenues, 74 rejetées.
  En inspectant les rejets : 63 étaient bien `videos/podcast/emission/
  diaporamas` (correctement exclus), mais **11 étaient des faux négatifs**
  — 10 articles datés de tout début d'archive (2012-02-17 à 2012-03-01) au
  format `https://www.cnews.fr/{YYYY-MM-DD}/{slug}` **sans segment
  rubrique**, plus la page d'accueil (`https://www.cnews.fr/`, à juste
  titre exclue).
- **Motif corrigé** (rubrique rendue optionnelle dans la regex, exclusions
  videos/podcast/emission/diaporamas inchangées) : **3999 retenues, 1
  rejetée** (uniquement la page d'accueil). Vérifié sur les pages 100 et
  215 : ce cas « sans rubrique » n'apparaît que sur la page 1 (tout début
  d'archive), 0 occurrence ailleurs — pas une dérive du motif, juste une
  particularité des tout premiers articles du site.
- Page 215 renvoie 1782 `<loc>` (< 2000) : confirme que 215 est bien la
  dernière page du sitemap, cohérent avec le total ~430k annoncé par le
  mapping (`214 × 2000 + 1782 ≈ 429 782`).
- Échantillon de 3 URLs retenues, bien conformes :
  - `https://www.cnews.fr/politique/2012-03-07/nicolas-sarkozy-sur-france-2-un-comedien-de-serie-b-selon-nathalie-arthaud-5151`
  - `https://www.cnews.fr/economie/2012-03-02/electricite-et-gaz-la-concurrence-progresse-en-2011-selon-la-cre-3749`
  - `https://www.cnews.fr/technologie/2012-03-27/nouvel-ipad-apple-attaque-en-justice-en-australie-11415`

`exploration/mapping_cnews.py` (script complet, 215 pages) intègre déjà le
motif corrigé — pas seulement la version smoke testée.

## Entrée medias.py prête à coller (NON appliquée)

```python
"cnews": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "div.article-body"}},
```

À insérer dans le bloc des médias `basic` de `scraping/medias.py`, avec un
commentaire du type `# cnews : validé prospection 07/07/2026, 100 % gratuit,
json-ld stable 2012-2026`. `attente` non précisé → `ATTENTE_BASIC` par
défaut suffit (pas de spécificité repérée).

## Plan de branchement (à exécuter uniquement sur validation explicite de Corto)

1. Lancer `python -m exploration.mapping_cnews` sur gallica (~36 min, 215
   pages × `Crawl-delay` 10 s). Produit `exploration/cnews_url.csv`
   (~190-200k URLs attendues, cf volumes ci-dessous).
2. Copier/déplacer `exploration/cnews_url.csv` vers `DATA_DIR` (par défaut
   `/data/elias/stage-mids/data/cnews_url.csv`, ou le `STAGE_DATA_DIR` de
   test si on valide d'abord sur base isolée) — c'est ce dossier que
   `scraping/pipeline.py` scrute (`DATA_DIR.glob("*_url.csv")`).
3. Charger en base : `charger_nouvelles_urls(conn)` dans
   `scraping/pipeline.py` est actuellement **désactivé** (ligne commentée
   dans `main()` : `# charger_nouvelles_urls(conn)  # désactivé : pas de
   nouveaux CSV pour l'instant`) — il faudra soit la réactiver le temps du
   chargement, soit l'appeler manuellement une fois, puis la
   recommenter si elle doit rester désactivée par défaut.
4. Ajouter l'entrée `"cnews"` ci-dessus dans `scraping/medias.py`.
5. Relancer le pipeline pour que `cnews` entre dans le prochain `new_batch()`
   — note : `lancer.sh` est actuellement à l'arrêt depuis le 06/07 (tests
   v2 en cours, cf `project_lancer_en_pause`), donc ce point dépend de la
   reprise générale du scraping, pas seulement de CNews.

## Volumes attendus

- ~430 000 URLs totales dans le sitemap (215 pages × ~2000, dernière page
  partielle à 1782).
- ~45 % d'articles texte selon le rapport mapping → **~190 000-200 000
  URLs** attendues dans `cnews_url.csv` après filtrage.
- Note manager : le smoke-test (pages 1-2, tout début d'archive 2012) a
  retenu 3999/4000 URLs (~100 %), très au-dessus de la moyenne 45 % globale
  — cohérent avec une montée en charge du contenu vidéo/podcast/émission
  au fil des ans (CNews est une chaîne TV, contrairement au début
  d'archive plus proche d'un simple portail texte). Le taux réel de
  filtrage se rapprochera de 45 % en moyenne sur l'ensemble des 215 pages,
  pas des ~100 % vus sur l'échantillon de 2 pages.

## Intérêt pour le mémoire

CNews est un cas d'école pour la question de recherche (rachats de
journaux français et couverture thématique) : rachetée par Vincent Bolloré
via Canal+/Vivendi, la chaîne (ex-iTélé) a connu une bascule de marque et
de ligne éditoriale documentée en 2016-2017 (grève historique de la
rédaction d'iTélé fin 2016, renommage en CNews mi-2017, virage éditorial
très commenté depuis). L'archive du site remonte à 2012-02-17, donc
**avant** le rachat Bolloré (qui prend le contrôle capitalistique de
Canal+/Vivendi à partir de 2014-2015 et impose la ligne CNews à partir de
2016-2017) : la profondeur disponible permet de mesurer une rupture
sémantique avant/pendant/après la bascule iTélé→CNews, exactement le type
de rupture que le mémoire cherche à détecter. Volume élevé (~190-200k
articles texte) et échantillonnage propre (json-ld stable, aucun tronqué)
en font un candidat solide pour la phase d'industrialisation.

## Fichiers produits par ce dossier

- `exploration/mapping_cnews.py` : script de mapping complet (215 pages,
  motif rubrique-optionnelle validé par smoke-test), prêt à lancer mais
  **non lancé** (mapping complet interdit dans le cadre de cette mission).
- `exploration/prospection/cnews.md` : ce dossier.

Aucun fichier de `scraping/` n'a été modifié ; `medias.py` n'a pas été
touché ; le mapping complet n'a pas été lancé.
