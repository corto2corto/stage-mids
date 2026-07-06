"""Construit la liste des URLs d'articles Le Point via l'API CDX de la
Wayback Machine (web.archive.org). Choix impose par la reco : DataDome
bloque robots.txt, /archives/ et les pages de rubriques meme en Firefox
headless (interstitiel), et le site n'expose aucun sitemap -- le CDX liste
toutes les captures archivees sans toucher lepoint.fr. Fenetre from=2010
(temoin long). Motif article : ...-JJ-MM-AAAA-ID_NN.php.

    python -m exploration.mapping_lepoint

MAPPING_LIMITE=N (env) : ne parcourt que 3xN pages d'index reparties (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

CDX = "http://web.archive.org/cdx/search/cdx"
DOMAINE = "www.lepoint.fr"
PERIODE = {"from": "2010"}
SORTIE = "exploration/lepoint_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}
MOTIF_ARTICLE = re.compile(r"^https://www\.lepoint\.fr/.+-\d{2}-\d{2}-\d{4}-\d+_\d+\.php$")

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

urls = set()
for i, page in enumerate(tqdm(pages), 1):
    texte = ""
    for tentative in range(3):
        try:
            r = requests.get(CDX, params={"url": DOMAINE, "matchType": "host", "page": page, "pageSize": "5",
                                          "fl": "original", "filter": ["statuscode:200", "mimetype:text/html"],
                                          "collapse": "urlkey", **PERIODE},
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
