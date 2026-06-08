"""Pilotage d'un navigateur Firefox headless avec bypass paywall + uBlock.

Trois fonctions :
- configurer_ublock() : à appeler UNE fois avant tout (permet de configurer uBlock).
- ouvrir_firefox()    : ouvre un Firefox prêt à scraper (extensions installées).
- scraper()           : récupère le HTML d'une URL avec un driver déjà ouvert.
"""

import json
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

# Racine du dépôt : sert à retrouver les ressources versionnées (extensions/).
RACINE = Path(__file__).resolve().parent.parent

# Geckodriver 0.36 à nous, dans extensions/geckodriver/ (pointé explicitement pour
# que Selenium n'aille pas chercher via le PATH ni déclencher Selenium Manager).
# Override possible via la variable d'environnement GECKODRIVER_PATH.
GECKODRIVER_PATH = os.environ.get("GECKODRIVER_PATH", RACINE/"extensions"/"geckodriver"/"geckodriver")

# Firefox NON-snap (le snap est confiné au home et crashe avec un profil sur /data).
# On pointe le binaire déjà téléchargé par Selenium. Override via FIREFOX_BIN.
FIREFOX_BIN = os.environ.get(
    "FIREFOX_BIN", "/home/ubuntu/.cache/selenium/firefox/linux64/151.0.2/firefox"
)

UBLOCK_ID = "uBlock0@raymondhill.net"
MANAGED_DIR = os.path.expanduser("~/.mozilla/managed-storage")
ATTENTE_LISTES = 20   # au démarrage : uBlock télécharge ses listes (une fois)
ATTENTE_PAGE = 6      # laisse le bypass agir sur chaque page

ADMIN_SETTINGS = {
    "userSettings": {
        "externalLists": "https://www.i-dont-care-about-cookies.eu/abp/",
        "importedLists": ["https://www.i-dont-care-about-cookies.eu/abp/"],
    },
    "selectedFilterLists": [
        "user-filters", "ublock-filters", "ublock-badware", "ublock-privacy",
        "ublock-quick-fixes", "ublock-unbreak", "easylist", "easyprivacy",
        "urlhaus-1", "plowe-0", "fanboy-cookiemonster", "ublock-cookies-easylist",
        "easylist-annoyances", "FRA-0",
        "https://www.i-dont-care-about-cookies.eu/abp/",
    ],
}


def configurer_ublock():
    """Écrit le manifeste managed-storage. À appeler UNE fois avant tout."""
    os.makedirs(MANAGED_DIR, exist_ok=True)
    manifeste = {
        "name": UBLOCK_ID,
        "description": "Config uBlock pour scraping (listes anti-bandeaux)",
        "type": "storage",
        "data": {"adminSettings": ADMIN_SETTINGS},
    }
    with open(os.path.join(MANAGED_DIR, f"{UBLOCK_ID}.json"), "w", encoding="utf-8") as f:
        json.dump(manifeste, f)


def ouvrir_firefox():
    """Ouvre un Firefox headless avec bypass + uBlock, prêt à scraper."""
    # Profils + temporaires de Firefox sous /data (et non le home/racine, petit et
    # vite saturé). Possible car on utilise un Firefox non-snap : le snap, lui, est
    # confiné au home et crashe avec un profil hors du home ("status 1").
    os.environ["TMPDIR"] = str(RACINE/"extensions"/"firefox"/"tmp")
    os.makedirs(os.environ["TMPDIR"], exist_ok=True)
    options = Options()
    options.add_argument("--headless")
    options.binary_location = FIREFOX_BIN
    options.set_preference("permissions.default.image", 2)
    driver = webdriver.Firefox(options=options, service=Service(str(GECKODRIVER_PATH)))
    extensions_dir = RACINE/"extensions"/"firefox"
    for xpi in os.listdir(extensions_dir):
        if xpi.endswith(".xpi"):
            driver.install_addon(os.path.join(extensions_dir, xpi), temporary=True)
    time.sleep(ATTENTE_LISTES)   # uBlock télécharge ses listes une seule fois
    return driver


def scraper(driver, url):
    """Récupère le HTML d'une URL en repartant d'un état propre (cookies vidés)."""
    driver.delete_all_cookies()
    driver.get(url)
    time.sleep(ATTENTE_PAGE)
    return driver.page_source


if __name__ == "__main__":
    from scraping.batch import new_batch
    from scraping import extraction

    TAIL = 250
    configurer_ublock()
    batch = new_batch()
    driver = ouvrir_firefox()
    try:
        for media, (id, url) in batch.items():
            contenu = extraction.extraire(media, scraper(driver, url))["contenu"]
            print(f"\n=== {media} (id={id}, {len(contenu.split())} mots) ===")
            print(f"...{contenu[-TAIL:]}")
    finally:
        driver.quit()
