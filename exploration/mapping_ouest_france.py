"""Construit la liste des URLs d'articles Ouest-France via ses ~179 sitemaps
sitemap-articles-ouest-france-N.xml (2007 -> aujourd'hui, ~45k URLs chacun,
plusieurs millions au total). Particularite reperee lors de la reco : le site
(DataDome) ne sert ces sitemaps qu'a un vrai navigateur -- curl et requests
recoivent la home a la place. On passe donc par le Firefox headless du projet
(scraping.navigateur), une page XML a la fois.

    python -m exploration.mapping_ouest_france

MAPPING_LIMITE=N (env) : ne parcourt que les N derniers sitemaps (smoke test).
"""
import csv
import os
import re

from tqdm import tqdm

from scraping.navigateur import ouvrir_firefox, scraper

INDEX = "https://www.ouest-france.fr/sitemap.xml"
SORTIE = "exploration/ouest_france_url.csv"
MOTIF_SOUS_SITEMAP = re.compile(r"sitemap-articles-ouest-france-\d+\.xml")
MOTIF_LOC = re.compile(r"<loc>(https://www\.ouest-france\.fr/[^<]+)</loc>")

driver = ouvrir_firefox()
try:
    # les reponses DataDome sont parfois tres lentes : delai de page large et
    # 3 tentatives sur l'index (un echec ici condamnerait tout le mapping)
    driver.set_page_load_timeout(120)
    html = ""
    for tentative in range(3):
        try:
            html = scraper(driver, INDEX, attente=3)
            if MOTIF_SOUS_SITEMAP.search(html):
                break
        except Exception as e:
            print(f"index tentative {tentative + 1} : echec ({type(e).__name__})")
    sous_sitemaps = sorted(
        set("https://www.ouest-france.fr/" + s for s in MOTIF_SOUS_SITEMAP.findall(html)),
        key=lambda u: int(re.search(r"-(\d+)\.xml", u).group(1)),
    )
    limite = int(os.environ.get("MAPPING_LIMITE", "0"))
    if limite:
        sous_sitemaps = sous_sitemaps[-limite:]
    print(f"{len(sous_sitemaps)} sitemaps articles a parcourir")

    urls = set()
    for i, sm in enumerate(tqdm(sous_sitemaps), 1):
        try:
            html = scraper(driver, sm, attente=2)
        except Exception as e:
            print(f"{sm} : echec ({type(e).__name__}), ignore")
            continue
        # strip query/fragment (ex. liseuse "leditiondusoir" : reader.html?t=...#!...)
        urls.update(
            propre for u in MOTIF_LOC.findall(html)
            for propre in [u.split("?")[0].split("#")[0]]
            if not propre.endswith(".xml") and "/leditiondusoir/" not in propre
        )
        if i % 20 == 0:  # checkpoint
            with open(SORTIE, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["url"])
                for u in sorted(urls):
                    w.writerow([u])
finally:
    driver.quit()

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
