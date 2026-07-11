"""Diagnostic one-shot : pourquoi les ~1 800 articles le_monde rejoués (tri du
11/07) échouent-ils tous avec le compte abonné, alors que le flux quotidien et
12 000 articles payants passent ?

Une seule connexion au compte, puis :
- 1 contrôle = dernier article payant réussi (free=non) du CSV de sortie ;
- 5 URLs du résidu (etat 0/1) ;
- la 1re URL du résidu retestée avec attente 10 s (hypothèse rendu trop lent).

Pour chaque page : verdict est_bloque, nb de mots, champ free, fin du texte.
Les HTML bruts sont gardés dans data/backup/diag_residu_lemonde/ pour inspection.

    python -m exploration.tester_residu_lemonde
"""
import csv
import sqlite3

from scraping.connexion import ouvrir_firefox_connecte
from scraping.extraction import extraire
from scraping.navigateur import configurer_ublock, scraper
from scraping.paywall import est_bloque
from scraping.stockage import DATA_DIR

csv.field_size_limit(2**31 - 1)

DOSSIER = DATA_DIR / "backup" / "diag_residu_lemonde"
DOSSIER.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(f"file:{DATA_DIR / 'urls.db'}?mode=ro", uri=True)
residu = conn.execute("SELECT id, url FROM urls WHERE media='le_monde' "
                      "AND etat IN (0, 1) LIMIT 5").fetchall()
conn.close()

# Contrôle : le dernier article payant scrapé en entier (preuve que le compte marche).
controle = None
with open(DATA_DIR / "csv" / "le_monde.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["free"] == "non":
            controle = (row["id"], row["url"])

cas = [("controle", *controle, 3)]
cas += [(f"residu{i}", id, url, 3) for i, (id, url) in enumerate(residu, 1)]
cas.append(("residu1_attente10", residu[0][0], residu[0][1], 10))

configurer_ublock()
driver = ouvrir_firefox_connecte("le_monde")
print(f"page après login : {driver.current_url}")
try:
    for etiquette, id, url, attente in cas:
        html = scraper(driver, url, attente, garder_cookies=True)
        meta = extraire("le_monde", html)
        mots = len(meta["contenu"].split())
        verdict = "BLOQUÉ" if est_bloque(meta["contenu"]) else "OK"
        print(f"\n== {etiquette} (id={id}, attente={attente}s) : "
              f"{verdict}, {mots} mots, free={meta['free']!r}, titre={meta['titre'][:60]!r}")
        print(f"   {url}")
        print(f"   fin : ...{meta['contenu'][-200:]}")
        (DOSSIER / f"{etiquette}_{id}_a{attente}.html").write_text(html, "utf-8")
finally:
    driver.quit()
print(f"\nHTML gardés dans {DOSSIER}")
