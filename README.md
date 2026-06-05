# stage-mids

Mémoire de fin de master — Analyse de l'impact des rachats de journaux français sur le contenu éditorial.

## Question de recherche

Les rachats de journaux français modifient-ils la couverture thématique des articles ?

## Structure du dépôt

```
stage-mids/
├── scraping/              # le code du scraping (package importable)
│   ├── navigateur.py      # Firefox headless + bypass paywall + uBlock
│   ├── batch.py           # constitution d'un batch d'URLs depuis la BDD
│   ├── extraction.py      # extraction des métadonnées + corps d'un article
│   ├── paywall.py         # détection des articles tronqués (est_bloque)
│   ├── stockage.py        # écriture des CSV + mise à jour de l'état en base
│   └── pipeline.py        # orchestration (ouvre, scrape, extrait, écrit)
│
├── scripts/              # préparation, à lancer une fois dans l'ordre
│   ├── 1_telecharger_donnees.py   # télécharge les URLs depuis Hugging Face
│   ├── 2_creer_bdd.py             # crée la base sqlite urls.db
│   ├── 3_importer_csv.py          # importe les URLs dans la base
│   └── creer_csv.py               # crée les CSV de sortie (un par média)
│
├── exploration/          # prototypes et tests (référence, hors prod)
├── notebooks/            # notebooks d'analyse
└── extensions/           # extensions Firefox (.xpi) — présentes sur le serveur
```

Les données (CSV, base `urls.db`) et les extensions vivent sur le serveur,
sous `/data/elias/stage-mids/`. Les chemins serveur sont définis dans
[scraping/stockage.py](scraping/stockage.py) (`DATA_DIR`) et
[scraping/navigateur.py](scraping/navigateur.py) (`RACINE`).

## Installation

```bash
# Cloner le dépôt
git clone <url-du-dépôt>
cd stage-mids

# Créer l'environnement et installer les dépendances (uv)
uv venv
uv pip install -r requirements.txt
```

## Utilisation

Préparation de la base (une seule fois, dans l'ordre) :

```bash
python scripts/1_telecharger_donnees.py
python scripts/2_creer_bdd.py
python scripts/3_importer_csv.py
python scripts/creer_csv.py
```

Lancer le scraping :

```bash
python -m scraping.pipeline
```
