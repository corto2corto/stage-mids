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

# Réglage serveur : Firefox a besoin d'un tmp dédié (cf. scraping/navigateur.py)
os.environ["TMPDIR"] = "/data/elias/tmp/firefox"

ATTENTE = 3  # laisse la page (et son paywall) s'afficher

# Une URL payante par média (vérifiées manuellement comme étant derrière paywall)
URLS = {
    "le_capital":             "https://www.capital.fr/votre-carriere/morald-chibout-le-conseiller-qui-recadre-les-pdg-sans-detour-1527026",
    "le_figaro":              "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516",
    "le_journal_du_dimanche": "https://www.lejdd.fr/International/suede-la-fin-de-lillusion-multiculturaliste-175155",
    "le_monde":               "https://www.lemonde.fr/archives/article/1945/04/21/avant-la-conference-de-san-francisco_1858640_1819218.html",
    "le_nouvel_observateur":  "https://www.nouvelobs.com/musique/20260602.OBS115437/areski-belkacem-est-mort-et-il-restera-injustement-et-pour-l-eternite-dans-l-ombre-de-brigitte-fontaine.html",
    "les_echos":              "https://www.lesechos.fr/monde/europe/faut-il-parler-a-poutine-la-question-cruciale-qui-tourmente-les-europeens-2233690",
    "nice_matin":             "https://www.nicematin.com/societe/justice/violences-gratuites-propos-homophobes-3-ans-de-prison-pour-l-agresseur-de-deux-etudiants-roues-de-coups-pres-de-la-gare-de-cannes-10683099",
    "paris_match":            "https://www.parismatch.com/culture/cinema/antonin-baudry-le-general-de-gaulle-cest-quelquun-a-bout-de-souffle-qui-essaie-de-porter-une-france-a-bout-de-souffle-269941",
    "telerama":               "https://www.telerama.fr/livre/ce-que-dit-boualem-sansal-dans-la-legende-son-nouveau-recit-7031419.php",
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
