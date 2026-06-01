import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

# Rend le paquet `scrapers` importable quel que soit le dossier de lancement
RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RACINE)

from scrapers.bypass_firefox import configurer_ublock, ouvrir_firefox, scraper

BASE = "/data/elias/stage-mids/data/urls.db"
HTML_DIR = os.path.join(RACINE, "data", "html")
MEDIAS = ["le_journal_du_dimanche", "le_monde", "le_figaro", "paris_match"]  # médias Firefox


# --- Lecture / écriture BDD ------------------------------------------------
def lire_batch():
    """Une URL non traitée (etat=0) par média : {media: (id, url)}."""
    marques = ",".join("?" * len(MEDIAS))
    batch = {}
    with sqlite3.connect(BASE) as conn:
        rows = conn.execute(
            f"SELECT media, id, url FROM urls WHERE etat=0 AND media IN ({marques}) GROUP BY media",
            MEDIAS,
        ).fetchall()
    for media, id, url in rows:
        batch[media] = (id, url)
    return batch


def ecrire_resultats(resultats):
    """Met à jour l'état : 2 = succès, 1 = échec."""
    maj = [(2 if html else 1, id) for (id, url, html) in resultats.values()]
    with sqlite3.connect(BASE) as conn:
        conn.executemany("UPDATE urls SET etat=? WHERE id=?", maj)


def sauver_html(resultats):
    """Sauve le HTML récupéré (interim, en attendant 6_verification / 7_extraction)."""
    for media, (id, url, html) in resultats.items():
        if html:
            dossier = os.path.join(HTML_DIR, media)
            os.makedirs(dossier, exist_ok=True)
            with open(os.path.join(dossier, f"{id}.html"), "w", encoding="utf-8") as f:
                f.write(html)


# --- Scraping (navigateurs persistants) ------------------------------------
def ouvrir_navigateurs():
    """Ouvre un navigateur par média, en parallèle (download uBlock simultané)."""
    with ThreadPoolExecutor(max_workers=len(MEDIAS)) as ex:
        return dict(zip(MEDIAS, ex.map(lambda m: ouvrir_firefox(), MEDIAS)))


def scraper_url(media, id, url, driver):
    try:
        html = scraper(driver, url)
    except Exception:
        html = None
    return media, (id, url, html)


def scraper_batch(batch, navigateurs):
    """Scrape une vague (1 URL/média) en réutilisant les navigateurs ouverts."""
    resultats = {}
    with ThreadPoolExecutor(max_workers=len(batch)) as ex:
        taches = [
            ex.submit(scraper_url, media, id, url, navigateurs[media])
            for media, (id, url) in batch.items()
        ]
        for tache in taches:
            media, valeur = tache.result()
            resultats[media] = valeur
    return resultats


# --- Orchestration ---------------------------------------------------------
def main():
    configurer_ublock()
    navigateurs = ouvrir_navigateurs()
    try:
        while batch := lire_batch():
            resultats = scraper_batch(batch, navigateurs)
            sauver_html(resultats)
            ecrire_resultats(resultats)
    finally:
        for driver in navigateurs.values():
            driver.quit()


if __name__ == "__main__":
    main()
