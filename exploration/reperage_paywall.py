"""Récupère le texte des pages payantes SANS bypass ni extension.

But : voir ce que chaque site affiche derrière son paywall, pour repérer les
phrases-signal ("Pour lire la suite, abonnez-vous", etc.). Ces phrases
serviront ensuite à écrire bypass_checker, qui vérifiera que le bypass a bien
fonctionné (= ces phrases ont disparu) avant d'enregistrer un article.

À lancer sur le serveur (Firefox headless). Affiche, média par média, le texte
de toutes les balises <p>, numérotées.

    python exploration/reperage_paywall.py
"""

import os
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

# Réglage serveur : Firefox a besoin d'un tmp dédié (cf. scraping/navigateur.py).
# Ignoré en local (ex : Mac) si le dossier n'existe pas.
_TMP = "/data/elias/tmp/firefox"
if os.path.isdir(_TMP):
    os.environ["TMPDIR"] = _TMP

ATTENTE = 3  # laisse la page (et son paywall) s'afficher

# Une URL payante par média (vérifiées manuellement comme étant derrière paywall)
URLS = {
    "le_journal_du_dimanche": "https://www.lejdd.fr/Societe/emeutes-apres-psg-arsenal-la-defaite-de-lordre-public-175371",
    "le_capital":             "https://www.capital.fr/votre-carriere/morald-chibout-le-conseiller-qui-recadre-les-pdg-sans-detour-1527026",
    "nice_matin":             "https://www.nicematin.com/economie/commerce/depuis-1890-cette-famille-cultive-la-vigne-du-domaine-du-blavet-a-roquebrune-sur-argens-10683092",
    "paris_match":             "https://www.parismatch.com/People/je-sais-que-ma-carriere-est-terminee-tentatives-de-viol-agressions-sexuelles-affaire-patrick-bruel-nos-revelations-269775"
}


def ouvrir_firefox_nu():
    """Firefox headless SANS extension ni bypass : on veut justement voir le paywall."""
    options = Options()
    options.add_argument("--headless")
    return webdriver.Firefox(options=options)


def main():
    driver = ouvrir_firefox_nu()
    try:
        for media, url in URLS.items():
            driver.delete_all_cookies()
            driver.get(url)
            time.sleep(ATTENTE)
            paragraphes = BeautifulSoup(driver.page_source, "html.parser").find_all("p")
            print(f"\n{'=' * 20}")
            print(f"== {media}  ({len(paragraphes)} balises <p>)")
            print(f"{'=' * 20}")
            for i, p in enumerate(paragraphes):
                texte = p.get_text(strip=True)
                if texte:
                    print(f"[{i}] {texte}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
