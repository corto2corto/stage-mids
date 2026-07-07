"""Dispatch entre les moteurs de scraping. Le moteur de chaque média est déclaré dans medias.py :

- "firefox" : Firefox headless + extensions bypass paywall (navigateur.py)
- "log"     : Firefox connecté à un compte abonné (connexion.py)
- "basic"   : simple requête HTTP, sans navigateur (basic.py)
- "hybride" : basic d'abord (rapide), Firefox bypass en secours si l'article
              ressort bloqué (payant). Pour les sites anti-bot qui ne
              ralentissent que les navigateurs (telerama & co) : leurs pages
              gratuites arrivent en <1 s en HTTP alors que Firefox y pend
              10-30 s.
"""

import time

from scraping import basic, extraction, navigateur
from scraping.connexion import ouvrir_firefox_connecte
from scraping.medias import ATTENTE_BASIC, ATTENTE_DEFAUT, MEDIAS
from scraping.paywall import est_bloque


def ouvrir_session(media):
    """Ouvre la session de scraping d'un média selon son moteur (driver Firefox ou session HTTP)."""
    moteur = MEDIAS[media]["moteur"]
    if moteur == "basic":
        return basic.ouvrir_session()
    if moteur == "log":
        return ouvrir_firefox_connecte(media)
    driver = navigateur.ouvrir_firefox()
    if "timeout" in MEDIAS[media]:
        driver.set_page_load_timeout(MEDIAS[media]["timeout"])
    if moteur == "hybride":
        return {"basic": basic.ouvrir_session(), "firefox": driver}
    return driver


def scraper(media, session, url):
    """Récupère le HTML d'une URL avec la session déjà ouverte du média."""
    regles = MEDIAS[media]
    moteur = regles["moteur"]
    if moteur == "basic":
        html = basic.scraper(session, url)
        time.sleep(regles.get("attente", ATTENTE_BASIC))   # politesse : ne pas marteler le site
        return html
    if moteur == "hybride":
        try:
            html = basic.scraper(session["basic"], url)
        except Exception:
            html = None   # le client HTTP a échoué : on tentera le Firefox
        if html and not est_bloque(extraction.extraire(media, html)["contenu"]):
            # Politesse du chemin rapide : sans elle, l'hybride enchaînerait
            # les gratuits à la vitesse HTTP et martèlerait le site.
            time.sleep(regles.get("attente_basic", 2))
            return html
        # Article payant (ou requête en échec) : au tour du Firefox bypass,
        # en espaçant les deux sollicitations du site.
        time.sleep(1)
        return navigateur.scraper(session["firefox"], url,
                                  regles.get("attente", ATTENTE_DEFAUT))
    attente = regles.get("attente", ATTENTE_DEFAUT)
    return navigateur.scraper(session, url, attente, garder_cookies=(moteur == "log"))


def fermer_session(media, session):
    moteur = MEDIAS[media]["moteur"]
    if moteur == "basic":
        session.close()
    elif moteur == "hybride":
        session["basic"].close()
        session["firefox"].quit()
    else:
        session.quit()
