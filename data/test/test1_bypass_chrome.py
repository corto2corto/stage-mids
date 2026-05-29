import shutil
import tempfile
import time
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

PROFIL_MODELE = "/data/elias/stage-mids/extensions/chrome-bpc"
URL = "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516"

profil_temp = tempfile.mkdtemp()
shutil.copytree(PROFIL_MODELE, profil_temp, dirs_exist_ok=True)

options = Options()
options.add_argument(f"--user-data-dir={profil_temp}")
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--remote-debugging-port=0")

service = Service(log_output="/data/elias/stage-mids/data/test/chromedriver.log")

with webdriver.Chrome(options=options, service=service) as driver:
    driver.get(URL)
    time.sleep(10)
    html = driver.page_source

with open("/data/elias/stage-mids/data/test/article.html", "w", encoding="utf-8") as f:
    f.write(html)
