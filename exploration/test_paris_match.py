"""Vérifie le bypass Paris Match : scrape 3 URLs et extrait leur contenu.

Pour chaque URL : nb de mots extraits, verdict est_bloque(), les 3 dernières
balises, et le contenu complet — pour juger à l'œil si l'article est complet.

    python -m exploration.test_paris_match
"""

from pathlib import Path

from bs4 import BeautifulSoup

from scraping import extraction
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
from scraping.paywall import _paragraphes, est_bloque

SORTIE = Path("exploration/test_paris_match.txt")

URLS = [
    "https://www.parismatch.com/Actu/qui-achetera-la-demeure-historique-du-general-de-gaulle-estimee-a-12-million-deuros-270154",
    "https://www.parismatch.com/People/chambre-cuisine-decouvrez-en-exclusivite-les-pieces-secretes-de-la-maison-du-general-de-gaulle-270157",
    "https://www.parismatch.com/actu/politique/cette-lettre-qui-a-permis-a-churchill-de-gagner-la-guerre-269601",
]


def main():
    configurer_ublock()
    driver = ouvrir_firefox()
    try:
        with open(SORTIE, "w", encoding="utf-8") as f:
            for url in URLS:
                html = scraper(driver, url)
                meta = extraction.extraire("paris_match", html)
                paras = _paragraphes("paris_match", BeautifulSoup(html, "html.parser"))
                contenu = meta["contenu"]

                f.write(f"\n{'='*70}\n{url}\n")
                f.write(f"mots : {len(contenu.split())}   bloqué : {est_bloque('paris_match', html)}   free : {meta['free'] or '?'}\n")
                f.write("--- 3 dernières balises ---\n")
                for p in paras[-3:]:
                    f.write(f"  • {p}\n")
                f.write("--- contenu complet ---\n")
                f.write(contenu + "\n")
                print(f"{len(contenu.split()):5} mots  bloqué={est_bloque('paris_match', html)}  {url}")
        print(f"\nÉcrit dans {SORTIE}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
