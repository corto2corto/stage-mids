import shutil
import tempfile
import chromedriver_binary
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

PROFIL_MODELE = "/data/elias/stage-mids/extensions/chrome-bpc"

profil_temp = tempfile.mkdtemp()
shutil.copytree(PROFIL_MODELE, profil_temp, dirs_exist_ok=True)

options = Options()
options.add_argument(f"--user-data-dir={profil_temp}")
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

with webdriver.Chrome(options=options) as driver:
    print("Chrome ouvert avec profil")
    print(f"Version : {driver.capabilities['browserVersion']}")
