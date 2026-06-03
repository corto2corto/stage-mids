"""Test du bypass Paris Match : l'extension arrive-t-elle à débloquer le contenu ?

Paris Match utilise Poool qui masque le texte via data-poool-mode="hide".
L'extension doit retirer cet attribut via JS. On teste ici si attendre plus
longtemps change quelque chose — ce qui distingue un problème de timing
d'un blocage structurel (Poool détecte headless et ne charge pas le contenu).

    python exploration/test_paris_match.py
"""

import os
import sys
import time

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping.navigateur import configurer_ublock, ouvrir_firefox

URL = "https://www.parismatch.com/People/je-sais-que-ma-carriere-est-terminee-tentatives-de-viol-agressions-sexuelles-affaire-patrick-bruel-nos-revelations-269775"

SIGNAL = "la suite de cet article est réservée aux abonnés"
DELAIS = [5, 10, 20]   # on lit le DOM après chaque palier (en secondes cumulées)


def afficher(label, html):
    paragraphes = BeautifulSoup(html, "html.parser").find_all("p")
    signal_present = SIGNAL.lower() in html.lower()
    print(f"\n{'=' * 20}")
    print(f"== {label}  ({len(paragraphes)} <p>)  —  signal paywall : {signal_present}")
    print(f"{'=' * 20}")
    for i, p in enumerate(paragraphes):
        texte = p.get_text(strip=True)
        if texte:
            print(f"[{i}] {texte}")


def main():
    configurer_ublock()
    driver = ouvrir_firefox()
    try:
        driver.delete_all_cookies()
        driver.get(URL)

        elapsed = 0
        for delai in DELAIS:
            time.sleep(delai - elapsed)
            elapsed = delai
            afficher(f"t={delai}s", driver.page_source)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
