"""Sonde les nouveaux medias (tout exploration/<media>_url.csv dont le media
n'est pas encore dans MEDIAS) pour choisir leur moteur de scraping et leur
strategie d'extraction (futures entrees de scraping/medias.py). Pour chaque
media, prend 3 URLs reparties dans son csv (produit par les scripts de
mapping), recupere le HTML via le moteur "basic" (curl_cffi, sans navigateur)
et regarde :
- statut HTTP (le site accepte-t-il une requete sans Selenium ?),
- JSON-LD Article : present ? isAccessibleForFree ? taille d'articleBody
  (article complet dans le HTML servi = cas JDD, moteur basic suffisant),
- conteneurs HTML les plus riches en <p> : piste pour le selecteur "corps".

A lancer sur le serveur :  python -m exploration.sonder_nouveaux_medias
"""
import csv
import time
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from scraping.basic import ouvrir_session, scraper
from scraping.extraction import noeud_json_ld
from scraping.medias import MEDIAS
from scraping.paywall import est_bloque

session = ouvrir_session()
for chemin in sorted(Path("exploration").glob("*_url.csv")):
    media = chemin.stem.removesuffix("_url")
    if media in MEDIAS:
        continue
    with open(chemin, newline="", encoding="utf-8") as f:
        urls = [ligne["url"] for ligne in csv.DictReader(f)]
    if not urls:
        print(f"\n=== {media} : csv vide, ignore ===")
        continue

    echantillon = urls[:: max(1, len(urls) // 3)][:3]
    print(f"\n=== {media} ({len(urls)} URLs dans le csv) ===")
    for url in echantillon:
        try:
            html = scraper(session, url)
        except Exception as e:
            print(f"  ECHEC {type(e).__name__} : {url[:100]}")
            continue
        soup = BeautifulSoup(html, "html.parser")
        try:
            article = noeud_json_ld(soup)
        except Exception:
            article = {}
        corps_ld = str(article.get("articleBody", ""))
        free = str(article.get("isAccessibleForFree", ""))

        # Conteneurs directs les plus riches en <p> : candidats pour "corps".
        parents = Counter()
        for p in soup.find_all("p"):
            classes = ".".join(p.parent.get("class", []))
            parents[p.parent.name + ("." + classes if classes else "")] += 1
        texte_p = " ".join(p.get_text() for p in soup.find_all("p"))

        print(f"  {url[:100]}")
        print(f"    json_ld={'oui' if article else 'NON'}  free={free or '?'}  "
              f"articleBody={len(corps_ld.split())} mots  "
              f"(bloque : {est_bloque(corps_ld) if corps_ld else '-'})")
        print(f"    <p> de la page : {len(texte_p.split())} mots  "
              f"conteneurs : {parents.most_common(3)}")
        time.sleep(1)  # politesse envers le serveur
