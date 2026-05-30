import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

URL = "https://fr.wikipedia.org/wiki/Wikip%C3%A9dia:Accueil_principal"
OUTPUT = "wikipedia.html"

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

with webdriver.Chrome(options=options) as driver:
    driver.get(URL)
    time.sleep(3)
    html = driver.page_source

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

with open(OUTPUT, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

for p in soup.find_all("p"):
    print(p.texts)
