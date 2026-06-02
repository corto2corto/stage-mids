import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

USER_DATA_DIR = "/data/elias/stage-mids/chrome-bpc"
TIMEOUT = 10


def bypass_chrome(url):
    options = Options()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--incognito")
    options.add_argument("--headless")

    with webdriver.Chrome(options=options) as driver:
        driver.get(url)
        time.sleep(TIMEOUT)
        return driver.page_source
