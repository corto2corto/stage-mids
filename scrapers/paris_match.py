import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.parismatch.com/actu/societe/exclusif-larmee-explore-sa-future-arme-anti-drone-268773"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    driver.delete_all_cookies()
    driver.get(URL)
    time.sleep(2)
    html = driver.page_source

with open(r"docs\paris_match.html", "w", encoding="utf-8") as f:
    f.write(html)