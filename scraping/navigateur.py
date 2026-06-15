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
from selenium.webdriver.firefox.service import Service

from scraping.config import (RACINE, GECKODRIVER_PATH, FIREFOX_BIN, MANAGED_DIR, ADMIN_SETTINGS)


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
    tmp = RACINE / "extensions" / "firefox" / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(tmp)

    options = Options()
    options.add_argument("--headless")
    options.binary_location = FIREFOX_BIN
    options.set_preference("permissions.default.image", 2)
    driver = webdriver.Firefox(options=options, service=Service(str(GECKODRIVER_PATH)))

    extensions_dir = RACINE / "extensions" / "firefox"
    for xpi in extensions_dir.glob("*.xpi"):
        driver.install_addon(str(xpi), temporary=True)
    time.sleep(15)   # uBlock télécharge ses listes sur le web
    return driver


def scraper(driver, url, attente=6):
    driver.delete_all_cookies()
    driver.get(url)
    time.sleep(attente)
    return driver.page_source


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
