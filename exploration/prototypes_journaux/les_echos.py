import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

USER_DATA_DIR = r"C:\Users\E.E\Desktop\STAGE\Dashboard\stage-mids\chrome-bpc"
URL = "https://www.lesechos.fr/idees-debats/editos-analyses/superprofit-et-supercherie-2230754"

options = Options()
options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
options.add_argument("--incognito")

with webdriver.Chrome(options=options) as driver:
    driver.get(URL)
    time.sleep(6)
    html = driver.page_source

with open(r"docs\les_echos.html", "w", encoding="utf-8") as f:
    f.write(html)