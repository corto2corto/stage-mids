"""Pilotage d'un navigateur Firefox headless avec bypass paywall + uBlock.

Trois fonctions :
- configurer_ublock() : à appeler UNE fois avant tout (permet de configurer uBlock).
- ouvrir_firefox()    : ouvre un Firefox prêt à scraper (extensions installées).
- scraper()           : récupère le HTML d'une URL avec un driver déjà ouvert.
"""

import json
import os
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.remote_connection import FirefoxRemoteConnection
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.client_config import ClientConfig

from scraping.config import (RACINE, GECKODRIVER_PATH, FIREFOX_BIN, MANAGED_DIR, ADMIN_SETTINGS, TMP_FIREFOX)

# Selenium fixe en dur 120 s de délai HTTP vers geckodriver — trop court pour
# OUVRIR 16 Firefox en parallèle quand le disque est chargé : tous dépassent le
# délai (ReadTimeoutError) et le cycle tourne avec une poignée de navigateurs.
# On ouvre donc avec un délai large, puis ouvrir_firefox() revient au délai
# standard : un navigateur gelé en cours de run ne doit pas bloquer 10 min.
DELAI_OUVERTURE = 600
DELAI_SCRAPING = 120

_init_firefox_connection = FirefoxRemoteConnection.__init__

def _init_patient(self, remote_server_addr, keep_alive=True, ignore_proxy=False, client_config=None):
    client_config = client_config or ClientConfig(
        remote_server_addr=remote_server_addr, keep_alive=keep_alive, timeout=DELAI_OUVERTURE)
    _init_firefox_connection(self, remote_server_addr, keep_alive, ignore_proxy, client_config)

FirefoxRemoteConnection.__init__ = _init_patient


def configurer_ublock():
    MANAGED_DIR.mkdir(parents=True, exist_ok=True)
    manifeste = {
        "name": "uBlock0@raymondhill.net",
        "description": "Config uBlock pour scraping (listes anti-bandeaux)",
        "type": "storage",
        "data": {"adminSettings": ADMIN_SETTINGS},
    }
    fichier = MANAGED_DIR / "uBlock0@raymondhill.net.json"
    fichier.write_text(json.dumps(manifeste), "utf-8")


def ouvrir_firefox():
    TMP_FIREFOX.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(TMP_FIREFOX)

    options = Options()
    options.add_argument("--headless")
    options.binary_location = FIREFOX_BIN
    options.set_preference("permissions.default.image", 2)
    # Pas de cache retour : Firefox garde sinon en RAM les dernières pages de
    # l'onglet (y compris celle qu'on vient de remplacer par about:blank).
    options.set_preference("browser.sessionhistory.max_total_viewers", 0)
    driver = webdriver.Firefox(options=options, service=Service(str(GECKODRIVER_PATH)))

    # Si l'installation des extensions échoue, on ferme le Firefox déjà lancé
    # pour ne pas laisser de processus orphelin.
    try:
        # Au-delà, driver.get lève TimeoutException (défaut : 300 s). Un
        # timeout coûte tout ce temps au média : 30 s suffisent, une page
        # saine charge bien avant (durées visibles dans le log du pipeline).
        driver.set_page_load_timeout(30)
        extensions_dir = RACINE / "extensions" / "firefox"
        for xpi in extensions_dir.glob("*.xpi"):
            driver.install_addon(str(xpi), temporary=True)
        time.sleep(15)   # uBlock télécharge ses listes sur le web
    except Exception:
        driver.quit()
        raise
    # Navigateur prêt : retour au délai standard pour les commandes de scraping.
    driver.command_executor._client_config.timeout = DELAI_SCRAPING
    return driver


def scraper(driver, url, attente=6, garder_cookies=False):
    # garder_cookies=True pour le moteur "log" : effacer les cookies déconnecterait le compte.
    if not garder_cookies:
        driver.delete_all_cookies()
    driver.get(url)
    time.sleep(attente)
    html = driver.page_source
    # Décharge la page une fois le HTML en main : sinon son JS (pubs, players
    # vidéo) tourne en continu entre deux vagues et fait gonfler le processus
    # (vu à 6,5 Go / 67 % CPU sur challenges.fr après 1h30 de cycle).
    try:
        driver.get("about:blank")
    except Exception:
        pass   # navigateur en vrac : l'échec se verra à la vague suivante
    return html


# Test : Scrape un batch et affiche la fin de chaque article

if __name__ == "__main__":
    from scraping.batch import new_batch
    from scraping import extraction

    configurer_ublock()
    batch = new_batch()
    driver = ouvrir_firefox()
    try:
        for media, (id, url) in batch.items():
            contenu = extraction.extraire(media, scraper(driver, url))["contenu"]
            print(f"\n== {media} (id={id}, {len(contenu.split())} mots) ==")
            print(f"...{contenu[-250:]}")
    finally:
        driver.quit()
