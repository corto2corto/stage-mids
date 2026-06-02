import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

USER_DATA_DIR = r"C:\Users\E.E\Desktop\STAGE\Dashboard\stage-mids\chrome-bpc"
URL = "https://www.lexpress.fr/secret-defense/lalgerie-et-le-maroc-se-preparent-au-pire-entre-rabat-et-alger-la-course-aux-armements-sintensifie-BEOYDZQW4ZABTIKQ3PUD6WTDXI/?cmp_redirect=true"

options = Options()
options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
options.add_argument("--incognito")

with webdriver.Chrome(options=options) as driver:
    driver.get(URL)
    time.sleep(10)
    html = driver.page_source

with open(r"docs\lexpress.html", "w", encoding="utf-8") as f:
    f.write(html)