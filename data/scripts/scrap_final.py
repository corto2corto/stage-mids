import csv
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from data.scripts.creation_batch import new_batch
from scrapers.bypass_firefox import configurer_ublock, ouvrir_firefox, scraper

CSV_DIR = "/data/elias/stage-mids/data/csv"
BASE = "/data/elias/stage-mids/data/urls.db"

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


def ecriture_csv(media, id, url, html):
    """Parse le HTML et écrit une ligne (id, url, contenu) dans le CSV du média."""
    contenu = " ".join(p.get_text() for p in BeautifulSoup(html, "html.parser").find_all("p"))
    chemin = os.path.join(CSV_DIR, f"{media}.csv")
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([id, url, contenu])


def maj_bdd(conn, id, etat=2):
    """Met à jour l'état d'une URL dans la BDD. Le commit est géré par la boucle (par batch)."""
    conn.execute("UPDATE urls SET etat = ? WHERE id = ?", (etat, id))


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

# Connexion persistante pour les mises à jour d'état (commit par batch)
conn = sqlite3.connect(BASE)

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
        maj_bdd(conn, id, etat=1)
        continue
    for p in BeautifulSoup(html, "html.parser").find_all("p")[:10]:
        print(p.get_text())
    ecriture_csv(media, id, url, html)
    maj_bdd(conn, id)

# Un seul commit pour tout le batch
conn.commit()

print(f"\nTemps total : {time.time() - debut:.1f}s")

# Ferme les navigateurs après le test
for driver in navigateurs.values():
    driver.quit()

conn.close()