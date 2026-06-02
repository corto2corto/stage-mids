"""Pilotage d'un navigateur Firefox headless avec bypass paywall + uBlock.

Trois fonctions :
- configurer_ublock() : à appeler UNE fois avant tout (écrit la config uBlock).
- ouvrir_firefox()    : ouvre un Firefox prêt à scraper (extensions installées).
- scraper()           : récupère le HTML d'une URL avec un driver déjà ouvert.
"""

import json
import os
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from scraping.config import EXTENSIONS_DIR, TMP_DIR

UBLOCK_ID = "uBlock0@raymondhill.net"
MANAGED_DIR = os.path.expanduser("~/.mozilla/managed-storage")
ATTENTE_LISTES = 20   # au démarrage : uBlock télécharge ses listes (une fois)
ATTENTE_PAGE = 5      # laisse le bypass agir sur chaque page

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
    os.environ["TMPDIR"] = str(TMP_DIR)
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    for xpi in os.listdir(EXTENSIONS_DIR):
        if xpi.endswith(".xpi"):
            driver.install_addon(os.path.join(EXTENSIONS_DIR, xpi), temporary=True)
    time.sleep(ATTENTE_LISTES)   # uBlock télécharge ses listes une seule fois
    return driver


def scraper(driver, url):
    """Récupère le HTML d'une URL en repartant d'un état propre (cookies vidés)."""
    driver.delete_all_cookies()
    driver.get(url)
    time.sleep(ATTENTE_PAGE)
    return driver.page_source
