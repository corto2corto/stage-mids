"""Moteur "log" : Firefox connecté à un compte abonné.

Même Firefox que navigateur.py, avec une étape en plus à l'ouverture : la page
de connexion du média est remplie avec les identifiants lus dans un fichier
NON versionné (config.IDENTIFIANTS, ignoré par git via la règle *.json) :

    {"le_monde": {"email": "...", "mot_de_passe": "..."},
     "mediapart": {"email": "...", "mot_de_passe": "..."}}

Important : une fois connecté, il ne faut plus effacer les cookies du driver
(garder_cookies=True dans navigateur.scraper), sinon le compte est déconnecté.
"""

import json
import time

from selenium.webdriver.common.by import By

from scraping.config import IDENTIFIANTS
from scraping.navigateur import ouvrir_firefox

# Page de connexion de chaque média : URL + sélecteurs CSS des champs.
# le_monde : bouton de validation sous plusieurs formes selon la page servie
# (input.button sur l'ancien script, button[type=submit] sur la page secure).
CONNEXIONS = {
    "le_monde": {
        "url": "https://secure.lemonde.fr/sfuser/connexion",
        "email": "input#email",
        "mot_de_passe": "input#password",
        "valider": "button[type='submit'], input.button, input[type='submit']",
    },
    "mediapart": {
        "url": "https://www.mediapart.fr/login",
        "email": "input[name='name']",
        "mot_de_passe": "input[name='password']",
        "valider": "button[type='submit']",
    },
}

ATTENTE_LOGIN = 5   # secondes de chargement laissées à chaque étape de connexion


def ouvrir_firefox_connecte(media):
    """Ouvre un Firefox et le connecte au compte du média. Retourne le driver."""
    identifiants = json.loads(IDENTIFIANTS.read_text("utf-8"))[media]
    connexion = CONNEXIONS[media]

    driver = ouvrir_firefox()
    try:
        driver.get(connexion["url"])
        time.sleep(ATTENTE_LOGIN)
        driver.find_element(By.CSS_SELECTOR, connexion["email"]).send_keys(identifiants["email"])
        driver.find_element(By.CSS_SELECTOR, connexion["mot_de_passe"]).send_keys(identifiants["mot_de_passe"])
        driver.find_element(By.CSS_SELECTOR, connexion["valider"]).click()
        time.sleep(ATTENTE_LOGIN)
    except Exception:
        driver.quit()
        raise
    return driver


# Test : se connecte au compte, scrape une URL et affiche la fin de l'article
# python -m scraping.connexion <media> <url>

if __name__ == "__main__":
    import sys

    from scraping import extraction
    from scraping.navigateur import configurer_ublock, scraper

    media, url = sys.argv[1], sys.argv[2]
    configurer_ublock()
    driver = ouvrir_firefox_connecte(media)
    try:
        contenu = extraction.extraire(media, scraper(driver, url, garder_cookies=True))["contenu"]
        print(f"{len(contenu.split())} mots")
        print(f"...{contenu[-250:]}")
    finally:
        driver.quit()
