# Essayer une version avec request pour améliorer performances

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.valeursactuelles.com/societe/lexposition-vivre-ensemble-de-yann-arthus-bertrand-a-paris-saccagee-par-des-supporters-celebrant-la-qualification-du-psg-en-finale-de-la-ligue-des-champions"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    driver.delete_all_cookies()
    driver.get(URL)
    html = driver.page_source

with open(r"docs\v_a.html", "w", encoding="utf-8") as f:
    f.write(html)