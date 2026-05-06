from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False = navigateur visible
    page = browser.new_page()
    stealth_sync(page)  # masque les traces d'automatisation
    page.goto("https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226")
    page.wait_for_load_state("domcontentloaded")
    
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")
paragraphes = soup.find_all("p")

for p in paragraphes:
    text = str(p)
    print(p)