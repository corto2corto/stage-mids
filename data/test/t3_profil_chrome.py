import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Dossier décompressé de l'extension bypass-paywalls-chrome-clean
# (situé dans le profil chrome-bpc, sous Default/Extensions/<id>/<version>)
EXTENSION = "/data/elias/stage-mids/extensions/bypass-paywalls-chrome-clean-master"

URL = "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516"
OUTPUT = "/data/elias/stage-mids/data/test/article.html"

start = time.time()

options = Options()

# Nouveau mode headless : c'est le SEUL headless qui charge les extensions.
options.add_argument("--headless=new")

# Charger l'extension directement depuis son dossier décompressé.
options.add_argument(f"--load-extension={EXTENSION}")
options.add_argument(f"--disable-extensions-except={EXTENSION}")

# Stabilité sur serveur Linux.
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

with webdriver.Chrome(options=options) as driver:
    driver.get(URL)
    time.sleep(10)  # laisser l'extension agir + la page se charger
    html = driver.page_source

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

with open(OUTPUT, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

print(f"HTML sauvegardé dans {OUTPUT} ({len(html)} caractères)")
print(f"Temps d'exécution : {time.time() - start:.1f}s")

for p in soup.find_all("p"):
    print(p.get_text())

