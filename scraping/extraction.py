"""
Extraction des métadonnées et du corps d'un article à partir de son HTML.

Chaque média est routé via le dico MEDIAS, qui dit pour ce média :
- "meta"  : indique dans quels balises extraire les métadonnées (titre, auteur, date, section, free)
            soit via le "json_ld" (schema.org NewsArticle) ou alors directement dans le "corps" (lu dans le HTML) ;
- "corps" : comment récupérer le texte de l'article (sélecteur CSS du conteneur, ou règle spéciale pour les médias sans conteneur unique).
"""

import json
import re
from bs4 import BeautifulSoup

MEDIAS = {
    "le_capital":             {"meta": "json_ld", "corps": "div.articleBody"},
    "le_figaro":              {"meta": "json_ld", "corps": "div.fig-content-body"},
    "le_monde":               {"meta": "json_ld", "corps": ".article__content"},
    "telerama":               {"meta": "json_ld", "corps": "article.article__page-content"},
    "valeurs_actuelles":      {"meta": "json_ld", "corps": "div.post__content"},
    "les_echos":              {"meta": "json_ld", "corps": "div.post-paywall"},
    "paris_match":            {"meta": "json_ld", "corps": "section.content-rte"},
    "le_nouvel_observateur":  {"meta": "json_ld", "corps": "p.node__paragraphe"},
    "nice_matin":             {"meta": "json_ld", "corps": "article"},
    "le_journal_du_dimanche": {"meta": "corps",   "corps": "div.rte"},
}


def meta_json_ld(soup):
    """ Extraction des metadatas via le json-ld"""
    article = {}
    for script in soup.find_all("script", type="application/ld+json"):
        data = json.loads(script.get_text())
        # Certains sites emballent les données dans une liste sous "@graph".
        noeuds = data.get("@graph", [data]) if isinstance(data, dict) else data
        for noeud in noeuds:
            if "Article" in str(noeud.get("@type", "")):
                article = noeud
                break
        if article:
            break

    auteur = article.get("author", "")
    if isinstance(auteur, dict):
        auteur = auteur.get("name") or ""          # name peut être null (archives Échos)
    elif isinstance(auteur, list):
        auteur = ", ".join((a.get("name") or "") if isinstance(a, dict) else a for a in auteur)

    section = article.get("articleSection", "")
    if isinstance(section, list):
        section = ", ".join(section)

    # isAccessibleForFree arrive en bool (True) ou en texte ('true'/'False') : on homogénéise.
    free = str(article.get("isAccessibleForFree", "")).lower()
    free = {"true": "oui", "false": "non"}.get(free, "")

    return {
        "titre":   article.get("headline", ""),
        "auteur":  auteur,
        "date":    article.get("datePublished", ""),
        "section": section,
        "free":    free,
    }


def meta_corps(soup):
    """ Extraction des metadatas via le corp html"""
    titre = soup.find("h1", class_="main-title")
    auteur = soup.find("a", class_="author")
    date = soup.find("time")
    return {
        "titre":   titre.get_text(strip=True) if titre else "",
        "auteur":  auteur.get_text(strip=True) if auteur else "",
        "date":    date.get("datetime", "") if date else "",
        "section": "",
        "free":    "",
    }


def extraire_corps(media, regle, soup):
    if regle == "article":
        # Nice Matin : pas de conteneur unique, on prend les <p> de tout l'article.
        conteneur = soup.find("article")
        paragraphes = conteneur.find_all("p") if conteneur else []
    else:
        elements = soup.select(regle)
        if len(elements) == 1 and elements[0].name != "p":
            paragraphes = elements[0].find_all("p")
        else:
            paragraphes = elements

    if media == "paris_match" and paragraphes and \
            paragraphes[-1].get_text(strip=True) == "La suite de cet article est réservée aux abonnés.":
        paragraphes = paragraphes[:-1]

    texte = " ".join(p.get_text() for p in paragraphes)
    return re.sub(r"\s+", " ", texte).strip()   # un seul espace, pas de sauts de ligne


def extraire(media, html):
    """Renvoie les métadonnées + le contenu d'un article sous forme de dict."""
    soup = BeautifulSoup(html, "html.parser")
    config = MEDIAS[media]

    meta = meta_json_ld(soup) if config["meta"] == "json_ld" else meta_corps(soup)
    meta["contenu"] = extraire_corps(media, config["corps"], soup)
    return meta


def extraire_url(media, url):
    """Fonction facultative qui permet de scraper un URL et d'obtenir ses metadatas + contenu"""
    
    from scraping.navigateur import configurer_ublock, ouvrir_firefox, scraper

    configurer_ublock()
    driver = ouvrir_firefox()
    try:
        return extraire(media, scraper(driver, url))
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys

    meta = extraire_url(sys.argv[1], sys.argv[2])
    for cle, valeur in meta.items():
        if cle == "contenu":
            print(f"contenu : {len(valeur.split())} mots")
            print(f"  ...{valeur[-400:]}")
        else:
            print(f"{cle:8}: {valeur}")