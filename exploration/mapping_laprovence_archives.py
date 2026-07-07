"""Complete laprovence_url.csv (limite au recent : la pagination page-N ne
sert que ~5-7 pages par rubrique avant de re-servir la page 1, cf
mapping_laprovence -- ~12k URLs) avec l'historique via l'API CDX de la
Wayback Machine. Deux formats d'articles au fil des refontes :
- /article/<rubrique>/<id>/<slug> (ancien avec .html, nouveau sans),
- /actu/en-direct/<id>/<slug>.html (anciennes breves, vraies pages) ;
le wrapper moderne /actu/en-direct/<id>/article/... est exclu (doublon du
canonique /article/...).

FUSIONNE le resultat avec le laprovence_url.csv existant (union) -- si
mapping_laprovence est relance apres coup, il ecrase le fichier et ce
script est a relancer.

    python -m exploration.mapping_laprovence_archives

MAPPING_LIMITE=N (env) : ne parcourt que 3xN pages d'index reparties (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

CDX = "http://web.archive.org/cdx/search/cdx"
DOMAINE = "www.laprovence.com"
SORTIE = "exploration/laprovence_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}
MOTIF_ARTICLE = re.compile(
    r"^https://www\.laprovence\.com/(?:article/.+|actu/en-direct/\d+/[^/]+\.html)$")

urls = set()
if os.path.exists(SORTIE):  # union avec le mapping pagination deja fait
    with open(SORTIE, newline="", encoding="utf-8") as f:
        urls.update(l[0] for l in list(csv.reader(f))[1:] if l)
    print(f"{len(urls)} URLs deja presentes dans {SORTIE}")

r = requests.get(CDX, params={"url": DOMAINE, "matchType": "host", "showNumPages": "true", "pageSize": "5"},
                 headers=ENTETES, timeout=60)
r.raise_for_status()
nb_pages = int(r.text.strip())
pages = list(range(nb_pages))
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    # 3x limite sondes reparties : l'index est clairseme apres filtres (zones creuses)
    pages = pages[::max(1, nb_pages // (3 * limite))][:3 * limite]
print(f"{nb_pages} pages d'index CDX a parcourir")

for i, page in enumerate(tqdm(pages), 1):
    texte = ""
    for tentative in range(3):
        try:
            r = requests.get(CDX, params={"url": DOMAINE, "matchType": "host", "page": page, "pageSize": "5",
                                          "fl": "original", "filter": ["statuscode:200", "mimetype:text/html"],
                                          "collapse": "urlkey"},
                             headers=ENTETES, timeout=180)
            r.raise_for_status()
            texte = r.text
            if texte.strip() or tentative == 2:
                break  # page reellement vide apres 3 essais : zone creuse de l'index
            print(f"page {page} tentative {tentative + 1} : reponse vide, on reessaie")
        except requests.RequestException as e:
            print(f"page {page} tentative {tentative + 1} : echec ({e})")
        time.sleep(10 * (tentative + 1))  # l'API CDX throttle par moments
    for brute in texte.splitlines():
        u = brute.split("?")[0].split("#")[0].replace("http://", "https://").replace(":80/", "/")
        if MOTIF_ARTICLE.match(u):
            urls.add(u)
    if i % 50 == 0:  # checkpoint
        with open(SORTIE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["url"])
            for u in sorted(urls):
                w.writerow([u])
    time.sleep(1)  # politesse envers l'API

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
