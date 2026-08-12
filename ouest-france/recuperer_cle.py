"""Recupere la cle API Algolia de Ouest-France (valable ~24 h).

Fait a la main : ouvrir ouest-france.fr/recherche/, inspecter, onglet Reseau,
filtrer "algo", cliquer une requete "queries", onglet Headers, copier
x-algolia-api-key et x-algolia-application-id.

Ici : Firefox ouvre la page, ses scripts appellent Algolia comme d'habitude, et
on relit les en-tetes envoyes. On ne pilote pas l'interface DevTools (Selenium
ne sait pas le faire) : on ecoute le journal reseau du navigateur via WebDriver
BiDi, qui est la source meme de l'onglet Network.

    python -m ouest-france.recuperer_cle           # affiche les cles
    eval $(python -m ouest-france.recuperer_cle --export)   # OF_ALGOLIA_KEY=...
"""
import sys
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

URL = "https://www.ouest-france.fr/recherche/"
APP_ID_VOULU = "C8KP7JV01T"  # l'index articles ; l'autre (76T47RYM6W) = archives papier
ATTENTE = 12  # secondes de navigation, le temps que les appels Algolia partent

options = Options()
options.add_argument("--headless")
options.enable_bidi = True  # journal reseau (equivalent Firefox du CDP)

navigateur = webdriver.Firefox(options=options)
requetes = []
try:
    navigateur.network.add_event_handler("before_request_sent", requetes.append)
    navigateur.get(URL)
    time.sleep(ATTENTE)
finally:
    navigateur.quit()

# ne garder que les appels a Algolia et y lire les deux en-tetes
trouvees = {}
for evenement in requetes:
    requete = evenement.get("request", {})
    if "algolia" not in requete.get("url", ""):
        continue
    entetes = {e["name"].lower(): e["value"]["value"] for e in requete.get("headers", [])}
    cle = entetes.get("x-algolia-api-key")
    app_id = entetes.get("x-algolia-application-id")
    if cle and app_id:
        trouvees[app_id] = cle

if not trouvees:
    sys.exit("Aucune requete Algolia captee : la page a peut-etre change.")

app_id = APP_ID_VOULU if APP_ID_VOULU in trouvees else sorted(trouvees)[0]

if "--export" in sys.argv:
    print(f'export OF_ALGOLIA_APP_ID="{app_id}"')
    print(f'export OF_ALGOLIA_KEY="{trouvees[app_id]}"')
else:
    for autre_id, autre_cle in sorted(trouvees.items()):
        marque = "  <-- index articles" if autre_id == APP_ID_VOULU else ""
        print(f"App ID : {autre_id}{marque}")
        print(f"Cle    : {autre_cle}\n")
