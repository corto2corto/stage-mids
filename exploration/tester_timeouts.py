"""Teste 3 durées de page_load_timeout (6/10/14 s) sur les médias lents
(telerama, le_figaro, le_nouvel_observateur) : 9 Firefox en parallèle
(3 médias × 3 timeouts), 12 URLs distinctes chacun, attente 6 s conservée.

Sortie par couple (média, timeout) : succès, timeouts, s/URL, URLs/min.
À lancer depuis la racine du clone v2 avec STAGE_DATA_DIR sur la base de test.
"""

import sqlite3
import threading
import time

from selenium.common.exceptions import TimeoutException

from scraping import extraction, navigateur
from scraping.paywall import est_bloque
from scraping.stockage import DATA_DIR

MEDIAS_TEST = ["telerama", "le_figaro", "le_nouvel_observateur"]
TIMEOUTS = [6, 10, 14]
N = 12   # URLs par couple (média, timeout)

conn = sqlite3.connect(DATA_DIR / "urls.db", timeout=30)
urls_media = {m: [u for (u,) in conn.execute(
    "SELECT url FROM urls WHERE media=? LIMIT ?", (m, N * len(TIMEOUTS)))]
    for m in MEDIAS_TEST}
conn.close()

navigateur.configurer_ublock()
verrou = threading.Lock()


def tester(media, secondes, urls):
    driver = navigateur.ouvrir_firefox()
    driver.set_page_load_timeout(secondes)
    ok = bloques = timeouts = 0
    t0 = time.time()
    for url in urls:
        try:
            html = navigateur.scraper(driver, url, attente=6)
            if est_bloque(extraction.extraire(media, html)["contenu"]):
                bloques += 1
            else:
                ok += 1
        except TimeoutException:
            timeouts += 1
        except Exception:
            pass
    duree = time.time() - t0
    driver.quit()
    with verrou:
        print(f"{media:<22} timeout={secondes:>2}s : {ok:>2} ok, {bloques} bloqués, "
              f"{timeouts:>2} timeouts / {len(urls)} URLs — {duree/len(urls):4.1f} s/URL, "
              f"{len(urls)*60/duree:4.1f} URLs/min", flush=True)


threads = []
for m in MEDIAS_TEST:
    for i, secondes in enumerate(TIMEOUTS):
        th = threading.Thread(target=tester, args=(m, secondes, urls_media[m][i*N:(i+1)*N]))
        th.start()
        threads.append(th)
for th in threads:
    th.join()
print("=== tests timeouts terminés ===", flush=True)
