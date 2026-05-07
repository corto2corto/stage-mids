from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226")
    page.wait_for_load_state()
    html = page.content()
    browser.close()

soup = BeautifulSoup(html, "html.parser")
paragraphes = soup.find_all("p")

print(len(paragraphes))