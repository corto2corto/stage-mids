# Règles d'identification des URLs non-articles (etat=5)

Corpus de référence pour les futurs filtres en amont (mapping, chargement, sitemaps).
Issu de l'audit des motifs d'URLs du 11/07/2026 et des tests de calibration du 12/07/2026.

**État dédié : etat=5** (« hors corpus / non-article », cf scraping/stockage.py). Le pipeline ne
consomme que les états 0 et 1 : une URL en 5 ne sera plus jamais scrapée. Chaque marquage a sa
sauvegarde de réversibilité dans data/backup/ (media, id, url).

Principe de calibration : **ne jamais filtrer sur la présence d'un mot dans le slug** (video,
podcast, rss, auteur, diaporama, galerie… abondent dans des titres d'articles légitimes) ; une
règle porte sur un sous-domaine, un segment de chemin ou une extension, et se valide sur
échantillons avant tout marquage. En cas de doute on garde : un faux article coûte un échec de
scraping, un vrai article perdu ne se rattrape pas.

## Règles appliquées (marquages faits)

| média | règle | URLs marquées | date |
|---|---|---:|---|
| le_figaro | sous-domaine `video.lefigaro.fr/` | 233 946 | 11/07 |
| le_monde | tout sauf segment `/article/` (resultats-*, podcasts., /live/, /visuel/) | 56 308 | 11/07 |
| le_monde | pages resultats-* historiques (etat=5 initial) | 51 400 | avant 11/07 |
| challenges | etat=4 complets : diaporamas/fiches sans `articleBody` | 21 903 | 11/07 |
| l_opinion | etat=4 complets : `theme/`, `dossiers`, `auteur/`, concours, `.xml` + corps perdus côté site (confirmé sonde Firefox) | 14 556 | 11/07 |
| latribune | etat=4 complets : artefacts Wayback (`.jpg`, `=`, `&`, `width=`, `format=`) — 100 % vérifiés porteurs d'un motif | 29 228 | 12/07 |
| le_nouvel_observateur | segment `/galeries-photos/` (zéro capturée en CSV) | 8 157 | 12/07 |
| les_echos | segment `/internal/` (vidéos, pages de service) | 2 024 | 11/07 |
| le_journal_du_dimanche | segment `/sommaire/` (sommaires du magazine) | 220 | 11/07 |
| laprovence | motifs `image:media`, `httpRequest`, `%20http` (artefacts de mapping) | 123 | 12/07 |
| telerama | 4 URLs malformées exactes (racine, `//`, `/,n…`, `/node/`) | 4 | 12/07 |
| ouest_france | 1 URL au slug ayant avalé une autre URL (id 33696945) | 1 | 12/07 |

## Règles testées et ÉCARTÉES (à ne pas réappliquer sans nouveau test)

- **le_telegramme — slugs à markup `span`** : 1 885 871 URLs (et non ~72 k estimés à l'audit).
  Test des doublons par ID d'article (`-NNNNNN.php`) sur les 4,6 M d'URLs du média : **zéro
  jumeau au slug propre** — ce sont les seules entrées de ces articles — et 48 763 sont déjà
  scrapées avec succès. Slugs sales mais vrais articles uniques : **on garde tout**.
- **gala — pages `video-`** (~20 900 en etat=0) : les 202 déjà capturées font 262 mots en
  médiane ~256, et 3 sondes en direct donnent 295-474 mots de texte éditorial réel. Vrais
  articles people avec vidéo intégrée : **on garde**. Même verdict pour voici (~12 700),
  valeurs_actuelles (~3 400) et francesoir (~1 400), déjà capturées avec contenu.
- **atlantico — slugs `http--`** (URL étrangère avalée, ~5-10 estimées) : le seul motif SQL
  testé n'a attrapé qu'un faux positif (article « rgpd-et-https--… »). Volume négligeable,
  motif non fiable : **on ne touche pas**.

## Médias sains (audit 11/07 : rien à nettoyer)

marianne, le_capital, challenges (file active), francesoir, le_journal_du_dimanche (hors
/sommaire/), mediapart, bfmtv, la_croix, leparisien, les_echos (hors /internal/), sud_ouest,
midilibre, la_depeche, ouest_france, nice_matin, paris_match, paris_normandie, telerama,
valeurs_actuelles, voici, gala, atlantico, le_telegramme, latribune (file active), l_opinion
(file vide), le_monde (file vide). Leurs comptes `video`/`direct`/`rss`/`galerie` sont des mots
de slugs légitimes.

## Motifs à bloquer en amont (mapping / chargement / sitemaps)

- Sous-domaines non éditoriaux : `video.<domaine>`, `podcasts.<domaine>`.
- Segments : `/galeries-photos/`, `/internal/`, `/sommaire/` (jdd), `/theme/`, `/auteur/`,
  `resultats-*` (le_monde), `/live/` et `/visuel/` (le_monde : garder seulement `/article/`).
- Extensions fichier : `.jpg .jpeg .png .webp .gif .pdf .mp3 .mp4 .xml`.
- Artefacts : `image:media`, `httpRequest`, `width=`, `format=`, URL avalant une autre URL
  (`%20http`, `http…http`), racine du site seule.
