"""Teste si Firefox + extensions bypass paywall recupere plus de texte que le
moteur basic, sur les medias ou la sonde a montre du payant tronque ou des
blocages (lepoint, lexpress, marianne, liberation, paris_normandie) et sur les
deux medias a confirmer (latribune, midilibre).

Pour chaque media, 15 URLs reparties dans exploration/<media>_url.csv ; chaque
URL est recuperee DEUX fois : via Firefox+bypass (scraping.navigateur) et via
basic (scraping.basic). On compare le nombre de mots des deux versions : si
Firefox rapporte nettement plus de texte sur les articles payants, le bypass
fonctionne ; s'il rapporte pareil, basic suffit (ou le bypass echoue).

Tous les HTML sont sauves dans exploration/html_v2/ (<media>_<n>_<ff|basic>.html)
pour l'exploration des selecteurs "corps" de medias.py.

Un seul Firefox ouvert a la fois (RAM), referme apres chaque media.
A lancer sur le serveur :  python -m exploration.tester_firefox_bypass
"""
import csv
import time
from pathlib import Path
from statistics import median

from bs4 import BeautifulSoup

from scraping import basic
from scraping.extraction import noeud_json_ld
from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper
from scraping.paywall import est_bloque

A_TESTER = ["lepoint", "lexpress", "marianne", "liberation", "paris_normandie",
            "latribune", "midilibre"]
N_PAR_MEDIA = 15
SORTIE = Path("exploration/html_v2")
SORTIE.mkdir(exist_ok=True)

configurer_ublock()
session = basic.ouvrir_session()
for media in A_TESTER:
    chemin = Path("exploration") / f"{media}_url.csv"

    # Echantillon : 15 positions reparties, sans charger le csv (jusqu'a ~1 Go).
    with open(chemin, newline="", encoding="utf-8") as f:
        total = sum(1 for _ in f) - 1
    positions = {int(total * (i + 0.5) / N_PAR_MEDIA) for i in range(N_PAR_MEDIA)}
    echantillon = []
    with open(chemin, newline="", encoding="utf-8") as f:
        for i, ligne in enumerate(csv.DictReader(f)):
            if i in positions:
                echantillon.append(ligne["url"])

    dispo = [l for l in open("/proc/meminfo") if l.startswith("MemAvailable")][0].split()[1]
    print(f"\n=== {media} ({len(echantillon)} URLs, RAM dispo {int(dispo)//1024**2} Go) ===", flush=True)

    driver = ouvrir_firefox()
    gains_payant = []   # ratio texte <p> firefox / basic sur les articles payants
    try:
        for num, url in enumerate(echantillon, 1):
            pages = {}
            try:
                pages["ff"] = scraper(driver, url)
            except Exception as e:
                print(f"  ff=ECHEC {type(e).__name__:<18} {url[:85]}", flush=True)
            try:
                pages["basic"] = basic.scraper(session, url)
            except Exception:
                pass

            # Mots du json-ld et des <p>, statut payant, signal paywall — par version.
            stats = {}
            for source, html in pages.items():
                (SORTIE / f"{media}_{num:02d}_{source}.html").write_text(html, encoding="utf-8")
                soup = BeautifulSoup(html, "html.parser")
                try:
                    article = noeud_json_ld(soup)
                except Exception:
                    article = {}
                corps = str(article.get("articleBody", ""))
                texte_p = " ".join(p.get_text() for p in soup.find_all("p"))
                stats[source] = (len(corps.split()), len(texte_p.split()),
                                 str(article.get("isAccessibleForFree", "")).lower(),
                                 est_bloque(corps or texte_p))
            if "ff" not in stats:
                time.sleep(1)
                continue
            ff_ld, ff_p, free_ff, ff_bloque = stats["ff"]
            ba_ld, ba_p, free_ba, _ = stats.get("basic", (0, 0, "", False))
            free = free_ff or free_ba or "?"
            if free == "false" and ba_p:
                gains_payant.append(ff_p / ba_p)
            print(f"  free={free:5} ff: ld={ff_ld:5} p={ff_p:5} bloque={'oui' if ff_bloque else 'non'} | "
                  f"basic: ld={ba_ld:5} p={ba_p:5}  {url[:70]}", flush=True)
            time.sleep(1)
    finally:
        driver.quit()

    verdict = (f"gain median firefox/basic sur payant = x{median(gains_payant):.2f} "
               f"({len(gains_payant)} payants)") if gains_payant else "aucun payant comparable"
    print(f"  --- bilan {media} : {verdict}", flush=True)

print("\n=== TEST BYPASS TERMINE ===", flush=True)
