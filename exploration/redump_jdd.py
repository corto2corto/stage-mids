"""Re-dumpe un article JDD standard (pas un live) dans exploration/html/.

Le dump précédent était un live (structure atypique). On écrase le_journal_du_dimanche.html
avec un article classique pour valider les sélecteurs d'extraction.

Lancement : python -m exploration.redump_jdd
"""

from pathlib import Path

from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper

URL = "https://www.lejdd.fr/economie/gregory-et-frederic-dubly-dsi-plastic-lecologie-ne-fonctionne-que-si-elle-coute-moins-cher-que-le-jetable-175533"
CIBLE = Path(__file__).resolve().parent / "html" / "le_journal_du_dimanche.html"


def main():
    configurer_ublock()
    driver = ouvrir_firefox()
    try:
        html = scraper(driver, URL)
        CIBLE.write_text(html, encoding="utf-8")
        print(f"OK -> {CIBLE} ({len(html)} caractères)")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()