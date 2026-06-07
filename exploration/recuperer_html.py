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
    "jdd_1": "https://www.lejdd.fr/International/guerre-au-moyen-orient-jd-vance-quitte-le-pakistan-sans-accord-avec-liran-171252",
    "jdd_2": "https://www.lejdd.fr/International/guerre-en-iran-jd-vance-au-pakistan-des-echanges-prevus-entre-le-liban-et-israel-171123",
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
