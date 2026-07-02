"""Dispatch entre les moteurs de scraping. Le moteur de chaque média est déclaré dans medias.py :

- "firefox" : Firefox headless + extensions bypass paywall (navigateur.py)
- "log"     : Firefox connecté à un compte abonné (connexion.py)
- "basic"   : simple requête HTTP, sans navigateur (basic.py)
"""

from scraping import basic, navigateur
from scraping.connexion import ouvrir_firefox_connecte
from scraping.medias import ATTENTE_DEFAUT, MEDIAS


def ouvrir_session(media):
    """Ouvre la session de scraping d'un média selon son moteur (driver Firefox ou session HTTP)."""
    moteur = MEDIAS[media]["moteur"]
    if moteur == "basic":
        return basic.ouvrir_session()
    if moteur == "log":
        return ouvrir_firefox_connecte(media)
    return navigateur.ouvrir_firefox()


def scraper(media, session, url):
    """Récupère le HTML d'une URL avec la session déjà ouverte du média."""
    moteur = MEDIAS[media]["moteur"]
    if moteur == "basic":
        return basic.scraper(session, url)
    attente = MEDIAS[media].get("attente", ATTENTE_DEFAUT)
    return navigateur.scraper(session, url, attente, garder_cookies=(moteur == "log"))


def fermer_session(media, session):
    if MEDIAS[media]["moteur"] == "basic":
        session.close()
    else:
        session.quit()
