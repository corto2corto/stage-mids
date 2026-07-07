"""Constantes de configuration du scraping (chemins serveur + réglages uBlock)."""

from pathlib import Path

RACINE = Path("/data/elias/stage-mids")
GECKODRIVER_PATH = RACINE / "extensions" / "geckodriver" / "geckodriver"
# Profils temporaires Firefox en RAM (/dev/shm) : le disque de données est
# saturé en permanence, les profils y coûtaient x3 sur l'ouverture et la
# navigation (mesuré 07/07/2026). ~122 Mo par profil, nettoyé au reboot.
TMP_FIREFOX = Path("/dev/shm/stage-mids-firefox-tmp")
SOURCES_SITE = RACINE / "site" / "sources" / "suivi"
IDENTIFIANTS = RACINE / "identifiants.json"   # comptes abonnés (moteur "log"), jamais versionné
FIREFOX_BIN = "/home/ubuntu/.cache/selenium/firefox/linux64/151.0.2/firefox"

MANAGED_DIR = Path.home() / ".mozilla" / "managed-storage"

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
