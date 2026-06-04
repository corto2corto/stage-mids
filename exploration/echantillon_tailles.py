"""Échantillonne la taille des articles SANS bypass ni extension.

But : mesurer le nombre de mots par article pour repérer un pattern de
troncature (article paywallé = toujours ~N mots ?).

    python exploration/echantillon_tailles.py
"""

import os
import sqlite3
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

_TMP = "/data/elias/tmp/firefox"
if os.path.isdir(_TMP):
    os.environ["TMPDIR"] = _TMP

BASE = "/data/elias/stage-mids/data/urls.db"
MEDIAS = [
    "le_monde", "le_figaro", "le_journal_du_dimanche", "paris_match",
    "le_capital", "les_echos", "valeurs_actuelles", "le_nouvel_observateur",
    "nice_matin", "telerama",
]
N_PAR_MEDIA = 10
ATTENTE = 2
SORTIE = "exploration/echantillon_tailles2.txt"

options = Options()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

conn = sqlite3.connect(BASE)

with open(SORTIE, "w", encoding="utf-8") as f:
    for media in MEDIAS:
        rows = conn.execute(
            "SELECT id, url FROM urls WHERE media=? ORDER BY RANDOM() LIMIT ?",
            (media, N_PAR_MEDIA),
        ).fetchall()

        f.write(f"\n{'#'*40}\n######## MEDIA: {media}\n{'#'*40}\n")
        print(f"\n== {media} ({len(rows)} URLs)")

        for id, url in rows:
            driver.delete_all_cookies()
            driver.get(url)
            time.sleep(ATTENTE)

            paras = [
                p.get_text(" ", strip=True)
                for p in BeautifulSoup(driver.page_source, "html.parser").find_all("p")
                if p.get_text(strip=True)
            ]
            n_mots = sum(len(p.split()) for p in paras)

            f.write(f"\n==== [id={id}] {n_mots} mots ====\n{url}\n")
            for i, p in enumerate(paras):
                f.write(f"[p{i}] {p}\n")
            print(f"  id={id}: {n_mots} mots")

conn.close()
driver.quit()
print(f"\nÉcrit dans {SORTIE}")
