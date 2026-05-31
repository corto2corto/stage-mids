import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Profil Chrome NATIF Linux, créé par Chrome lui-même au 1er lancement.
# (On n'utilise PLUS le profil chrome-bpc venu de Windows : ses chemins internes
#  contiennent des "\" Windows qui font planter le renderer sur Linux.)
PROFIL = "/data/elias/stage-mids/extensions/chrome-linux-profile"

# Extension décompressée (OS-neutre), chargée DANS ce profil neuf.
EXTENSION = "/data/elias/stage-mids/extensions/bypass-paywalls-chrome-clean-master"

URL = "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516"
OUTPUT = "/data/elias/stage-mids/data/test/article.html"

start = time.time()

options = Options()
options.add_argument(f"--user-data-dir={PROFIL}")
options.add_argument(f"--load-extension={EXTENSION}")

# Nouveau mode headless : seul headless capable de charger des extensions.
options.add_argument("--headless=new")

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