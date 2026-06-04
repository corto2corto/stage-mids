"""Compare un article AVANT / APRÈS bypass, à uBlock constant.

Protocole (pour isoler l'effet du bypass, et lui seul) :
1. Passe « contrôle » : Firefox + uBlock SEUL  -> version paywallée.
2. Extraction des <p> via les sélecteurs de extraction.py (mêmes balises que la prod).
3. Passe « bypass »   : Firefox + uBlock + extension bypass -> version complète.
4. Ré-extraction des mêmes balises.
5. Recherche des signaux + comparaison (longueurs, ratio, fin du corps).

uBlock est présent DANS LES DEUX passes : la seule variable qui change est le
bypass, donc toute différence dans le corps extrait lui est imputable.

On ne traite QUE les articles payants (free != "oui" dans le JSON-LD) : inutile
de comparer un article gratuit, identique des deux côtés.

Un signal de troncature fiable = présent dans la fin du corps « contrôle » ET
absent du corps « bypass » (le bypass devant aussi nettement rallonger le texte).

À lancer SUR LE SERVEUR (chemins /data/elias, dossier extensions/firefox) :

    python -m exploration.comparaison_bypass
"""

import os
import re
import sqlite3
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from scraping import extraction
from scraping.config import BASE, EXTENSIONS_DIR, SCRAPERS, TMP_DIR
from scraping.navigateur import (
    ATTENTE_LISTES,
    GECKODRIVER_PATH,
    configurer_ublock,
    scraper,
)
from scraping.paywall import SIGNAUX_PAYWALL

N_CANDIDATS = 6                         # URLs tirées par média (avant filtre payant)
PAYANTS_SEULEMENT = True                # ignore les articles free == "oui"
N_BALISES_FIN = 3                       # nb de derniers <p> montrés (la « fin »)
SORTIE = "exploration/comparaison_bypass.txt"


def classer_xpi():
    """Sépare les .xpi en (uBlock, bypass) d'après leur nom de fichier.

    Heuristique : un .xpi dont le nom contient « ublock » est uBlock ; tout le
    reste est considéré comme du bypass. Les deux listes sont affichées au
    démarrage pour vérification (à ajuster ici si un nom de fichier trompe).
    """
    ublock, bypass = [], []
    for nom in sorted(os.listdir(EXTENSIONS_DIR)):
        if not nom.endswith(".xpi"):
            continue
        chemin = os.path.join(EXTENSIONS_DIR, nom)
        (ublock if "ublock" in nom.lower() else bypass).append(chemin)
    return ublock, bypass


def ouvrir_firefox(xpis):
    """Firefox headless avec exactement les extensions données (liste de .xpi)."""
    os.environ["TMPDIR"] = str(TMP_DIR)
    options = Options()
    options.add_argument("--headless")
    options.set_preference("permissions.default.image", 2)
    if os.path.exists(GECKODRIVER_PATH):
        driver = webdriver.Firefox(options=options, service=Service(GECKODRIVER_PATH))
    else:
        driver = webdriver.Firefox(options=options)
    for xpi in xpis:
        driver.install_addon(xpi, temporary=True)
    time.sleep(ATTENTE_LISTES)          # uBlock télécharge ses listes une fois
    return driver


def selectionner_p(regle, soup):
    """Mêmes balises que extraction.extraire_corps, mais renvoyées en liste.

    Logique recopiée à l'identique de extraction.extraire_corps (on ne modifie
    pas extraction.py) ; le sélecteur, lui, reste lu dans extraction.MEDIAS.
    """
    if regle == "article":
        conteneur = soup.find("article")
        return conteneur.find_all("p") if conteneur else []
    elements = soup.select(regle)
    if len(elements) == 1 and elements[0].name != "p":
        return elements[0].find_all("p")
    return elements


def analyser(media, html):
    """(meta, [textes des <p>]) via la logique de sélection de extraction.py."""
    soup = BeautifulSoup(html, "html.parser")
    cfg = extraction.MEDIAS[media]
    meta = (extraction.meta_json_ld(soup) if cfg["meta"] == "json_ld"
            else extraction.meta_corps(soup))
    paras = [t for p in selectionner_p(cfg["corps"], soup)
             if (t := p.get_text(" ", strip=True))]
    return meta, paras


def candidats():
    """{media: [(id, url), ...]} : N_CANDIDATS URLs tirées au hasard par média."""
    tirage = {}
    with sqlite3.connect(BASE) as conn:
        for media in SCRAPERS:
            tirage[media] = conn.execute(
                "SELECT id, url FROM urls WHERE media=? ORDER BY RANDOM() LIMIT ?",
                (media, N_CANDIDATS),
            ).fetchall()
    return tirage


def n_mots(paras):
    return sum(len(p.split()) for p in paras)


def fin(paras):
    """Les N_BALISES_FIN derniers <p> (là où se loge un message de troncature)."""
    return paras[-N_BALISES_FIN:]


def main():
    configurer_ublock()
    ublock, bypass = classer_xpi()
    print(f"uBlock : {[os.path.basename(x) for x in ublock]}")
    print(f"bypass : {[os.path.basename(x) for x in bypass]}")
    if not ublock:
        print("!! Aucun .xpi uBlock détecté — vérifie classer_xpi()."); return

    tirage = candidats()

    # --- Passe 1 : contrôle (uBlock seul) -> on garde les articles payants -----
    retenus = []   # (media, id, url, paras_ctrl, free)
    print("\n=== PASSE 1 : uBlock seul (paywallé) ===")
    driver = ouvrir_firefox(ublock)
    try:
        for media, rows in tirage.items():
            for id, url in rows:
                meta, paras = analyser(media, scraper(driver, url))
                free = meta.get("free", "")
                if PAYANTS_SEULEMENT and free == "oui":
                    print(f"  {media} id={id}: gratuit -> ignoré")
                    continue
                retenus.append((media, id, url, paras, free))
                print(f"  {media} id={id}: {n_mots(paras)} mots (free={free or '?'})")
    finally:
        driver.quit()

    # --- Passe 2 : bypass (uBlock + extension) sur les MÊMES URLs --------------
    print("\n=== PASSE 2 : uBlock + bypass (complet) ===")
    resultats = []   # (media, id, url, free, paras_ctrl, paras_byp)
    driver = ouvrir_firefox(ublock + bypass)
    try:
        for media, id, url, paras_ctrl, free in retenus:
            _, paras_byp = analyser(media, scraper(driver, url))
            resultats.append((media, id, url, free, paras_ctrl, paras_byp))
            print(f"  {media} id={id}: {n_mots(paras_ctrl)} -> {n_mots(paras_byp)} mots")
    finally:
        driver.quit()

    # --- Comparaison + écriture ------------------------------------------------
    with open(SORTIE, "w", encoding="utf-8") as f:
        for media, id, url, free, p_ctrl, p_byp in resultats:
            n_c, n_b = n_mots(p_ctrl), n_mots(p_byp)
            ratio = (n_b / n_c) if n_c else float("inf")
            motif = SIGNAUX_PAYWALL.get(media) or ""
            sig_c = bool(motif) and re.search(motif, " ".join(p_ctrl), re.I) is not None
            sig_b = bool(motif) and re.search(motif, " ".join(p_byp), re.I) is not None

            f.write(f"\n{'='*70}\n{media}  id={id}  free={free or '?'}\n{url}\n")
            f.write(f"mots : controle={n_c}  bypass={n_b}  ratio=x{ratio:.2f}\n")
            f.write(f"signal actuel ({motif or 'aucun'}) : "
                    f"controle={'OUI' if sig_c else 'non'}  bypass={'OUI' if sig_b else 'non'}\n")
            f.write(f"--- fin du corps CONTROLE ({N_BALISES_FIN} dernieres balises) ---\n")
            for p in fin(p_ctrl):
                f.write(f"  • {p}\n")
            f.write(f"--- fin du corps BYPASS ({N_BALISES_FIN} dernieres balises) ---\n")
            for p in fin(p_byp):
                f.write(f"  • {p}\n")

    print(f"\nÉcrit dans {SORTIE}  ({len(resultats)} articles payants comparés)")


if __name__ == "__main__":
    main()
