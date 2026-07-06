# stage-mids

Mémoire de fin de master — Analyse de l'impact des rachats de journaux français sur le contenu éditorial.

## Question de recherche

Les rachats de journaux français modifient-ils la couverture thématique des articles ?

## Structure du dépôt

```
stage-mids/
├── scraping/       # le code du scraping (Firefox headless + bypass paywall)
├── scripts/        # scripts serveur : init de la base (1 à 4), bases ngram, suivi, lancer.sh
├── api/            # API Flask type Gallicagram (courbes ngram) + front
├── site/           # dashboard de suivi Evidence, publié sur GitHub Pages
├── exploration/    # prototypes, diagnostics, détail des métadonnées par média
├── notebooks/      # notebooks d'analyse
└── extensions/     # extensions Firefox (.xpi) — présentes sur le serveur
```

Les données (CSV, bases SQLite) vivent sur le serveur, sous `/data/elias/stage-mids/data/`.

## Installation

```bash
git clone https://github.com/corto2corto/stage-mids
cd stage-mids
uv venv
uv pip install -r requirements.txt
```

## Utilisation

Préparation de la base (une seule fois, dans l'ordre) : `python scripts/1_telecharger_donnees.py` puis `2_creer_bdd.py`, `3_creer_csv.py`, `4_marquer_doublons.py`.

Scraping en continu (sur le serveur, dans la session tmux `scrapping`) :

```bash
bash scripts/lancer.sh
```

API ngram (sur le serveur, puis tunnel ssh vers localhost:8501) :

```bash
python -m api.app
```
