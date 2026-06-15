#!/usr/bin/env bash
# Régénère la page de suivi (tendance) et la publie sur GitHub Pages.
#
# À lancer SUR LE SERVEUR, en boucle toutes les 10 min (voir README en bas).
# Réutilise `python -m scripts.suivi tendance` ; ne pousse que `index.html`
# (page autonome, aucune donnée brute d'article) sur la branche `gh-pages`.
#
# Pré-requis (une seule fois) :
#   cd /data/elias && git clone git@github.com:corto2corto/stage-mids.git stage-mids-pages
#   cd stage-mids-pages && git checkout --orphan gh-pages
#   git rm -rf . >/dev/null 2>&1 || true ; touch .nojekyll
#   git add .nojekyll && git commit -m "init gh-pages" && git push -u origin gh-pages
# Puis activer GitHub Pages : Settings > Pages > branche gh-pages, dossier / (root).
# Lancer en boucle (dans un tmux) :
#   while true; do bash scripts/publier_suivi.sh; sleep 600; done

set -eo pipefail

REPO=/data/elias/stage-mids          # dépôt du scraping (venv + scripts)
PAGES=/data/elias/stage-mids-pages   # clone dédié, sur la branche gh-pages

cd "$REPO"
source .venv/bin/activate
python -m scripts.suivi tendance     # écrit data/tendance.html

cp data/tendance.html "$PAGES/index.html"
cd "$PAGES"
git add index.html
# Page identique au dernier commit (pas de nouvel instantané) : rien à publier.
if git diff --cached --quiet -- index.html; then
    exit 0
fi
# On garde un seul commit sur gh-pages (amende + force-push) : l'historique
# ne gonfle pas malgré une publication toutes les 10 min.
git commit --amend --no-edit -q
git push -f -q origin gh-pages
echo "Page publiée : $(date '+%H:%M:%S')"
