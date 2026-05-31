import os
import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

EXTENSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "extensions", "firefox")

options = Options()
options.add_argument("--headless")

with webdriver.Firefox(options=options) as driver:
    for xpi in os.listdir(EXTENSIONS_DIR):
        if xpi.endswith(".xpi"):
            driver.install_addon(os.path.join(EXTENSIONS_DIR, xpi), temporary=True)

    # about:addons liste les extensions chargées dans Firefox
    driver.get("about:addons")
    time.sleep(2)

    # La page about:addons utilise un shadow DOM, on passe par le titre de la page
    # et on récupère le texte visible pour voir les extensions listées
    html = driver.page_source
    with open("test_addons.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Vérification rapide dans le HTML
    for nom in ["uBlock", "Bypass"]:
        if nom.lower() in html.lower():
            print(f"[OK] {nom} détecté dans about:addons")
        else:
            print(f"[KO] {nom} NON détecté dans about:addons")