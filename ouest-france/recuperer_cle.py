"""Recupere la cle API Algolia de Ouest-France (valable ~24 h).

Fait a la main : ouvrir ouest-france.fr/recherche/, inspecter, onglet Reseau,
filtrer "algo", cliquer une requete "queries", onglet Headers, copier
x-algolia-api-key et x-algolia-application-id.

Ici : Firefox ouvre la page, ses scripts appellent Algolia comme d'habitude, et
on relit les en-tetes envoyes. On ne pilote pas l'interface DevTools (Selenium
ne sait pas le faire) : on ecoute le journal reseau du navigateur via WebDriver
BiDi, qui est la source meme de l'onglet Network.

    python ouest-france/recuperer_cle.py           # affiche les cles
    eval $(python ouest-france/recuperer_cle.py --export)   # OF_ALGOLIA_KEY=...
"""
import base64
import sys
import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://www.ouest-france.fr/recherche/"
APP_ID_VOULU = "C8KP7JV01T"  # l'index articles ; l'autre (76T47RYM6W) = archives papier
INDEX_VOULU = "articles"

options = Options()
options.add_argument("--headless")
options.enable_bidi = True  # journal reseau (equivalent Firefox du CDP)

navigateur = webdriver.Firefox(options=options)
requetes = []
try:
    navigateur.network.add_event_handler("before_request_sent", requetes.append)
    navigateur.get(URL)

    # lancer une vraie recherche : sans ca le site ne demande qu'une cle
    # limitee a l'index "shopping", inutilisable sur "articles"
    champ = WebDriverWait(navigateur, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type=search], input[type=text]"))
    )
    champ.send_keys("rachat")
    champ.send_keys(Keys.ENTER)
    time.sleep(8)
finally:
    navigateur.quit()


def porte_sur(cle, index):
    """Une cle Algolia encode sa portee en base64 : restrictIndices=a,b,c."""
    try:
        droits = base64.b64decode(cle).decode("utf-8", "replace")
    except Exception:
        return False
    if "restrictIndices=" not in droits:
        return True  # pas de restriction listee
    portee = droits.split("restrictIndices=")[1].split("&")[0]
    return index in urllib.parse.unquote(portee).split(",")


# ne garder que les appels a Algolia et y lire les deux en-tetes ;
# une meme App ID sert plusieurs cles, on garde celle qui couvre l'index voulu
trouvees = {}
for evenement in requetes:
    requete = evenement.get("request", {})
    if "algolia" not in requete.get("url", ""):
        continue
    entetes = {e["name"].lower(): e["value"]["value"] for e in requete.get("headers", [])}
    cle = entetes.get("x-algolia-api-key")
    app_id = entetes.get("x-algolia-application-id")
    if not (cle and app_id):
        continue
    if app_id not in trouvees or porte_sur(cle, INDEX_VOULU):
        trouvees[app_id] = cle

if not trouvees:
    sys.exit("Aucune requete Algolia captee : la page a peut-etre change.")

app_id = APP_ID_VOULU if APP_ID_VOULU in trouvees else sorted(trouvees)[0]
if app_id == APP_ID_VOULU and not porte_sur(trouvees[app_id], INDEX_VOULU):
    sys.exit(f"Cle captee mais sans acces a l'index {INDEX_VOULU} : la recherche n'a pas abouti.")

if "--export" in sys.argv:
    print(f'export OF_ALGOLIA_APP_ID="{app_id}"')
    print(f'export OF_ALGOLIA_KEY="{trouvees[app_id]}"')
else:
    for autre_id, autre_cle in sorted(trouvees.items()):
        marque = "  <-- index articles" if autre_id == APP_ID_VOULU else ""
        print(f"App ID : {autre_id}{marque}")
        print(f"Cle    : {autre_cle}\n")
