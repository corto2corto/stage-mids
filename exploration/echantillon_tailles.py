"""Échantillonne la taille des articles, SANS bypass ni extension.

But : récupérer plusieurs articles par média (texte des <p> seulement) et
mesurer leur longueur en mots, pour voir s'il existe un pattern de troncature
exploitable — par ex. un article tronqué plafonne toujours autour de N mots,
là où un article complet en fait beaucoup plus.

Tout est écrit dans un .txt unique, article par article, avec le nombre de mots
en tête de chaque article, pour étude tranquille ensuite.

Firefox headless SANS extension : on veut justement voir la version paywallée.

    python exploration/echantillon_tailles.py
"""

import os
import sqlite3
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from scraping.config import BASE, SCRAPERS

# Réglage serveur : Firefox a besoin d'un tmp dédié (cf. scraping/navigateur.py).
# Ignoré en local (ex : Mac) si le dossier n'existe pas.
_TMP = "/data/elias/tmp/firefox"
if os.path.isdir(_TMP):
    os.environ["TMPDIR"] = _TMP

N_PAR_MEDIA = 8                        # nombre d'URLs à récupérer par média
ATTENTE = 2                            # sleep entre requêtes (ne pas surcharger)
SORTIE = "exploration/echantillon_tailles.txt"


def urls_par_media(n):
    """Retourne {media: [(id, url), ...]} : n URLs par média depuis la base."""
    echantillon = {}
    with sqlite3.connect(BASE) as conn:
        for media in SCRAPERS:
            rows = conn.execute(
                "SELECT id, url FROM urls WHERE media=? LIMIT ?", (media, n)
            ).fetchall()
            echantillon[media] = rows
    return echantillon


def ouvrir_firefox_nu():
    """Firefox headless SANS extension ni bypass : on veut voir le paywall."""
    options = Options()
    options.add_argument("--headless")
    return webdriver.Firefox(options=options)


def texte_paragraphes(html):
    """Liste des textes non vides des balises <p>."""
    soup = BeautifulSoup(html, "html.parser")
    return [t for p in soup.find_all("p") if (t := p.get_text(" ", strip=True))]


def main():
    echantillon = urls_par_media(N_PAR_MEDIA)
    driver = ouvrir_firefox_nu()
    try:
        with open(SORTIE, "w", encoding="utf-8") as f:
            for media, rows in echantillon.items():
                f.write(f"\n{'#' * 40}\n######## MEDIA: {media}\n{'#' * 40}\n")
                print(f"\n== {media} ({len(rows)} URLs)")
                for id, url in rows:
                    driver.delete_all_cookies()
                    driver.get(url)
                    time.sleep(ATTENTE)
                    paras = texte_paragraphes(driver.page_source)
                    n_mots = sum(len(p.split()) for p in paras)
                    f.write(f"\n==== [id={id}] {n_mots} mots ====\n{url}\n")
                    for i, p in enumerate(paras):
                        f.write(f"[p{i}] {p}\n")
                    print(f"  id={id}: {n_mots} mots")
        print(f"\nÉcrit dans {SORTIE}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
