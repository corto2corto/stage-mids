# Même principe que pour le JDD, mais on ajoute un timeur car le bypass est plus long.

import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.lemonde.fr/international/article/2026/05/08/donald-trump-minore-la-mise-en-peril-du-cessez-le-feu-en-iran-apres-des-echanges-de-tirs_6686886_3210.html"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    time.sleep(2)
    html = driver.page_source

with open(r"docs\le_monde.html", "w", encoding="utf-8") as f:
    f.write(html)