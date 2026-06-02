from selenium import webdriver
from selenium.webdriver.firefox.options import Options

PROFILE_PATH = r"C:\Users\E.E\AppData\Roaming\Mozilla\Firefox\Profiles\m5oos7by.default-release"
URL = "https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226"

options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE_PATH)

with webdriver.Firefox(options=options) as driver:
    driver.get(URL)
    html = driver.page_source

with open("test.html", "w", encoding="utf-8") as f:
    f.write(html)