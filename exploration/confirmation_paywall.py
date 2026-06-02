"""Récupère le texte des pages payantes AVEC le bypass actif (extension + uBlock).

À relancer sur les MÊMES URLs que reperage_paywall.py (qui, lui, scrape sans
bypass), pour comparer : les phrases-signal de troncature repérées sans bypass
doivent DISPARAÎTRE quand le bypass fonctionne. Teste tous les médias, y compris
les paywalls « mous » (pour voir s'il y a un changement notable).

Réutilise le vrai mécanisme de prod (scraping/navigateur.py) : ce test valide
donc aussi ce module. À lancer sur le serveur, depuis la racine du dépôt :

    python exploration/confirmation_paywall.py
"""

import os
import sys

from bs4 import BeautifulSoup

# Rend le package scraping/ importable quel que soit le dossier de lancement.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper

# Mêmes URLs que la passe sans bypass, pour une comparaison directe.
URLS = {
    "le_figaro":              "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516",
    "le_monde":               "https://www.lemonde.fr/archives/article/1945/04/21/avant-la-conference-de-san-francisco_1858640_1819218.html",
    "le_nouvel_observateur":  "https://www.nouvelobs.com/musique/20260602.OBS115437/areski-belkacem-est-mort-et-il-restera-injustement-et-pour-l-eternite-dans-l-ombre-de-brigitte-fontaine.html",
    "les_echos":              "https://www.lesechos.fr/monde/europe/faut-il-parler-a-poutine-la-question-cruciale-qui-tourmente-les-europeens-2233690",
    "paris_match":            "https://www.parismatch.com/culture/cinema/antonin-baudry-le-general-de-gaulle-cest-quelquun-a-bout-de-souffle-qui-essaie-de-porter-une-france-a-bout-de-souffle-269941",
    "telerama":               "https://www.telerama.fr/livre/ce-que-dit-boualem-sansal-dans-la-legende-son-nouveau-recit-7031419.php",
    "le_journal_du_dimanche": "https://www.lejdd.fr/Societe/emeutes-apres-psg-arsenal-la-defaite-de-lordre-public-175371",
    "le_capital":             "https://www.capital.fr/votre-carriere/morald-chibout-le-conseiller-qui-recadre-les-pdg-sans-detour-1527026",
    "nice_matin":             "https://www.nicematin.com/economie/commerce/depuis-1890-cette-famille-cultive-la-vigne-du-domaine-du-blavet-a-roquebrune-sur-argens-10683092",
}


def main():
    configurer_ublock()
    driver = ouvrir_firefox()   # installe les .xpi + attend le téléchargement des listes
    try:
        for media, url in URLS.items():
            html = scraper(driver, url)   # cookies vidés + chargement + attente bypass
            paragraphes = BeautifulSoup(html, "html.parser").find_all("p")
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
