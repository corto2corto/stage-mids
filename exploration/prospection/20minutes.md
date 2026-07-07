# Prospection 20minutes.fr — dossier manager

Candidat #2 de `candidats.md` (★★ Rossel + Ouest-France, gratuit intégral).
Croisement des rapports mapping / scrapper / explorateur + smoke-test serveur.
Rien n'est branché : ce dossier est prêt à valider par Corto.

## Verdict

**Ajoutable en « basic complet ».** 10/10 URLs d'échantillon en HTTP 200,
texte intégral, aucun paywall (108-826 mots), structure json-ld stable
2006→2026 — validé par exécution réelle de `extraire()`. Seul piège identifié
(les « direct/live ») est déjà géré automatiquement en échec propre, sans
code à ajouter. Site 100 % gratuit → pas de filtre `free` à prévoir. Bon
candidat volume (500-800k articles, 20 ans d'archives) et bon témoin de
presse gratuite nationale pour le mémoire.

## Synthèse des 3 rapports

**Mapping.** Source : pages d'archives datées
`https://www.20minutes.fr/archives/YYYY/MM-DD` (liens HTML bruts, pas de JS,
pas de pagination). Profondeur 2006 → 2026 (~7 400 pages-jour). Format
article : `https://www.20minutes.fr/<rubrique>[/<sous-rubrique>]/<ID>-<YYYYMMDD>-<slug>`
— chaque page-jour mélange les articles du jour avec des encarts « plus
lus » d'autres dates, donc filtrage obligatoire sur la date `YYYYMMDD` du
slug égale au jour de la page. Volume estimé 500-800k articles (95-150/jour
en semaine, moins le week-end en début de période). `robots.txt` : `/archives/`
autorisé, pas de `Crawl-delay` pour `*`. Les sitemaps historiques déclarés
dans le `robots.txt` sont morts (403 CloudFront) ; `sitemap-news.xml` ne
couvre que 48h — d'où le choix des pages d'archives datées comme seule
source exploitable sur toute la profondeur.

**Scrapper.** 10/10 (2006→2026) en HTTP 200 via curl_cffi (moteur basic),
zéro redirection, texte intégral dans le HTML (~600 ko/page), aucun
paywall. Piège repéré : les articles « direct/live » ont
`articleBody='A VOIR'` (contenu vide, pas un vrai corps). HTML sauvés côté
serveur dans `/data/elias/stage-mids-v2/exploration/prospection_html/20minutes/`.

**Explorateur.** Entrée validée par exécution réelle sur les 9 HTML non-live
de l'échantillon (108-826 mots, titre/auteur/date/section OK, structure
identique 2006→2026) :
`"20minutes": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}}`.
Les « direct » (`@type LiveBlogPosting`) sortent vides → `est_bloque` →
échec propre automatique (comportement souhaité, aucun code à ajouter pour
les exclure). `isAccessibleForFree` absent → colonne `free` vide (site 100 %
gratuit, cohérent avec le rapport scrapper). `articleSection` du json-ld
fiable sur toute la période 2006-2026.

## Smoke-test (vérification manager, 3 pages-jour connues)

Script testé : `mapping_20min_smoke.py` (copie limitée à 3 pages-jour),
exécuté sur gallica
(`cd /data/elias/stage-mids-v2 && PYTHONPATH=/data/elias/stage-mids-v2
.venv/bin/python /tmp/mapping_20min_smoke.py`), fichiers temporaires
supprimés après vérification. 6 requêtes réseau au total pour tout le
dossier (3 pages-jour + 1 page-année 2015 pour confirmer la structure des
pages d'archives + 2 sondes de mise au point de la regex sur cette même
page), sous le budget de 8.

- `archives/2006/01-03` : HTTP 200, 536 692 car., 136 liens article bruts,
  **100** du bon jour.
- `archives/2015/12-25` : HTTP 200, 531 387 car., 108 liens bruts, **68**
  du bon jour (jour férié — Noël, volume plus bas cohérent avec l'effet
  week-end/férié signalé par le rapport mapping en début de période).
- `archives/2026/07-06` : HTTP 200, 549 538 car., 152 liens bruts, **118**
  du bon jour.
- Comptes conformes à la fourchette attendue (95-190/jour, hors jours
  fériés/week-ends bas de fourchette voire en dessous comme Noël 2015).
- 3 URLs conformes au format `<rubrique>[/<sous-rubrique>]/<ID>-<YYYYMMDD>-<slug>` :
  - `https://www.20minutes.fr/arts-stars/4232720-20260706-lorie-worlds-apart-tragedie-pourquoi-toujours-fan-nostalgique-artistes-annees-1990-2000`
  - `https://www.20minutes.fr/arts-stars/cinema/4233141-20260706-minions-monstres-signe-tres-mauvais-demarrage-etats-unis-reste-monde`
  - `https://www.20minutes.fr/arts-stars/loisirs/4232636-20260706-pourquoi-souris-vit-2-ans-requin-plus-300-ans`
- Vérification structurelle complémentaire (1 requête sur `archives/2015`) :
  la page-année liste bien les 365 jours de l'année sous forme de href
  `https://www.20minutes.fr/archives/2015/MM-DD` (365 liens trouvés), ce qui
  confirme la logique en 2 temps du script complet (page-année → liste des
  jours → page-jour → liste des articles).

## Entrée medias.py prête à coller (NON appliquée)

```python
"20minutes": {"moteur": "basic", "meta": {"strategie": "json_ld", "corps": "json_ld"}},
```

À insérer dans le bloc des médias `basic` de `scraping/medias.py`, avec un
commentaire du type `# 20minutes : validé prospection 07/07/2026, 100 %
gratuit, json-ld stable 2006-2026, articles "direct" échouent proprement
(articleBody vide)`. `attente` non précisé → `ATTENTE_BASIC` par défaut
suffit (pas de spécificité repérée, aucun signe d'anti-bot en basic).

## Plan de branchement (à exécuter uniquement sur validation explicite de Corto)

1. Lancer `python -m exploration.mapping_20minutes` sur gallica (~3h, ~7 400
   pages-jour + 21 pages-année à 1s de politesse). Produit
   `exploration/20minutes_url.csv` (500-800k URLs attendues, cf volumes
   ci-dessous). Relançable par année via la constante `ANNEES` en cas
   d'interruption — le CSV est complété par ajout, pas écrasé.
2. Copier/déplacer `exploration/20minutes_url.csv` vers `DATA_DIR` (par
   défaut `/data/elias/stage-mids/data/`, ou le `STAGE_DATA_DIR` de test si
   on valide d'abord sur base isolée) — c'est ce dossier que
   `scraping/pipeline.py` scrute (`DATA_DIR.glob("*_url.csv")`).
3. Charger en base : `charger_nouvelles_urls(conn)` dans
   `scraping/pipeline.py` est actuellement **désactivé** (ligne commentée
   dans `main()` : `# charger_nouvelles_urls(conn)  # désactivé : pas de
   nouveaux CSV pour l'instant`) — il faudra soit la réactiver le temps du
   chargement, soit l'appeler manuellement une fois, puis la recommenter
   si elle doit rester désactivée par défaut.
4. Ajouter l'entrée `"20minutes"` ci-dessus dans `scraping/medias.py`.
5. Relancer le pipeline pour que `20minutes` entre dans le prochain
   `new_batch()` — note : `lancer.sh` est actuellement à l'arrêt depuis le
   06/07 (tests v2 en cours, cf `project_lancer_en_pause`), donc ce point
   dépend de la reprise générale du scraping, pas seulement de 20minutes.

## Volumes attendus

- ~7 400 pages-jour sur 2006-2026 (365/366 jours × 21 ans, dont 2026
  partielle).
- 95-150 articles/jour en semaine selon le rapport mapping, moins le
  week-end en début de période → **500 000-800 000 URLs** attendues dans
  `20minutes_url.csv`, cohérent avec les comptes du smoke-test (68-118
  articles/jour observés sur l'échantillon).
- Volume nettement supérieur à CNews (~190-200k) : 20minutes est un
  candidat lourd pour la phase d'industrialisation (à budgéter en temps de
  crawl ~3h et en espace disque HTML).

## Intérêt pour le mémoire

20minutes.fr est un témoin utile de la presse gratuite nationale : détenu à
parts égales par le groupe belge Rossel et le groupe Ouest-France depuis le
rachat des parts de Schibsted (2015-2016), après une histoire de
recompositions actionnariales (Schibsted/Ouest-France/Sipa-Ouest-France
depuis le lancement en 2002). Contrairement aux candidats « cas d'école »
(CNews/Bolloré), 20minutes apporte surtout de la profondeur (20 ans
d'archives, 2006-2026) et un volume important pour des comparaisons de
référence entre médias rachetés et médias au capital plus stable — un bon
complément statistique plutôt qu'un cas de rupture isolée à lui seul.

## Fichiers produits par ce dossier

- `exploration/mapping_20minutes.py` : script de mapping complet
  (2006-2026, structure page-année → page-jour validée par smoke-test),
  prêt à lancer mais **non lancé** (mapping complet interdit dans le cadre
  de cette mission).
- `exploration/prospection/20minutes.md` : ce dossier.

Aucun fichier de `scraping/` n'a été modifié ; `medias.py` n'a pas été
touché ; le mapping complet n'a pas été lancé.
