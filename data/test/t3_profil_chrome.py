import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Profil Chrome contenant DÉJÀ l'extension bypass-paywalls installée et configurée.
# (même approche que les scrapers locaux qui fonctionnent, ex. scrapers/lexpress.py)
PROFIL = "/data/elias/stage-mids/extensions/chrome-bpc"

URL = "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516"
OUTPUT = "/data/elias/stage-mids/data/test/article.html"

start = time.time()

options = Options()

# On passe le profil entier : l'extension est dedans, pas besoin de --load-extension.
options.add_argument(f"--user-data-dir={PROFIL}")

# Nouveau mode headless : seul headless capable de charger des extensions.
# (PAS de --incognito : la navigation privée désactive les extensions par défaut.)
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