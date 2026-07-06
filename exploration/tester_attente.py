"""Compare attente 6 s vs 4 s sur les médias premium (bypass BPC) : pour chaque
média, deux Firefox en parallèle scrappent 12 URLs chacun (jeux distincts,
répartis pair/impair). Si le taux de « bloqués » monte à 4 s, c'est que BPC
n'a pas fini son travail — on saura qu'il faut rester à 6 s.

À lancer depuis la racine du clone v2 avec STAGE_DATA_DIR sur la base de test.
"""

import sqlite3
import threading
import time

from selenium.common.exceptions import TimeoutException

from scraping import extraction, navigateur
from scraping.paywall import est_bloque
from scraping.stockage import DATA_DIR

MEDIAS_TEST = ["le_figaro", "paris_match", "les_echos"]
ATTENTES = [6, 4]
N = 12

conn = sqlite3.connect(DATA_DIR / "urls.db", timeout=30)
urls_media = {m: [u for (u,) in conn.execute(
    "SELECT url FROM urls WHERE media=? LIMIT ?", (m, N * len(ATTENTES)))]
    for m in MEDIAS_TEST}
conn.close()

navigateur.configurer_ublock()
verrou = threading.Lock()


def tester(media, attente, urls):
    driver = navigateur.ouvrir_firefox()
    ok = bloques = timeouts = 0
    longueurs = []
    t0 = time.time()
    for url in urls:
        try:
            html = navigateur.scraper(driver, url, attente=attente)
            contenu = extraction.extraire(media, html)["contenu"]
            if est_bloque(contenu):
                bloques += 1
            else:
                ok += 1
                longueurs.append(len(contenu))
        except TimeoutException:
            timeouts += 1
        except Exception:
            pass
    duree = time.time() - t0
    driver.quit()
    moy = sum(longueurs) / len(longueurs) if longueurs else 0
    with verrou:
        print(f"{media:<14} attente={attente}s : {ok:>2} ok, {bloques} bloqués, "
              f"{timeouts:>2} timeouts / {len(urls)} — contenu moyen {moy:5.0f} car., "
              f"{duree/len(urls):4.1f} s/URL", flush=True)


threads = []
for m in MEDIAS_TEST:
    for i, attente in enumerate(ATTENTES):
        urls = urls_media[m][i::len(ATTENTES)]   # répartition pair/impair
        th = threading.Thread(target=tester, args=(m, attente, urls))
        th.start()
        threads.append(th)
for th in threads:
    th.join()
print("=== test attente terminé ===", flush=True)
