"""Orchestration du scraping : ouvre les navigateurs, scrape, écrit.
Point d'entrée : main(). Lancé via `python -m scraping.pipeline`.

Chaque média a sa boucle dans son propre thread : scraper une URL, écrire,
respecter son attente, recommencer. Aucune synchronisation entre médias :
un site lent (ou un chargement Firefox qui traîne) ne ralentit que lui-même.
C'est ce qui donne le débit — l'ancienne organisation en vagues attendait le
média le plus lent avant de relancer tout le monde.
"""

import csv
import shutil
import sqlite3
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from scraping.batch import new_batch, prochaine_url
from scraping.config import TMP_FIREFOX
from scraping.medias import MEDIAS
from scraping.moteurs import fermer_session, ouvrir_session, scraper
from scraping.navigateur import configurer_ublock
from scraping.stockage import DATA_DIR, ecriture_csv, maj_bdd
from scraping.suivi import snapshot

# Les threads des médias écrivent tous dans le même log : sans verrou, les
# lignes s'entremêlent et deviennent inexploitables pour la surveillance.
VERROU_PRINT = threading.Lock()

DUREE_MAX = 2 * 3600   # un run s'arrête seul au bout de 2 h, lancer.sh relance


def ouvrir_sessions(batch):
    """Ouvre une session par média (en parallèle) selon son moteur. Retourne {media: session}.

    Une session qui échoue à l'ouverture est signalée puis ignorée : ses URLs
    restent à etat=0 et seront reprises au cycle suivant de lancer.sh."""
    def ouvrir(media):
        try:
            return media, ouvrir_session(media)
        except Exception as e:
            print(f"  {media} : échec d'ouverture de la session ({type(e).__name__})")
            return media, None

    resultats = {}
    # Les sessions log d'abord, une par une au calme : le login échoue pendant
    # la ruée des Firefox, et chaque échec consomme une tentative sur le
    # compte abonné.
    logs = [media for media in batch if MEDIAS.get(media, {}).get("moteur") == "log"]
    t = time.time()
    for media in logs:
        resultats[media] = ouvrir(media)[1]
    if logs:
        ouverts = sum(1 for media in logs if resultats[media])
        print(f"[chrono] sessions log : {time.time()-t:.1f}s ({ouverts}/{len(logs)} ouvertes)")

    autres = [media for media in batch if media not in resultats]
    t = time.time()
    if autres:
        with ThreadPoolExecutor(max_workers=len(autres)) as ex:
            resultats.update(ex.map(ouvrir, autres))
    # Seconde chance, un par un, une fois la ruée passée.
    for media in [m for m, s in resultats.items() if s is None]:
        resultats[media] = ouvrir(media)[1]
    print(f"[chrono] sessions firefox+basic : {time.time()-t:.1f}s")
    return {media: session for media, session in resultats.items() if session}


def traiter_url(conn, media, session, id, url):
    """Scrape une URL, écrit le résultat, met à jour l'état. Retourne l'état (1 ou 2)."""
    try:
        html = scraper(media, session, url)
    except Exception:
        html = None
    try:
        etat = ecriture_csv(media, id, url, html) if html else 1
    except Exception:
        etat = 1
    maj_bdd(conn, id, etat)
    conn.commit()
    return etat


def boucle_media(media, session, debut):
    """Boucle d'un média : une URL à la fois, à son rythme, jusqu'à épuisement.

    Connexion propre au thread. Le mode WAL évite que les écritures croisées
    des ~30 threads ne se bloquent (en mode journal classique, SQLite renvoie
    « database is locked » sans respecter le timeout quand deux transactions
    s'entrecroisent) ; synchronous=NORMAL suffit en WAL et allège les commits."""
    conn = sqlite3.connect(DATA_DIR/"urls.db", timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")   # persistant sur le fichier, idempotent
    conn.execute("PRAGMA synchronous=NORMAL")
    traitees = 0
    t0 = time.time()
    try:
        while time.time() - debut < DUREE_MAX:
            suivant = prochaine_url(conn, media)
            if not suivant:
                break
            id, url = suivant
            t = time.time()
            etat = traiter_url(conn, media, session, id, url)
            traitees += 1
            with VERROU_PRINT:
                print(f"  {media:<24} id={id}  etat={etat} "
                      f"({'succès' if etat == 2 else 'échec'} en {time.time()-t:.1f}s)")
    except Exception:
        # Sans ça, l'exception resterait cachée dans le future jusqu'à la fin
        # du run : on la montre tout de suite, les autres médias continuent et
        # les URLs restantes seront reprises au cycle suivant de lancer.sh.
        with VERROU_PRINT:
            print(f"\n[{media}] boucle interrompue par une erreur :")
            traceback.print_exc()
    finally:
        try:
            fermer_session(media, session)
        except Exception:
            pass   # session déjà morte : lancer.sh nettoiera le processus
        conn.close()
    duree = time.time() - t0
    with VERROU_PRINT:
        print(f"[bilan] {media} : {traitees} URLs en {duree/60:.1f} min "
              f"({traitees*60/duree:.1f} URLs/min)")
    return traitees


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
    # charger_nouvelles_urls(conn)  # désactivé : pas de nouveaux CSV pour l'instant

    # Le premier batch fixe l'ensemble des médias à traiter, donc les sessions
    # à ouvrir (aucun média ne peut en gagner en cours de route).
    # Les médias en pause (champ "pause" de medias.py) sont écartés d'emblée.
    batch = {media: iu for media, iu in new_batch().items()
             if not MEDIAS.get(media, {}).get("pause")}
    if not batch:
        print("Aucune URL à etat=0 — rien à faire.")
        return

    print(f"Ouverture des sessions pour : {', '.join(sorted(batch))}")
    sessions = ouvrir_sessions(batch)
    if not sessions:
        print("Aucune session n'a pu démarrer — fin du run.")
        return

    # Le suivi tourne à part, hors du chemin critique des médias.
    arret = threading.Event()
    def suivi_periodique():
        while not arret.wait(60):
            try:
                snapshot(min_nouveaux=1000)   # instantané + alerte tous les 1000 articles
            except Exception:
                pass   # le suivi ne doit jamais gêner le scraping
    threading.Thread(target=suivi_periodique, daemon=True).start()

    print(f"[chrono] scraping lancé, un thread par média ({len(sessions)})")
    try:
        with ThreadPoolExecutor(max_workers=len(sessions)) as ex:
            futurs = [ex.submit(boucle_media, media, session, debut)
                      for media, session in sessions.items()]
            traitees = sum(f.result() for f in futurs)
    finally:
        arret.set()
        shutil.rmtree(TMP_FIREFOX, ignore_errors=True)   # profils temp de la session

    print(f"\n{traitees} URLs traitées en {time.time() - debut:.1f}s.")


if __name__ == "__main__":
    main()
