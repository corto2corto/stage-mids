import json
import os
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

EXTENSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "extensions", "firefox")

# Page connue pour afficher un gros bandeau de consentement cookies
URL = "https://www.lemonde.fr/"
ATTENTE = 20  # 1er lancement : uBlock télécharge ses listes de filtres

# --- Configuration uBlock via managed storage -----------------------------
# Firefox lit ce manifeste indépendamment du profil. uBlock y trouve
# `adminSettings` au démarrage et écrase ses réglages par les tiens (donc
# les listes anti-bandeaux que tu as activées sur ton Mac).
UBLOCK_ID = "uBlock0@raymondhill.net"
MANAGED_DIR = os.path.expanduser("~/.mozilla/managed-storage")

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


def installer_manifeste():
    os.makedirs(MANAGED_DIR, exist_ok=True)
    manifeste = {
        "name": UBLOCK_ID,
        "description": "Config uBlock pour scraping (listes anti-bandeaux)",
        "type": "storage",
        "data": {"adminSettings": ADMIN_SETTINGS},
    }
    chemin = os.path.join(MANAGED_DIR, f"{UBLOCK_ID}.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(manifeste, f)
    print(f"[manifeste] écrit : {chemin}")


installer_manifeste()

options = Options()
options.add_argument("--headless")

with webdriver.Firefox(options=options) as driver:
    for xpi in os.listdir(EXTENSIONS_DIR):
        if xpi.endswith(".xpi"):
            driver.install_addon(os.path.join(EXTENSIONS_DIR, xpi), temporary=True)

    driver.get(URL)
    time.sleep(ATTENTE)

    # Cherche des éléments typiques d'un bandeau de consentement encore visibles
    suspects = driver.execute_script("""
        const sel = '[id*=consent],[class*=consent],[id*=cookie],[class*=cookie],[id*=didomi],[class*=didomi],[id*=cmp]';
        return Array.from(document.querySelectorAll(sel))
            .filter(e => e.offsetParent !== null)   // visible à l'écran
            .map(e => e.tagName + '#' + e.id + '.' + e.className)
            .slice(0, 10);
    """)

    if suspects:
        print(f"[KO] bandeau cookies probablement encore présent ({len(suspects)} éléments visibles) :")
        for s in suspects:
            print("   -", s)
    else:
        print("[OK] aucun élément de bandeau cookies visible — uBlock a fait le ménage")

    driver.save_full_page_screenshot("test_ublock.png")
    print("Capture : test_ublock.png (à inspecter pour confirmer)")
