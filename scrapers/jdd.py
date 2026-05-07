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
    
    # On télécharge le html dans un fichier, qu'on passera à BS4 ensuite

with open("173226.html", "w", encoding="utf-8") as f:
    f.write(html)