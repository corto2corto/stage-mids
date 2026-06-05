"""Diagnostic : pourquoi certains articles RÉCENTS donnent 0 mot à l'extraction ?

Sur des templates récents, le sélecteur de extraction.py (ex. div.fig-content-body
pour le_figaro, div.article__content pour le_monde) ne capte plus rien. Ce script
récupère le HTML (via navigateur.py : uBlock + bypass) des URLs problématiques et,
pour chacune, affiche :
1. ce que rend le sélecteur ACTUEL (nb de <p>, nb de mots) ;
2. le conteneur RÉEL : la classe du parent le plus fréquent des <p> « longs »
   (vrai texte d'article) — c'est le sélecteur de remplacement candidat ;
3. le top des conteneurs riches en <p>, pour vérifier à l'œil.

On ne modifie rien : on observe, pour ensuite corriger extraction.MEDIAS à la main.

URLS = liste (media, url) à diagnostiquer. Par défaut : les articles à 0 mot vus
dans comparaison_bypass.txt. À compléter au besoin.

    python -m exploration.diagnostic_selecteurs
"""

from collections import Counter

from bs4 import BeautifulSoup

from scraping import extraction
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper

SORTIE = "exploration/diagnostic_selecteurs.txt"
SEUIL_LONG = 200          # un <p> de + de 200 caractères = vrai paragraphe d'article

URLS = [
    ("le_figaro", "https://www.lefigaro.fr/international/guerre-en-ukraine-un-missile-balistique-fait-18-morts-a-kryvyi-rig-la-ville-d-origine-de-zelensky-20250405"),
    ("le_monde",  "https://www.lemonde.fr/a-la-une/article/2005/06/20/crise-dans-les-transports-franciliens_664088_3208.html"),
    ("le_monde",  "https://www.lemonde.fr/m-perso/article/2017/06/02/le-duel-koh-lanta-versus-the-island_5137977_4497916.html"),
]


def cle(el):
    """Étiquette lisible d'un élément : tag.classe1.classe2."""
    classes = ".".join(el.get("class", []))
    return f"{el.name}.{classes}" if classes else f"{el.name}(sans-classe)"


def selecteur_actuel(media, soup):
    """(règle, nb de mots) rendus par le sélecteur de extraction.py."""
    regle = extraction.MEDIAS[media]["corps"]
    corps = extraction.extraire_corps(regle, soup)
    return regle, len(corps.split())


def conteneur_reel(soup):
    """Parent le plus fréquent des <p> « longs » = conteneur d'article candidat."""
    longs = [p for p in soup.find_all("p") if len(p.get_text(strip=True)) >= SEUIL_LONG]
    parents = Counter(cle(p.find_parent()) for p in longs if p.find_parent())
    return longs, parents


def top_conteneurs(soup, n=10):
    """Top des éléments par nombre de <p> descendants (dédupliqués par étiquette)."""
    compte = {}
    for el in soup.find_all(["div", "article", "section", "main"]):
        nb = len(el.find_all("p", recursive=True))
        if nb >= 3:
            etq = cle(el)
            compte[etq] = max(compte.get(etq, 0), nb)
    return sorted(compte.items(), key=lambda kv: kv[1], reverse=True)[:n]


def main():
    configurer_ublock()
    driver = ouvrir_firefox()
    try:
        with open(SORTIE, "w", encoding="utf-8") as f:
            for media, url in URLS:
                soup = BeautifulSoup(scraper(driver, url), "html.parser")

                regle, n_mots = selecteur_actuel(media, soup)
                longs, parents = conteneur_reel(soup)

                f.write(f"\n{'='*70}\n{media}\n{url}\n")
                f.write(f"sélecteur actuel : {regle!r} -> {n_mots} mots\n")
                f.write(f"<p> longs (>{SEUIL_LONG} car.) trouvés : {len(longs)}\n")

                f.write("\nparent le + fréquent des <p> longs (= conteneur réel) :\n")
                for etq, nb in parents.most_common(5):
                    f.write(f"  {nb:3} × {etq}\n")

                f.write("\ntop conteneurs riches en <p> :\n")
                for etq, nb in top_conteneurs(soup):
                    f.write(f"  {nb:3} <p> | {etq}\n")

                if longs:
                    f.write(f"\nexemple de <p> long :\n  {longs[0].get_text(' ', strip=True)[:200]}\n")
                print(f"{media}: {n_mots} mots (sélecteur actuel), {len(longs)} <p> longs")
        print(f"\nÉcrit dans {SORTIE}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
