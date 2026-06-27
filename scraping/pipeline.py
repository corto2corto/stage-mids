"""Orchestration du scraping : ouvre les navigateurs, scrape un batch, écrit.
Point d'entrée : main(). Lancé via `python -m scraping.pipeline`.
"""

import csv
import shutil
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from scraping.batch import new_batch
from scraping.config import TMP_FIREFOX
from scraping.medias import MEDIAS
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
from scraping.stockage import DATA_DIR, ecriture_csv, maj_bdd
from scraping.suivi import snapshot


def ouvrir_multi_firefox(batch):
    """Ouvre un Firefox par média (en parallèle). Retourne {media: driver}."""
    medias = [m for m in batch if MEDIAS[m]["moteur"] == "firefox"]
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


def traiter_vague(conn, batch, navigateurs):
    actifs = {media: navigateurs[media] for media in batch if media in navigateurs}
    resultats = scraper_batch(batch, actifs)

    for media, (id, url, html) in resultats.items():
        try:
            etat = ecriture_csv(media, id, url, html) if html else 1
        except Exception:
            etat = 1
        print(f"  {media:<24} id={id}  etat={etat} ({'succès' if etat == 2 else 'échec'})")
        maj_bdd(conn, id, etat)

    conn.commit()
    return len(resultats)



def charger_nouvelles_urls(conn):
    """Importe les URLs des *_url.csv pas encore en base (etat=0)."""
    existantes = {u for (u,) in conn.execute("SELECT url FROM urls")}
    for chemin in DATA_DIR.glob("*_url.csv"):
        media = chemin.stem.removesuffix("_url")
        with open(chemin, newline="", encoding="utf-8") as f:
            nouvelles = [(media, ligne["url"]) for ligne in csv.DictReader(f)
                         if ligne["url"] not in existantes]
        conn.executemany("INSERT INTO urls (media, url, etat) VALUES (?, ?, 0)", nouvelles)
        if nouvelles:
            print(f"{media} : {len(nouvelles)} nouvelles URLs chargées")
    conn.commit()


def main():
    debut = time.time()
    configurer_ublock()
    conn = sqlite3.connect(DATA_DIR/"urls.db")
    # charger_nouvelles_urls(conn)  # désactivé : pas de nouveaux CSV pour l'instant

    # Le premier batch fixe l'ensemble des médias à traiter, donc les navigateurs
    # à ouvrir (aucun média ne peut en gagner en cours de route).
    batch = new_batch()
    if not batch:
        print("Aucune URL à etat=0 — rien à faire.")
        conn.close()
        return

    print(f"Ouverture d'un Firefox pour : {', '.join(sorted(batch))}")
    navigateurs = ouvrir_multi_firefox(batch)

    traitees = 0
    vague = 0
    try:
        while batch and time.time() - debut < (2*3600):
            vague += 1
            print(f"\n=== Vague {vague}  ({traitees} URLs traitées) ===")
            traitees += traiter_vague(conn, batch, navigateurs)
            snapshot(min_nouveaux=1000)   # instantané + alerte tous les 1000 articles
            batch = new_batch()
    finally:
        for driver in navigateurs.values():
            driver.quit()
        shutil.rmtree(TMP_FIREFOX, ignore_errors=True)   # profils temp de la session
        conn.close()

    print(f"\n{traitees} URLs traitées en {time.time() - debut:.1f}s.")


if __name__ == "__main__":
    main()
