"""Construit la liste des URLs d'articles Closer (closermag.fr) via l'index de
sitemaps Yoast WordPress https://www.closermag.fr/sitemap_index.xml. Parmi les
8 types de fichiers references dans l'index (post/page/category/author/...),
seuls les post-sitemap*.xml contiennent des articles : post-sitemap.xml (1er
chunk) puis post-sitemap2.xml -> post-sitemap220.xml (le dernier partiel),
~1000 URLs chacun -> ~219 000 articles au total (repere lors de la reco).
Format article : https://www.closermag.fr/<rubrique>/<slug>-<id>.

Attention : le <lastmod> du sitemap est trompeur (reindexation massive de mai
2023 sur tout l'historique) -- ne pas s'y fier pour dater les articles, seul
le datePublished json-ld dans la page fait foi.

~221 requetes (1 index + ~220 post-sitemaps) a 1.5s de politesse -> ~7 min.

    python -m mapping.closermag

Relancable : le fichier de sortie est complete par ajout (pas ecrase), les
URLs deja presentes sont chargees au demarrage et jamais redemandees.
"""
import csv
import os
import re
import time

from scraping import basic

INDEX = "https://www.closermag.fr/sitemap_index.xml"
SORTIE = "exploration/closermag_url.csv"
MOTIF_SOUS_SITEMAP = re.compile(r"<loc>(https://www\.closermag\.fr/post-sitemap(\d*)\.xml)</loc>")
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
ATTENTE = 1.5  # secondes, politesse envers le serveur

session = basic.ouvrir_session()

r = session.get(INDEX, timeout=30)
r.raise_for_status()
sous_sitemaps = sorted(
    set(MOTIF_SOUS_SITEMAP.findall(r.text)),
    key=lambda t: int(t[1]) if t[1] else 1,
)
print(f"{len(sous_sitemaps)} post-sitemaps a parcourir")

deja = set()
if os.path.exists(SORTIE):  # reprise : les URLs deja ecrites ne sont pas redemandees
    with open(SORTIE, newline="", encoding="utf-8") as f:
        deja.update(l[0] for l in list(csv.reader(f))[1:] if l)
    print(f"{len(deja)} URLs deja presentes dans {SORTIE}")

nouveau_fichier = not os.path.exists(SORTIE)
sortie = open(SORTIE, "a", newline="", encoding="utf-8")
w = csv.writer(sortie)
if nouveau_fichier:
    w.writerow(["url"])

echecs = 0
for i, (sm, _n) in enumerate(sous_sitemaps, 1):
    try:
        r = session.get(sm, timeout=30)
        if r.status_code == 404:
            print(f"{sm} : 404, ignore")
            echecs += 1
            time.sleep(ATTENTE)
            continue
        r.raise_for_status()
    except Exception as e:
        print(f"{sm} : echec ({e}), ignore")
        echecs += 1
        time.sleep(ATTENTE)
        continue

    nouvelles = set(MOTIF_LOC.findall(r.text)) - deja
    for u in nouvelles:
        w.writerow([u])
    sortie.flush()  # ecriture au fil de l'eau : reprise facile en cas d'interruption
    deja.update(nouvelles)

    if i % 10 == 0:
        print(f"{i}/{len(sous_sitemaps)} sitemaps : {len(deja)} URLs cumulees, {echecs} echecs")

    time.sleep(ATTENTE)

sortie.close()
print(f"Termine : {len(deja)} URLs dans {SORTIE}, {echecs} sitemaps en echec")
