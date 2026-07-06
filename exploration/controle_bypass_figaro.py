"""Controle positif du dispositif de test bypass : le_figaro est scrape avec
succes en prod via Firefox + extensions. Si notre Firefox de test recupere ici
nettement plus de texte que basic sur un article payant du Figaro, c'est que
l'extension bypass etait bien active pendant tester_firefox_bypass -- et donc
que les gains x1.00 mesures sur lexpress/marianne/liberation/paris_normandie
sont une vraie limite de ces sites, pas un defaut du dispositif.

A lancer sur le serveur :  python -m exploration.controle_bypass_figaro
"""
from bs4 import BeautifulSoup

from scraping import basic
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper

URLS = [
    "https://www.lefigaro.fr/festival-de-cannes/des-films-qui-n-en-finissent-plus-le-festival-de-cannes-vu-par-eric-neuhoff-20260516",
    "https://www.lefigaro.fr/international/russie-vladimir-poutine-a-signe-un-decret-facilitant-la-delivrance-de-passeports-russes-en-transnistrie-20260516",
]

configurer_ublock()
session = basic.ouvrir_session()
driver = ouvrir_firefox()
try:
    for url in URLS:
        mots = {}
        for source in ("ff", "basic"):
            try:
                html = scraper(driver, url) if source == "ff" else basic.scraper(session, url)
                corps = BeautifulSoup(html, "html.parser").select_one("div.fig-content-body")
                mots[source] = len(corps.get_text(" ").split()) if corps else 0
            except Exception as e:
                mots[source] = f"ECHEC {type(e).__name__}"
        gain = isinstance(mots["ff"], int) and isinstance(mots["basic"], int) and mots["ff"] > 1.5 * mots["basic"]
        print(f"ff={mots['ff']} basic={mots['basic']} -> {'BYPASS ACTIF' if gain else 'pas de gain'}  {url[:80]}", flush=True)
finally:
    driver.quit()
