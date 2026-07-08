"""Verse dans urls.db les URLs des CSV absentes de la base, média par média.
Étape « nourrir la base » du pipeline quotidien (après exploration.sitemap_news
qui remplit les CSV), et resynchronisation à la demande.

S'appuie sur l'index UNIQUE (media, url) : chaque URL du CSV est proposée en
INSERT OR IGNORE — la base insère les nouvelles (etat=0) et écarte
instantanément les connues, sans relire toute la table. Conséquences :

- efficace : aucun scan de la base, l'index tranche ;
- sûr : que des INSERT (etat=0), jamais d'UPDATE/DELETE ; un doublon (media,url)
  est structurellement impossible (contrainte unique) ;
- idempotent : réexécutable, un média déjà versé donne 0 inséré ;
- un média absent de la base est initialisé quand même (utile après un mapping) ;
- médias en pause / dans EXCLUS ignorés ;
- lignes sans URL exploitable (vide, déchet, octet de crash) comptées à part,
  jamais insérées.

Pas de sauvegarde automatique (le quotidien n'ajoute que des lignes ignorées
si connues) : pour un gros versement ponctuel, sauvegarder la base avant.

    python -m exploration.verser_nouveaux            # tous les médias
    python -m exploration.verser_nouveaux le_figaro  # un seul
"""
import csv
import sys
from pathlib import Path

from exploration.collecte import url_article
from scraping.medias import MEDIAS
from scraping.stockage import DATA_DIR
import sqlite3

SOURCES = [Path("data/urls"), Path("exploration")]

# Médias temporairement écartés du versement (aucun pour l'instant).
EXCLUS = set()

conn = sqlite3.connect(DATA_DIR / "urls.db", timeout=60)
medias = sys.argv[1:] or sorted(MEDIAS)
total = 0
for media in medias:
    if media in EXCLUS:
        print(f"{media:<24} exclu (cf. EXCLUS) : ignoré", flush=True)
        continue
    if MEDIAS[media].get("pause"):
        print(f"{media:<24} en pause : ignoré", flush=True)
        continue
    chemin = next((d / f"{media}_url.csv" for d in SOURCES
                   if (d / f"{media}_url.csv").exists()), None)
    if not chemin:
        print(f"{media:<24} aucun CSV : ignoré", flush=True)
        continue
    urls, ignorees = [], 0
    with open(chemin, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)  # en-tête (url ou sitemap,url)
        for champs in r:
            u = url_article(champs)
            if u:
                urls.append(u)
            else:
                ignorees += 1
    avant = conn.total_changes
    with conn:  # une transaction par média
        conn.executemany("INSERT OR IGNORE INTO urls (media, url, etat) VALUES (?, ?, 0)",
                         [(media, u) for u in urls])
    inserees = conn.total_changes - avant
    suffixe = f", {ignorees} ignorées" if ignorees else ""
    print(f"{media:<24} {len(urls):>8} au CSV{suffixe}, {inserees:>6} insérées", flush=True)
    total += inserees

print(f"\nTerminé : {total} URLs insérées.")
conn.close()
