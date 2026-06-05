"""Orchestration du scraping : ouvre les navigateurs, scrape un batch, écrit.
Point d'entrée : main(). Lancé via lancer_scraping.py à la racine du dépôt.
"""

import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from scraping.batch import new_batch
from scraping.config import DATA_DIR, SCRAPERS
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
from scraping.stockage import ecriture_csv, maj_bdd


def ouvrir_multi_firefox(batch):
    """Ouvre un Firefox par média (en parallèle). Retourne {media: driver}."""
    medias = [m for m in batch if SCRAPERS.get(m) == "firefox"]
    with ThreadPoolExecutor(max_workers=len(medias)) as ex:
        drivers = list(ex.map(lambda _: ouvrir_firefox(), medias))
    return dict(zip(medias, drivers))


def scraper_batch(batch, navigateurs):
    """Scrape toutes les URLs du batch en parallèle. Retourne {media: (id, url, html)}."""
    def scraper_url(media):
        id, url = batch[media]
        try:
            html = scraper(navigateurs[media], url)
        except Exception:
            html = None
        return media, (id, url, html)

    with ThreadPoolExecutor(max_workers=len(navigateurs)) as ex:
        return dict(ex.map(scraper_url, navigateurs))


def main():
    debut = time.time()

    # Écrit la config uBlock dans ~/.mozilla/managed-storage/ (listes anti-bandeaux)
    configurer_ublock()

    # Connexion persistante pour les mises à jour d'état (commit par batch)
    conn = sqlite3.connect(DATA_DIR/"urls.db")

    # Une URL par média depuis la BDD (etat=0)
    batch = new_batch()

    # Un Firefox par média, en parallèle
    navigateurs = ouvrir_multi_firefox(batch)

    try:
        resultats = scraper_batch(batch, navigateurs)
        for media, (id, url, html) in resultats.items():
            if html is None:
                print(f"{media}: ECHEC")
                maj_bdd(conn, id, etat=1)
                continue
            etat = ecriture_csv(media, id, url, html)
            maj_bdd(conn, id, etat=etat)
        conn.commit()   # un seul commit pour tout le batch
        print(f"\nTemps total : {time.time() - debut:.1f}s")
    finally:
        for driver in navigateurs.values():
            driver.quit()
        conn.close()


if __name__ == "__main__":
    main()
