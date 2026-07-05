"""Construit la liste des URLs d'articles Marianne par pagination des 7
rubriques principales avec le parametre ?p=N (repere lors de la reco : ?page=
est ignore, ?p= pagine reellement ; profondeur reelle ~200-500 pages selon la
rubrique). Un article = slug long (>= 25 caracteres), ce qui ecarte les pages
de tags et sous-rubriques aux slugs courts. Arret d'une rubrique apres 2 pages
consecutives sans nouvelle URL (le site repete la derniere page au-dela de la
profondeur reelle).

    python -m exploration.mapping_marianne

MAPPING_LIMITE=N (env) : 1 rubrique et N pages max (smoke test).
"""
import csv
import os
import re
import time

import requests
from tqdm import tqdm

RUBRIQUES = ["politique", "societe", "economie", "monde", "culture", "art-de-vivre", "agora"]
MAX_PAGES = 600  # garde-fou anti-boucle infinie
SORTIE = "exploration/marianne_url.csv"
ENTETES = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}

max_pages = MAX_PAGES
limite = int(os.environ.get("MAPPING_LIMITE", "0"))
if limite:
    RUBRIQUES = RUBRIQUES[:1]
    max_pages = limite

urls = set()
for rubrique in RUBRIQUES:
    motif = re.compile(rf'href="(https://www\.marianne\.net/{rubrique}(?:/[a-z0-9-]+)?/[a-z0-9-]{{25,}})"')
    pages_sans_nouveaute = 0
    print(f"\n=== {rubrique} ===")
    for page in tqdm(range(1, max_pages + 1)):
        try:
            r = requests.get(f"https://www.marianne.net/{rubrique}", params={"p": page}, headers=ENTETES, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"{rubrique} p={page} : echec ({e}), ignoree")
            continue
        avant = len(urls)
        urls.update(motif.findall(r.text))
        if len(urls) == avant:
            pages_sans_nouveaute += 1
            if pages_sans_nouveaute >= 2:
                print(f"{rubrique} : fin de pagination a p={page}")
                break
        else:
            pages_sans_nouveaute = 0
        time.sleep(0.5)  # politesse envers le serveur
    # checkpoint apres chaque rubrique
    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(urls):
            w.writerow([u])
    print(f"{rubrique} termine, {len(urls)} URLs uniques cumulees")

print(f"\nTermine : {len(urls)} URLs ecrites dans {SORTIE}")
