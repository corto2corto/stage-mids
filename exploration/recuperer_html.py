"""Scrape une ou plusieurs URLs et sauve le HTML brut dans exploration/html/.

Sert à inspecter en local ce que Firefox+bypass a réellement récupéré (pour
diagnostiquer un échec d'extraction : sélecteur absent ? bypass raté ?).

Un seul Firefox est ouvert pour toutes les URLs (comme en prod), afin de
reproduire les conditions d'un run enchaîné.

À lancer SUR LE SERVEUR :

    python -m exploration.recuperer_html
"""

import os

from scraping.navigateur import RACINE, configurer_ublock, ouvrir_firefox, scraper

SORTIE = RACINE / "exploration" / "html"

# nom de fichier -> URL. Le nom devient <nom>.html dans exploration/html/.
CIBLES = {
    "lemonde_ko_ferrare":      "https://www.lemonde.fr/archives/article/1945/04/21/vers-ferrare-et-vers-bologne_1858584_1819218.html",
    "lemonde_ok_sanfrancisco": "https://www.lemonde.fr/archives/article/1945/04/21/avant-la-conference-de-san-francisco_1858640_1819218.html",
}

os.makedirs(SORTIE, exist_ok=True)
configurer_ublock()
driver = ouvrir_firefox()
try:
    for nom, url in CIBLES.items():
        html = scraper(driver, url)
        chemin = SORTIE / f"{nom}.html"
        chemin.write_text(html, encoding="utf-8")
        print(f"{nom:30} {len(html):>8} chars  ->  {chemin}")
finally:
    driver.quit()
