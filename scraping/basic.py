"""Moteur "basic" : récupération du HTML par simple requête HTTP, sans navigateur.

Pour les médias gratuits ou dont l'article complet est déjà dans le HTML servi
(ex : le JDD). Beaucoup plus rapide et léger en RAM que Selenium.

On passe par curl_cffi plutôt que requests : certains CDN (Akamai chez
paris-normandie, cf mapping_paris_normandie.py) bloquent l'empreinte TLS de
python-requests (403 systématique). curl_cffi imite un vrai Chrome (TLS +
en-têtes cohérents) et passe.
"""

from curl_cffi import requests


def ouvrir_session():
    """Session HTTP réutilisable (cookies et connexion conservés entre les URLs)."""
    session = requests.Session(impersonate="chrome")
    session.headers["Accept-Language"] = "fr-FR,fr;q=0.8,en-US;q=0.5,en;q=0.3"
    return session


def scraper(session, url):
    reponse = session.get(url, timeout=30)
    reponse.raise_for_status()
    return reponse.text


# Test : scrape une URL et affiche la fin de l'article
# python -m scraping.basic <media> <url>

if __name__ == "__main__":
    import sys

    from scraping import extraction

    media, url = sys.argv[1], sys.argv[2]
    contenu = extraction.extraire(media, scraper(ouvrir_session(), url))["contenu"]
    print(f"{len(contenu.split())} mots")
    print(f"...{contenu[-250:]}")
