import os
import time

debut = time.time()

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

EXTENSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "extensions", "firefox")
URL = "https://www.lejdd.fr/politique/lue-prete-a-interdire-le-parti-dont-est-membre-reconquete-au-parlement-europeen-175125"
ATTENTE = 5  # secondes laissées aux extensions pour agir

options = Options()
options.add_argument("--headless")

# Aucun profil spécifié : geckodriver crée un profil neuf et jetable à chaque
# lancement, puis le supprime sur .quit() (appelé par le `with`). Rien ne
# survit d'un run à l'autre → script idempotent par défaut.
with webdriver.Firefox(options=options) as driver:
    for xpi in os.listdir(EXTENSIONS_DIR):
        if xpi.endswith(".xpi"):
            driver.install_addon(os.path.join(EXTENSIONS_DIR, xpi), temporary=True)
    driver.get(URL)
    time.sleep(ATTENTE)  # laisse bypass-paywalls retirer le paywall
    html = driver.page_source

print(f"Temps de scraping : {time.time() - debut:.2f}s")

with open("test.html", "w", encoding="utf-8") as f:
    f.write(html)

soup = BeautifulSoup(html, "html.parser")
for p in soup.find_all("p"):
    print(p.get_text())
