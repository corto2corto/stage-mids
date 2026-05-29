import shutil
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

PROFIL_MODELE = "/data/elias/stage-mids/extensions/chrome-bpc"
URL = ""  # à renseigner

profil_temp = tempfile.mkdtemp()
shutil.copytree(PROFIL_MODELE, profil_temp, dirs_exist_ok=True)

options = Options()
options.add_argument(f"--user-data-dir={profil_temp}")
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

with webdriver.Chrome(options=options) as driver:
    driver.get(URL)
    time.sleep(10)
    html = driver.page_source

with open("/data/elias/stage-mids/data/test/article.html", "w", encoding="utf-8") as f:
    f.write(html)
