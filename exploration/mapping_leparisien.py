"""Construit la liste des URLs d'articles du Parisien via les pages
d'archives par jour /archives/YYYY/JJ-MM-YYYY/ (verifiees lors de la reco :
elles remontent au moins a 2005 ; on part de 2010 pour couvrir large avant le
rachat LVMH de 2015). ~6 000 jours a 0.3 s -> environ 1h15 de crawl.
Motif article : lien protocole-relatif //www.leparisien.fr/...-JJ-MM-AAAA-ID.php,
ou ID est numerique dans les vieilles pages (2015 : -4864079.php) et un hash
alphanumerique majuscule depuis (2026 : -FUNC2C6F6ZHEVNFWNCMK4CYB7I.php).

    python -m exploration.mapping_leparisien

MAPPING_LIMITE=N (env) : ne parcourt que les N derniers jours (smoke test).
"""
import csv
import os
import re
import time
from datetime import date, timedelta

import requests
from tqdm import tqdm

DEBUT = date(2010, 1, 1)
SORTIE = "exploration/leparisien_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
MOTIF_ARTICLE = re.compile(r'href="(?:https:)?//www\.leparisien\.fr(/[^"]*-\d{2}-\d{2}-\d{4}-[A-Z0-9]+\.php)"')

jours = []
d = DEBUT
while d <= date.today():
    jours.append(d)
    d += timedelta(days=1)
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    jours = jours[-limite:]
print(f"{len(jours)} pages jour a parcourir")

urls = set()
for i, d in enumerate(tqdm(jours), 1):
    page = f"https://www.leparisien.fr/archives/{d.year}/{d.strftime('%d-%m-%Y')}/"
    try:
        r = requests.get(page, headers=ENTETES, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"{page} : echec ({e}), ignoree")
        continue
    urls.update("https://www.leparisien.fr" + m for m in MOTIF_ARTICLE.findall(r.text))
    if i % 200 == 0:  # checkpoint
        with open(SORTIE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["url"])
            for u in sorted(urls):
                w.writerow([u])
    time.sleep(0.3)  # politesse envers le serveur

with open(SORTIE, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["url"])
    for u in sorted(urls):
        w.writerow([u])
print(f"{len(urls)} URLs ecrites dans {SORTIE}")
