import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from data.scripts.creation_batch import new_batch
from scrapers.bypass_firefox import configurer_ublock, ouvrir_firefox, scraper

SCRAPERS = {
    "le_monde":               "firefox",
    "le_figaro":              "firefox",
    "le_journal_du_dimanche": "firefox",
    "paris_match":            "firefox",
    "le_capital":             "firefox",
    "les_echos":              "firefox",
    "valeurs_actuelles":      "firefox",
    "le_nouvel_observateur":  "firefox",
    "nice_matin":             "firefox",
    "telerama":               "firefox",
}


def ouvrir_multi_firefox(batch):
    medias = [m for m in batch if SCRAPERS.get(m) == "firefox"]
    with ThreadPoolExecutor(max_workers=len(medias)) as ex:
        drivers = list(ex.map(lambda _: ouvrir_firefox(), medias))
    return dict(zip(medias, drivers))


def scraper_batch(batch, navigateurs):
    def scraper_url(media):
        id, url = batch[media]
        try:
            html = scraper(navigateurs[media], url)
        except Exception:
            html = None
        return media, (id, url, html)

    with ThreadPoolExecutor(max_workers=len(navigateurs)) as ex:
        resultats = dict(ex.map(lambda m: scraper_url(m), navigateurs))
    return resultats


debut = time.time()

# Ecrit la config uBlock dans ~/.mozilla/managed-storage/ (listes anti-bandeaux)
configurer_ublock()

# Récupère une URL par média depuis la BDD (etat=0)
batch = new_batch()

# Ouvre un Firefox par média Firefox en parallèle
navigateurs = ouvrir_multi_firefox(batch)

# Scrape toutes les URLs en parallèle
resultats = scraper_batch(batch, navigateurs)

for media, (id, url, html) in resultats.items():
    print(f"\n== {media} ==")
    if html is None:
        print("ECHEC")
        continue
    for p in BeautifulSoup(html, "html.parser").find_all("p")[:10]:
        print(p.get_text())

print(f"\nTemps total : {time.time() - debut:.1f}s")

# Ferme les navigateurs après le test
for driver in navigateurs.values():
    driver.quit()