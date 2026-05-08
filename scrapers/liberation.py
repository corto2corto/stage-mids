# Cette fois, on a dû ajouter une ligne qui "clear" les cookies, sinon le bypass ne marche pas

import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.liberation.fr/international/asie-pacifique/lenfer-des-scam-centers-13-la-france-dans-la-ligne-de-mire-de-la-cyberescroquerie-20260508_LUPH6W65FREIJF7TVI4PIBMLQU/"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    driver.delete_all_cookies()
    driver.get(URL)
    time.sleep(2)
    html = driver.page_source

with open(r"docs\liberation.html", "w", encoding="utf-8") as f:
    f.write(html)