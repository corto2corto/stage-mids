"""Moteur "basic" : récupération du HTML par simple requête HTTP, sans navigateur.

Pour les médias gratuits ou dont l'article complet est déjà dans le HTML servi
(ex : le JDD). Beaucoup plus rapide et léger en RAM que Selenium.
"""

import requests

# En-têtes d'un vrai Firefox pour ne pas être identifié comme un robot.
ENTETES = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.5,en;q=0.3",
}


def ouvrir_session():
    """Session HTTP réutilisable (cookies et connexion conservés entre les URLs)."""
    session = requests.Session()
    session.headers.update(ENTETES)
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
