"""Dump du HTML d'un article par média dans exploration/html/.

Lancement depuis la racine du dépôt :
    python -m exploration.dump_html
"""

import os
from pathlib import Path

from scraping.batch import new_batch
from scraping.navigateur import configurer_ublock
from scraping.pipeline import ouvrir_multi_firefox, scraper_batch

HTML_DIR = Path(__file__).resolve().parent / "html"


def main():
    configurer_ublock()
    batch = new_batch()
    navigateurs = ouvrir_multi_firefox(batch)

    try:
        resultats = scraper_batch(batch, navigateurs)
        for media, (id, url, html) in resultats.items():
            if html is None:
                print(f"{media}: ECHEC")
                continue
            chemin = HTML_DIR / f"{media}.html"
            chemin.write_text(html, encoding="utf-8")
            print(f"{media}: OK -> {chemin}")
    finally:
        for driver in navigateurs.values():
            driver.quit()


if __name__ == "__main__":
    main()
