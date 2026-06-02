# stage-mids

Mémoire de fin de master — Analyse de l'impact des rachats de journaux français sur le contenu éditorial.

## Question de recherche

Les rachats de journaux français modifient-ils la couverture thématique des articles ?

## Structure du dépôt

```
stage-mids/
├── scraping/              # le code du scraping (package importable)
│   ├── config.py          # tous les chemins serveur + la liste des médias
│   ├── navigateur.py      # Firefox headless + bypass paywall + uBlock
│   ├── batch.py           # constitution d'un batch d'URLs depuis la BDD
│   ├── stockage.py        # écriture des CSV + mise à jour de l'état en base
│   └── pipeline.py        # orchestration (ouvre, scrape, écrit)
│
├── scripts/              # préparation, à lancer une fois dans l'ordre
│   ├── 1_telecharger_donnees.py   # télécharge les URLs depuis Hugging Face
│   ├── 2_creer_bdd.py             # crée la base sqlite urls.db
│   ├── 3_importer_csv.py          # importe les URLs dans la base
│   └── 4_init_csv_sortie.py       # crée les CSV de sortie (un par média)
│
├── lancer_scraping.py    # point d'entrée du scraping
├── exploration/          # prototypes et tests (référence, hors prod)
├── notebooks/            # notebooks d'analyse
└── extensions/           # extensions Firefox (.xpi) — présentes sur le serveur
```

Les données (CSV, base `urls.db`) et les extensions vivent sur le serveur,
sous `/data/elias/stage-mids/`. Leurs chemins sont centralisés dans
[scraping/config.py](scraping/config.py).

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
python scripts/4_init_csv_sortie.py
```

Lancer le scraping :

```bash
python lancer_scraping.py
```
