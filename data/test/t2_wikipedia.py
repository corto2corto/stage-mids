import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = "https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal"

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

with webdriver.Chrome(options=options) as driver:
    driver.get(URL)
    time.sleep(3)
    html = driver.page_source

print(html[:2000])
