"""Orchestration du scraping : ouvre les navigateurs, scrape un batch, écrit.
Point d'entrée : main(). Lancé via `python -m scraping.pipeline`.
"""

import csv
import shutil
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

from selenium.common.exceptions import TimeoutException

from scraping.batch import new_batch
from scraping.config import TMP_FIREFOX
from scraping.medias import MEDIAS
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
from scraping.stockage import DATA_DIR, ecriture_csv, maj_bdd
from scraping.suivi import snapshot


def ouvrir_multi_firefox(batch):
    """Ouvre un Firefox par média (en parallèle). Retourne {media: driver}.

    Un navigateur qui échoue à l'ouverture est signalé puis ignoré : ses URLs
    restent à etat=0 et seront reprises au cycle suivant de lancer.sh."""
    def ouvrir(media):
        try:
            return media, ouvrir_firefox()
        except Exception as e:
            print(f"  {media} : échec d'ouverture du navigateur ({type(e).__name__})")
            return media, None

    medias = [m for m in batch if MEDIAS[m]["moteur"] == "firefox"]
    with ThreadPoolExecutor(max_workers=len(medias)) as ex:
        resultats = dict(ex.map(ouvrir, medias))
    return {media: driver for media, driver in resultats.items() if driver}


def scraper_batch(batch, navigateurs):
    """Scrape toutes les URLs du batch en parallèle. Retourne {media: (id, url, html)}
    et l'ensemble des médias dont le navigateur n'a pas répondu (panne probable)."""
    pannes = set()

    def scraper_url(media):
        id, url = batch[media]
        try:
            html = scraper(navigateurs[media], url)
        except TimeoutException:          # page trop lente : le navigateur va bien
            html = None
        except Exception as e:
            print(f"  {media} : {type(e).__name__} — {e}")
            html = None
            pannes.add(media)
        return media, (id, url, html)

    with ThreadPoolExecutor(max_workers=len(navigateurs)) as ex:
        return dict(ex.map(scraper_url, navigateurs)), pannes


def traiter_vague(conn, batch, navigateurs):
    actifs = {media: navigateurs[media] for media in batch if media in navigateurs}
    resultats, pannes = scraper_batch(batch, actifs)

    for media, (id, url, html) in resultats.items():
        try:
            etat = ecriture_csv(media, id, url, html) if html else 1
        except Exception as e:
            print(f"  {media} : {type(e).__name__} — {e}")
            etat = 1
        print(f"  {media:<24} id={id}  etat={etat} ({'succès' if etat == 2 else 'échec'})")
        maj_bdd(conn, id, etat)

    conn.commit()
    return len(resultats), pannes



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
    if not navigateurs:
        print("Aucun navigateur n'a pu démarrer — fin du run.")
        conn.close()
        return
    # On ne garde que les médias dont le navigateur a démarré.
    batch = {media: iu for media, iu in batch.items() if media in navigateurs}

    traitees = 0
    vague = 0
    pannes = {}   # media -> vagues consécutives où son navigateur n'a pas répondu
    try:
        while batch and time.time() - debut < (2*3600):
            vague += 1
            print(f"\n=== Vague {vague}  ({traitees} URLs traitées) ===")
            traites, muets = traiter_vague(conn, batch, navigateurs)
            traitees += traites

            # Un navigateur muet 3 vagues de suite est considéré mort : on arrête
            # le run (lancer.sh relance tout proprement) plutôt que de marquer en
            # échec toutes les URLs restantes du média.
            for media in batch:
                pannes[media] = pannes.get(media, 0) + 1 if media in muets else 0
            morts = sorted(m for m, n in pannes.items() if n >= 3)
            if morts:
                print(f"Navigateur sans réponse depuis 3 vagues : {', '.join(morts)} "
                      "— arrêt du run.")
                break

            snapshot(min_nouveaux=1000)   # instantané + alerte tous les 1000 articles
            batch = {media: iu for media, iu in new_batch().items()
                     if media in navigateurs}
    finally:
        for driver in navigateurs.values():
            try:
                driver.quit()
            except Exception:
                pass   # navigateur déjà mort : lancer.sh nettoiera le processus
        shutil.rmtree(TMP_FIREFOX, ignore_errors=True)   # profils temp de la session
        conn.close()

    print(f"\n{traitees} URLs traitées en {time.time() - debut:.1f}s.")


if __name__ == "__main__":
    main()
