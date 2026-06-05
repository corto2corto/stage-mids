"""Dump du HTML d'articles dans exploration/html/.

Mode normal  : une URL aléatoire par média depuis la BDD (new_batch).
Mode ciblé   : URLs fixes dans URLS_CIBLES — utile pour diagnostiquer des
               articles précis (ex. templates récents qui cassent l'extraction).

Lancement depuis la racine du dépôt :
    python -m exploration.dump_html
"""

from pathlib import Path

from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
from scraping.batch import new_batch
from scraping.pipeline import ouvrir_multi_firefox, scraper_batch

HTML_DIR = Path(__file__).resolve().parent / "html"

# URLs à dumper explicitement (mode ciblé). Vide = mode normal (new_batch).
# Format : (nom_fichier_sortie, url)
URLS_CIBLES = [
    ("le_figaro_recent",  "https://www.lefigaro.fr/international/guerre-en-ukraine-un-missile-balistique-fait-18-morts-a-kryvyi-rig-la-ville-d-origine-de-zelensky-20250405"),
    ("le_monde_recent_1", "https://www.lemonde.fr/a-la-une/article/2005/06/20/crise-dans-les-transports-franciliens_664088_3208.html"),
    ("le_monde_recent_2", "https://www.lemonde.fr/m-perso/article/2017/06/02/le-duel-koh-lanta-versus-the-island_5137977_4497916.html"),
]


def main():
    configurer_ublock()
    HTML_DIR.mkdir(exist_ok=True)

    if URLS_CIBLES:
        driver = ouvrir_firefox()
        try:
            for nom, url in URLS_CIBLES:
                html = scraper(driver, url)
                chemin = HTML_DIR / f"{nom}.html"
                chemin.write_text(html, encoding="utf-8")
                print(f"{nom}: OK -> {chemin}")
        finally:
            driver.quit()
    else:
        batch = new_batch()
        navigateurs = ouvrir_multi_firefox(batch)
        try:
            resultats = scraper_batch(batch, navigateurs)
            for media, (_, url, html) in resultats.items():
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
