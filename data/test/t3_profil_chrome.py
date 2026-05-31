import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Dépôt source décompressé de l'extension bypass-paywalls-chrome-clean (contient manifest.json)
EXTENSION = "/data/elias/stage-mids/extensions/bypass-paywalls-chrome-clean-master"

URL = "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516"
OUTPUT = "/data/elias/stage-mids/data/test/article.html"

start = time.time()

options = Options()

# Nouveau mode headless : seul headless capable de charger des extensions.
options.add_argument("--headless=new")

# Charger l'extension depuis son dossier source décompressé,
# et désactiver toutes les autres pour éviter les conflits.
options.add_argument(f"--load-extension={EXTENSION}")
options.add_argument(f"--disable-extensions-except={EXTENSION}")

# Forcer l'activation des extensions (headless les désactive parfois en douce).
options.add_argument("--enable-extensions")
options.add_argument("--disable-extensions-file-access-check")

# Stabilité sur serveur Linux.
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

# User-agent réaliste : certains sites servent un paywall plus dur aux UA "headless".
options.add_argument(
    "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)

with webdriver.Chrome(options=options) as driver:
    # Laisser le service worker de l'extension (Manifest V3) démarrer
    # AVANT de charger l'article — sinon le paywall passe avant l'interception.
    time.sleep(5)

    driver.get(URL)
    time.sleep(10)  # laisser l'extension agir + la page se charger

    # Un reload force la page à repasser par les règles de l'extension,
    # désormais bien initialisée au 1er chargement.
    driver.refresh()
    time.sleep(8)

    html = driver.page_source

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

with open(OUTPUT, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

print(f"HTML sauvegardé dans {OUTPUT} ({len(html)} caractères)")
print(f"Temps d'exécution : {time.time() - start:.1f}s")

for p in soup.find_all("p"):
    print(p.get_text())