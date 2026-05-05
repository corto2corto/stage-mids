# stage-mids

Mémoire de fin de master — Analyse de l'impact des rachats de journaux français sur le contenu éditorial via la détection de ruptures sémantiques.

## Question de recherche

Les rachats de journaux français modifient-ils la couverture thématique des articles ? Certains sujets émergent-ils ou disparaissent-ils après un changement de propriétaire ?

## Démarche

1. **Scrapping local** (prototypage) — collecte d'articles sur quelques journaux ciblés
2. **Adaptation par source** — chaque site a sa structure, donc un scrapper par journal
3. **Industrialisation sur serveur** — passage à l'échelle
4. **Détection de ruptures sémantiques** — application de modèles statistiques pour mesurer les changements thématiques pré/post rachat

## Structure du dépôt

```
stage-mids/
├── journal/         # Journal de bord (Quarto .qmd)
├── scrapers/        # Un sous-dossier par journal
├── data/            # Données scrappées (NON versionnées)
│   ├── raw/         # Articles bruts
│   └── processed/   # Articles nettoyés
├── analysis/        # Scripts d'analyse, modèles de rupture
├── notebooks/       # Exploration interactive (Jupyter)
└── docs/            # Notes méthodo, rédaction du mémoire
```

## Installation

```bash
# Cloner le dépôt
git clone <url-du-dépôt>
cd stage-mids

# Créer un environnement virtuel
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## Données

Les données scrappées ne sont **pas versionnées** (volume + droits d'auteur). Elles sont stockées localement dans `data/` et sauvegardées séparément.

## Auteur

Corto — Master MIDS
