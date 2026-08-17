# stage-mids

Mémoire de fin de master — Analyse de l'impact des rachats de journaux français sur le contenu éditorial.

## Question de recherche

Les rachats de journaux français modifient-ils la couverture thématique des articles ?

## La chaîne, de bout en bout

1. **Mapping** (`mapping/`) — pour chaque journal, dresser la liste des URLs de ses articles.
2. **Scraping** (`scraping/`) — visiter ces URLs, en extraire titre, date et corps.
3. **Bases ngram** (`scripts/`) — compter les uni/bi/trigrammes jour par jour, avec le total de mots du jour.
4. **API** (`api/`) — servir les courbes de fréquence, à la manière de Gallicagram.
5. **Rupture** (`rupture/`) — ajuster une loi de comptage, détecter les pics, construire le dataset de sauts.

## Structure du dépôt

```
stage-mids/
├── mapping/        # listes d'URLs par média : moteur générique (5 méthodes) + catalogue de fiches
├── scraping/       # moteurs (Firefox+bypass, compte abonné, requête HTTP) et pipeline, un thread par média
├── scripts/        # serveur : init de la base (1 à 4), cycle sitemaps (cron), bases ngram, suivi, lancer.sh
├── api/            # API Flask type Gallicagram (/query, /top, /evolution, /fiche) + front
├── rupture/        # détection de pics et de ruptures (briques extraire → serie → pics → fenetres)
├── paper/          # le mémoire (main.tex), la feuille de route maths (to_do.md), les rapports chiffrés
├── exploration/    # prototypes, diagnostics, détail des métadonnées par média, notebooks/
├── site/           # suivi Evidence (GitHub Pages) + dashboard local site/static/dashboard.html
├── tests/          # pytest des moteurs de scraping (doublures, sans réseau ni Firefox)
└── extensions/     # extensions Firefox (.xpi) — présentes sur le serveur
```

Les données (CSV d'articles, bases SQLite) vivent sur le serveur, sous `/data/elias/stage-mids/data/`.

Documents à la racine : `journal.md` (journal de bord), `paper/to_do.md` (l'état des tâches maths, section par section), `interpretation.md` (lecture des fiches et choix de modèles), `plan.md`, `recommandation.md` (audit du dépôt, 11/07/2026).

## Où en est le projet (juillet 2026)

- **Corpus** — 32 médias branchés au scraping, tournant en continu sur le serveur ; les URLs récentes arrivent chaque jour par les sitemaps *news*, les archives par le mapping.
- **Bases ngram** — trois journaux disponibles : Le Monde (1944 → 2025, ~26 900 jours de parution), Le Figaro (2004 → 2024), Les Échos (1991 → 2024), avec mise à jour quotidienne incrémentale.
- **Détection de pics** — modèle acté : mélange Bernoulli × binomiale négative décalée (les jours à zéro cassaient l'ajustement), avec double fit (retirer les jours évidents, réajuster sur le bulk). Validé sur 20 mots (`paper/donnees_maths/fiches_bnb.pdf`, `double_fit.pdf`).
- **Phase 3, en cours** — dataset de sauts : top-10 000 mots du Monde par jours actifs, matrice de séries extraite (`rupture/masse.py`), détection des pics sur tout le vocabulaire (`rupture/pics_masse.py`), puis dédoublonnage NMS (`rupture/nms.py`), normalisation des fenêtres et PCA.

## Installation

```bash
git clone https://github.com/corto2corto/stage-mids
cd stage-mids
uv venv
uv pip install -r requirements.txt
```

## Le site de suivi

**<https://corto2corto.github.io/stage-mids>** — la collecte du corpus, en chiffres et mise à jour chaque jour.

- **Avancement** : où en est le scraping de chaque média, combien d'articles restent à récupérer.
- **Taux de réussite** : part des articles réellement récupérés, par média, sur 24 h, 72 h et depuis le début.
- **Évolution** : les courbes de taux de réussite dans le temps, à comparer entre médias.
- **Collecte des sitemaps** : les nouvelles URLs ajoutées à la file, à chacun des deux passages quotidiens.

Le site est construit avec [Evidence](https://evidence.dev) (dossier `site/`) et publié par GitHub Actions ; ses données viennent de trois CSV rafraîchis chaque nuit depuis le serveur.

## Bientôt en ligne : l'API des résultats

Les principaux résultats — nombre d'occurrences d'un mot jour par jour, fréquences, tops, pics détectés — seront **prochainement accessibles en ligne** via une API publique et son interface de courbes (`api/`), à la manière de [Gallicagram](https://shiny.ens-paris-saclay.fr/app/gallicagram). C'est par là qu'il faudra passer pour explorer le corpus : le dépôt, lui, documente sa construction.

## Licence

Aucune licence ouverte n'est accordée : **© Corto — tous droits réservés**.

Ce dépôt est publié pour consultation et pour rendre la démarche vérifiable, pas pour être réutilisé ou reproduit. Le code, les documents et les résultats ne peuvent être copiés, modifiés, redistribués ni exploités sans autorisation écrite. Le corpus d'articles n'est pas distribué : les articles restent la propriété de leurs éditeurs.
