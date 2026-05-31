import time

from bs4 import BeautifulSoup

from scrapers.bypass_firefox import configurer_ublock, ouvrir_firefox, scraper

# 3 URLs d'affilée pour vérifier : 1 seul téléchargement uBlock + cookies vidés entre chaque
URLS = [
    "https://www.lejdd.fr/politique/lue-prete-a-interdire-le-parti-dont-est-membre-reconquete-au-parlement-europeen-175125",
    "https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226",
    "https://www.lemonde.fr/international/article/2026/05/08/donald-trump-minore-la-mise-en-peril-du-cessez-le-feu-en-iran-apres-des-echanges-de-tirs_6686886_3210.html",
]

configurer_ublock()

t0 = time.time()
driver = ouvrir_firefox()
print(f"Ouverture (install extensions + download uBlock) : {time.time() - t0:.1f}s")

try:
    for i, url in enumerate(URLS, 1):
        t = time.time()
        html = scraper(driver, url)
        paragraphes = BeautifulSoup(html, "html.parser").find_all("p")
        print(f"\n===== URL {i} : {time.time() - t:.1f}s  —  {len(paragraphes)} balises <p>  —  {url} =====")
        for p in paragraphes:
            print(p.get_text())
finally:
    driver.quit()