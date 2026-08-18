"""Récupère le HTML d'une ou plusieurs URLs avec le moteur de son choix, SANS
que le média soit déclaré dans scraping/medias.py : c'est le point d'entrée
pour explorer un média qu'on ne sait pas encore scraper. Le HTML est sauvé dans
exploration/html/ pour être passé ensuite à exploration.explorer_html.

    python -m exploration.recuperer basic   <url> [url...]
    python -m exploration.recuperer firefox <url> [url...]
    python -m exploration.recuperer deux    <url> [url...]

« deux » récupère chaque URL par les DEUX moteurs et compare le nombre de mots :
c'est le test « basic suffit-il, ou faut-il Firefox + bypass ? ». Un écart net
en faveur de Firefox = le bypass sert ; à égalité sur un article payant = basic
suffit, ou le site résiste aux deux et il faut un compte abonné (moteur "log").

Pour un média DÉJÀ dans MEDIAS, préférer `python -m scraping.extraction <media> <url>`
qui applique en plus sa fiche d'extraction.

À lancer sur le serveur (le Mac n'a ni Firefox ni geckodriver).
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scraping import basic

MOTEUR, URLS = sys.argv[1], sys.argv[2:]
assert MOTEUR in ("basic", "firefox", "deux"), f"moteur inconnu : {MOTEUR}"
SORTIE = Path("exploration/html")
SORTIE.mkdir(parents=True, exist_ok=True)


def enregistrer(url, html, moteur):
    """Sauve le HTML sous <domaine>_<fin d'url>_<moteur>.html, renvoie son nombre de mots."""
    adresse = urlparse(url)
    fin = adresse.path.rstrip("/").split("/")[-1] or "index"
    slug = re.sub(r"[^a-z0-9]+", "-", fin.lower())[:60]
    chemin = SORTIE / f"{adresse.netloc.removeprefix('www.')}_{slug}_{moteur}.html"
    chemin.write_text(html, encoding="utf-8")
    mots = len(BeautifulSoup(html, "html.parser").get_text(" ").split())
    print(f"  {moteur:7} {len(html):>8} chars  {mots:>6} mots  ->  {chemin}", flush=True)
    return mots


session = basic.ouvrir_session() if MOTEUR in ("basic", "deux") else None
driver = None
if MOTEUR in ("firefox", "deux"):
    # Import tardif : selenium et geckodriver n'existent que sur le serveur,
    # le mode basic doit rester lançable en local.
    from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
    configurer_ublock()
    driver = ouvrir_firefox()

try:
    for url in URLS:
        print(url, flush=True)
        mots = {}
        if session:
            try:
                mots["basic"] = enregistrer(url, basic.scraper(session, url), "basic")
            except Exception as e:
                print(f"  basic   ECHEC {type(e).__name__}: {e}", flush=True)
            time.sleep(1)   # politesse : le HTTP est instantané, on temporise
        if driver:
            try:
                mots["ff"] = enregistrer(url, scraper(driver, url), "ff")
            except Exception as e:
                print(f"  ff      ECHEC {type(e).__name__}: {e}", flush=True)
        if len(mots) == 2:
            # Le mot-compte porte sur toute la page (menus, pubs compris) : c'est
            # l'ÉCART entre les deux moteurs qui parle, pas la valeur absolue.
            gain = mots["ff"] / mots["basic"] if mots["basic"] else float("inf")
            verdict = "bypass utile" if gain > 1.5 else "basic suffit (ou site résistant)"
            print(f"  -> gain Firefox x{gain:.2f} : {verdict}", flush=True)
finally:
    if session:
        session.close()
    if driver:
        driver.quit()
