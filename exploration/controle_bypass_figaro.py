"""Controle positif du dispositif de test bypass : le_figaro est scrape en prod
via Firefox + extensions. On repere d'abord de VRAIS articles premium
(isAccessibleForFree=false, corps tronque en basic) dans le csv de prod, puis
on compare Firefox+bypass vs basic sur ces articles-la uniquement.

- Si Firefox rapporte nettement plus de texte -> l'extension bypass etait bien
  active pendant tester_firefox_bypass : les gains x1.00 des nouveaux medias
  sont une vraie limite de ces sites.
- Si aucun gain meme ici -> le dispositif de test n'active pas l'extension,
  et les verdicts x1.00 ne prouvent rien.

A lancer sur le serveur :  python -m exploration.controle_bypass_figaro
"""
import csv
import time

from bs4 import BeautifulSoup

from scraping import basic
from scraping.extraction import noeud_json_ld
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper

CSV = "/data/elias/stage-mids/data/urls/le_figaro_url.csv"
N_PREMIUM = 3

# 30 URLs reparties dans le csv (colonne finale = url).
with open(CSV, newline="", encoding="utf-8") as f:
    total = sum(1 for _ in f) - 1
positions = {int(total * (i + 0.5) / 30) for i in range(30)}
urls = []
with open(CSV, newline="", encoding="utf-8") as f:
    lecteur = csv.reader(f)
    next(lecteur)
    for i, ligne in enumerate(lecteur):
        if i in positions and ligne and ligne[-1].startswith("http"):
            urls.append(ligne[-1])

# Reperage des premium via basic.
session = basic.ouvrir_session()
premium = []
for url in urls:
    try:
        soup = BeautifulSoup(basic.scraper(session, url), "html.parser")
        article = noeud_json_ld(soup)
    except Exception:
        continue
    if str(article.get("isAccessibleForFree", "")).lower() == "false":
        corps = soup.select_one("div.fig-content-body")
        premium.append((url, len(corps.get_text(" ").split()) if corps else 0))
        if len(premium) >= N_PREMIUM:
            break
    time.sleep(1)
print(f"{len(premium)} articles premium reperes (sur {len(urls)} sondes)", flush=True)

# Comparaison Firefox+bypass sur ces memes articles.
configurer_ublock()
driver = ouvrir_firefox()
try:
    for url, mots_basic in premium:
        try:
            soup = BeautifulSoup(scraper(driver, url), "html.parser")
            corps = soup.select_one("div.fig-content-body")
            mots_ff = len(corps.get_text(" ").split()) if corps else 0
        except Exception as e:
            print(f"ff=ECHEC {type(e).__name__}  {url[:80]}", flush=True)
            continue
        gain = mots_ff > 1.5 * mots_basic if mots_basic else mots_ff > 150
        print(f"premium ff={mots_ff:5} basic={mots_basic:5} -> "
              f"{'BYPASS ACTIF' if gain else 'PAS DE GAIN'}  {url[:80]}", flush=True)
finally:
    driver.quit()
