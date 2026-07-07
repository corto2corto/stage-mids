"""Construit la liste des URLs d'articles CNews par pagination du sitemap
index (https://www.cnews.fr/sitemap.xml?page=1..215, ~2000 URLs par page,
215 pages recensees lors de la reco, ~430 000 URLs au total dont ~45 %
d'articles textuels). Garde uniquement les URLs d'articles dates de la forme
/{rubrique}/{YYYY-MM-DD}/{slug}[-ID], exclut les prefixes videos/, podcast/,
emission/, diaporamas/ ainsi que les pages statiques sans date. Sur la page 1
(debut d'archive, 2012-02-17), une dizaine d'articles n'ont pas de segment
rubrique (/{YYYY-MM-DD}/{slug} au lieu de /{rubrique}/{YYYY-MM-DD}/{slug}) --
constate lors du smoke test, le motif accepte donc la rubrique en optionnelle.
robots.txt impose un Crawl-delay de 10s -> ~36 min pour les 215 pages
(215 * 10s + temps requete).

    python -m exploration.mapping_cnews
"""
import csv
import re
import time

from scraping import basic

INDEX = "https://www.cnews.fr/sitemap.xml"
SORTIE = "exploration/cnews_url.csv"
MAX_PAGES = 300  # garde-fou : 215 pages recensees lors de la reco
ATTENTE = 10  # secondes, impose par le Crawl-delay du robots.txt
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
MOTIF_ARTICLE = re.compile(
    r"^https://www\.cnews\.fr/(?:(?!videos/|podcast/|emission/|diaporamas/)[^/]+/)?\d{4}-\d{2}-\d{2}/[^/]+/?$"
)

session = basic.ouvrir_session()
urls = set()
rejetees = 0
pages_vides = 0

for page in range(1, MAX_PAGES + 1):
    try:
        r = session.get(INDEX, params={"page": page}, timeout=20)
    except Exception as e:
        print(f"page {page} : echec ({e}), ignoree")
        pages_vides += 1
        if pages_vides >= 2:
            print(f"arret a la page {page} apres 2 echecs consecutifs")
            break
        time.sleep(ATTENTE)
        continue

    if r.status_code == 404:
        print(f"page {page} : 404, fin du sitemap")
        break

    locs = MOTIF_LOC.findall(r.text)
    if not locs:
        pages_vides += 1
        print(f"page {page} : vide")
        if pages_vides >= 2:
            print(f"arret a la page {page} apres 2 pages vides consecutives")
            break
        time.sleep(ATTENTE)
        continue
    pages_vides = 0

    for loc in locs:
        if MOTIF_ARTICLE.match(loc):
            urls.add(loc)
        else:
            rejetees += 1

    if page % 10 == 0:
        print(f"page {page}/{MAX_PAGES} : {len(urls)} URLs cumulees, {rejetees} rejetees")
        with open(SORTIE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["url"])
            for u in sorted(urls):
                w.writerow([u])

    time.sleep(ATTENTE)

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"Termine : {len(urls)} URLs retenues, {rejetees} rejetees, ecrites dans {SORTIE}")
