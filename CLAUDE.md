# Memory

## Me
Corto, étudiant en master. Email: kalice.ecr@gmail.com

## Projet principal
**Mémoire de fin de master** — Analyse de l'impact des rachats de journaux français sur le contenu éditorial, via la détection de ruptures sémantiques.

### Étapes
1. Scrapper des articles de journaux en local (prototypage) — **en cours**
2. Identifier la méthode de scrapping adaptée à chaque journal (chaque site a sa structure)
3. Passer le scrapping sur des serveurs (industrialisation)
4. Appliquer des modèles mathématiques de détection de ruptures sémantiques (modèles à définir) pour mesurer si certains sujets émergent ou disparaissent après un rachat

### Notes
- Liste des journaux : à préciser
- Liste des modèles de rupture : sera fournie plus tard
- Question de recherche : les rachats de journaux français modifient-ils la couverture thématique ?

## Stack technique
- **Selenium** + `chromedriver_binary` pour le scraping
- **Python**, exécuté sur un serveur Linux (`/data/elias/stage-mids/`)
- Profil Chrome modèle stocké dans `extensions/chrome-bpc/` — copié en temp à chaque session pour charger les extensions (bypass paywall)
- Mode `--headless` obligatoire sur le serveur

## Problème en cours — Profil Chrome + extensions en headless
L'objectif est de lancer Chrome via Selenium avec un profil personnalisé contenant des extensions (bypass-paywalls-chrome-clean), pour scraper des articles derrière paywall.

**Approche actuelle** (`t3_profil_chrome.py`, `test1_bypass_chrome.py`) :
- Copie du profil modèle `chrome-bpc` dans un dossier temporaire via `shutil.copytree`
- Passage du profil via `--user-data-dir`
- Chrome lancé en headless avec `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`

**Problème** : les extensions ne semblent pas actives en mode headless. Chrome headless (nouveau mode) ne charge pas les extensions par défaut. Le HTML récupéré est celui de la page avec paywall, pas le contenu complet.

**Pistes à explorer** :
- Utiliser `--headless=new` vs ancien headless (le comportement diffère)
- Tester avec `--load-extension=/chemin/vers/extension` en plus du profil
- Vérifier si l'extension bypass-paywalls fonctionne réellement en headless (certaines extensions nécessitent un affichage)
- Alternative : utiliser un proxy ou une autre méthode de bypass si les extensions ne peuvent pas fonctionner en headless

## Structure du projet
```
stage-mids/
├── data/
│   └── test/
│       ├── t1_ouvrir_chrome.py       # Test basique : ouvrir Chrome headless
│       ├── t2_wikipedia.py           # Test : naviguer vers Wikipedia
│       ├── t3_profil_chrome.py       # Test : charger profil Chrome avec extensions
│       └── test1_bypass_chrome.py    # Test complet : scraper Le Figaro avec bypass
├── extensions/
│   └── chrome-bpc/                   # Profil Chrome modèle avec extensions installées
└── .claude/
    └── skills/
        └── maj/                      # Skill /maj : git add + commit auto + push
```

## Outils
- Notion (connecté)
- Google Tasks (pas de connecteur dispo)

## Preferences
- Parler en français
 