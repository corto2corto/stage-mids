"""Construit la liste des URLs d'articles 20minutes.fr via les pages
d'archives datees https://www.20minutes.fr/archives/YYYY/MM-DD (liens HTML
bruts, sans JS, sans pagination -- reperees lors de la reco). Chaque page
annuelle https://www.20minutes.fr/archives/YYYY liste les 365/366 jours de
l'annee (verifie lors du smoke-test manager : /archives/2015 contient bien
365 href /archives/2015/MM-DD). Chaque page-jour melange les articles du
jour avec des encarts "plus lus" d'autres dates -- on ne garde que les liens
dont le slug contient -YYYYMMDD- egal au jour de la page. Format article :
https://www.20minutes.fr/<rubrique>[/<sous-rubrique>]/<ID>-<YYYYMMDD>-<slug>.

2006 -> 2026 : ~7 400 pages-jour + 21 pages-annee, soit ~7 420 requetes a 1 s
de politesse -> environ 3h de crawl.

    python -m exploration.mapping_20minutes            # tout, 2006 -> 2026
    python -m exploration.mapping_20minutes 2026       # rattrapage d'une annee

Relancable par annee : passer en argument les annees manquantes/interrompues
(ou a rattraper) -- le fichier de sortie est complete par ajout (pas ecrase),
les URLs deja presentes sont chargees au demarrage et jamais reecrites.
"""
import csv
import os
import re
import sys
import time

from tqdm import tqdm

from scraping import basic

ANNEES = [int(a) for a in sys.argv[1:]] or range(2006, 2027)  # 2006 -> 2026 inclus
SORTIE = "exploration/20minutes_url.csv"
MOTIF_JOUR = re.compile(r'href="https://www\.20minutes\.fr/archives/(\d{4})/(\d{2})-(\d{2})"')
MOTIF_ARTICLE = re.compile(
    r'href="(https://www\.20minutes\.fr/[a-z0-9\-/]+/\d+-(\d{8})-[a-z0-9\-]+)"'
)

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

session = basic.ouvrir_session()

for annee in ANNEES:
    r = session.get(f"https://www.20minutes.fr/archives/{annee}", timeout=30)
    r.raise_for_status()
    jours = sorted(set((a, m, j) for a, m, j in MOTIF_JOUR.findall(r.text) if a == str(annee)))
    print(f"{annee} : {len(jours)} jours a parcourir")
    time.sleep(1)  # politesse envers le serveur

    mois_courant, urls_mois = None, 0
    for a, m, j in tqdm(jours, desc=str(annee)):
        page = f"https://www.20minutes.fr/archives/{a}/{m}-{j}"
        try:
            r = session.get(page, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"{page} : echec ({e}), ignoree")
            time.sleep(1)
            continue

        if m != mois_courant:  # progression par mois
            if mois_courant is not None:
                print(f"{a}-{mois_courant} : {urls_mois} URLs, {len(deja)} cumulees")
            mois_courant, urls_mois = m, 0

        jour_compact = f"{a}{m}{j}"
        nouvelles = {u for u, d in MOTIF_ARTICLE.findall(r.text) if d == jour_compact} - deja
        for u in nouvelles:
            w.writerow([u])
        sortie.flush()  # ecriture au fil de l'eau : reprise facile en cas d'interruption
        deja.update(nouvelles)
        urls_mois += len(nouvelles)

        time.sleep(1)  # politesse envers le serveur
    print(f"{a}-{mois_courant} : {urls_mois} URLs, {len(deja)} cumulees")

sortie.close()
print(f"Termine : {len(deja)} URLs dans {SORTIE}")
