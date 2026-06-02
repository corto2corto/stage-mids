from concurrent.futures import ThreadPoolExecutor

from scrapers.bypass_chrome import bypass_chrome

SCRAPERS = {
    "le_capital":             bypass_chrome,
    "les_echos":              bypass_chrome,
    "valeurs_actuelles":      bypass_chrome,
    "le_nouvel_observateur":  bypass_chrome,
    "le_monde":               bypass_chrome,
    "le_figaro":              bypass_chrome,
    "le_journal_du_dimanche": bypass_chrome,
    "paris_match":            bypass_chrome,
    "nice_matin":             bypass_chrome,
    "telerama":               bypass_chrome,
}


def scraper_url(media, id, url):
    try:
        html = SCRAPERS[media](url)
    except Exception:
        html = None
    return media, (id, url, html)


def scraper_batch(batch):
    resultats = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        taches = [
            executor.submit(scraper_url, media, id, url)
            for media, (id, url) in batch.items()
        ]
        for tache in taches:
            media, valeur = tache.result()
            resultats[media] = valeur
    return resultats