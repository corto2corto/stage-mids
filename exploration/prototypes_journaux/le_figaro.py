import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.lefigaro.fr/international/l-elysee-annonce-le-retour-de-son-ambassadeur-a-alger-et-amorce-un-degel-prudent-20260508"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    time.sleep(2)
    html = driver.page_source

with open(r"docs\le_figaro.html", "w", encoding="utf-8") as f:
    f.write(html)