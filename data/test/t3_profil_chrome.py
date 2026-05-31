import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from pyvirtualdisplay import Display

# Profil Chrome NATIF Linux, créé par Chrome au 1er lancement.
# (Pas le profil chrome-bpc venu de Windows : ses chemins internes en "\"
#  font planter le renderer sur Linux.)
PROFIL = "/data/elias/stage-mids/extensions/chrome-linux-profile"

# Extension décompressée (OS-neutre), chargée DANS ce profil.
EXTENSION = "/data/elias/stage-mids/extensions/bypass-paywalls-chrome-clean-master"

URL = "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516"
OUTPUT = "/data/elias/stage-mids/data/test/article.html"

start = time.time()

# Écran virtuel (Xvfb) : Chrome tourne en mode VISIBLE sur cet écran fantôme.
# C'est ce qui permet aux extensions de fonctionner (impossible en --headless).
display = Display(visible=False, size=(1920, 1080))
display.start()

try:
    options = Options()
    options.add_argument(f"--user-data-dir={PROFIL}")
    options.add_argument(f"--load-extension={EXTENSION}")

    # PAS de --headless : c'est Xvfb qui gère l'absence d'écran physique.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    with webdriver.Chrome(options=options) as driver:
        driver.get(URL)
        time.sleep(10)  # laisser l'extension agir + la page se charger
        html = driver.page_source
finally:
    display.stop()

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

with open(OUTPUT, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

print(f"HTML sauvegardé dans {OUTPUT} ({len(html)} caractères)")
print(f"Temps d'exécution : {time.time() - start:.1f}s")

for p in soup.find_all("p"):
    print(p.get_text())