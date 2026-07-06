"""Sonde les nouveaux medias (tout exploration/<media>_url.csv dont le media
n'est pas encore dans MEDIAS) pour choisir leur moteur de scraping et leur
strategie d'extraction (futures entrees de scraping/medias.py). Pour chaque
media, prend 10 URLs reparties dans son csv (les sitemaps etant grossierement
chronologiques, ca varie les periodes et melange articles gratuits/payants),
recupere le HTML via le moteur "basic" (curl_cffi, sans navigateur) et regarde :
- la requete passe-t-elle sans Selenium (statut HTTP, blocage TLS/CDN) ?
- JSON-LD Article : present ? isAccessibleForFree ? taille d'articleBody
  (article complet dans le HTML servi = cas JDD, moteur basic suffisant),
- conteneurs HTML les plus riches en <p> : piste pour le selecteur "corps".

Les csv ne sont jamais charges entierement (certains font ~1 Go) : une passe
pour compter les lignes, une pour cueillir les positions voulues.

A lancer sur le serveur :  python -m exploration.sonder_nouveaux_medias
SONDE_DIR=data/urls SONDE_TOUS=1 : sonder les anciens medias (deja dans MEDIAS).
"""
import csv
import os
import time
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from scraping.basic import ouvrir_session, scraper
from scraping.extraction import noeud_json_ld
from scraping.medias import MEDIAS
from scraping.paywall import est_bloque

N_PAR_MEDIA = 10

session = ouvrir_session()
for chemin in sorted(Path(os.environ.get("SONDE_DIR", "exploration")).glob("*_url.csv")):
    media = chemin.stem.removesuffix("_url")
    if media in MEDIAS and not os.environ.get("SONDE_TOUS"):
        continue

    # Passe 1 : compter les lignes sans rien garder en memoire.
    with open(chemin, newline="", encoding="utf-8") as f:
        total = sum(1 for _ in f) - 1
    if total <= 0:
        print(f"\n=== {media} : csv vide, ignore ===")
        continue

    # Passe 2 : cueillir N URLs reparties (5 %, 15 %, ..., 95 % du fichier).
    positions = {int(total * (0.05 + 0.10 * i)) for i in range(N_PAR_MEDIA)}
    echantillon = []
    with open(chemin, newline="", encoding="utf-8") as f:
        for i, ligne in enumerate(csv.DictReader(f)):
            if i in positions:
                echantillon.append(ligne["url"])

    print(f"\n=== {media} ({total} URLs dans le csv, {len(echantillon)} sondees) ===", flush=True)
    bilan = Counter()
    conteneurs = Counter()
    for url in echantillon:
        try:
            html = scraper(session, url)
        except Exception as e:
            bilan["echec"] += 1
            print(f"  ECHEC {type(e).__name__:<22} {url[:95]}", flush=True)
            time.sleep(1)
            continue
        bilan["ok"] += 1

        soup = BeautifulSoup(html, "html.parser")
        try:
            article = noeud_json_ld(soup)
        except Exception:
            article = {}
        corps_ld = str(article.get("articleBody", ""))
        free = str(article.get("isAccessibleForFree", "")).lower()
        texte_p = " ".join(p.get_text() for p in soup.find_all("p"))
        mots_ld, mots_p = len(corps_ld.split()), len(texte_p.split())
        bloque = est_bloque(corps_ld or texte_p)

        bilan["json_ld"] += bool(article)
        bilan["free_oui"] += free == "true"
        bilan["free_non"] += free == "false"
        # "complet" : du texte substantiel et pas de phrase-signal paywall en fin.
        bilan["complet"] += (max(mots_ld, mots_p) >= 100) and not bloque

        # Conteneurs directs les plus riches en <p> : candidats pour "corps".
        for p in soup.find_all("p"):
            classes = ".".join(p.parent.get("class", []))
            conteneurs[p.parent.name + ("." + classes if classes else "")] += 1

        print(f"  ld={'oui' if article else 'NON'} free={(free or '?'):5} body={mots_ld:5} "
              f"p={mots_p:5} bloque={'oui' if bloque else 'non'}  {url[:80]}", flush=True)
        time.sleep(1)  # politesse envers le serveur

    print(f"  --- bilan {media} : {bilan['ok']}/{len(echantillon)} ok, {bilan['echec']} echecs, "
          f"json_ld={bilan['json_ld']}, free oui/non={bilan['free_oui']}/{bilan['free_non']}, "
          f"complets={bilan['complet']}, conteneurs={conteneurs.most_common(3)}", flush=True)
