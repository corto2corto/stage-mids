"""
Extraction des métadonnées et du corps d'un article à partir de son HTML.
"""

import json
import re
from bs4 import BeautifulSoup

from scraping.medias import MEDIAS

def noeud_json_ld(soup):
    """Renvoie le noeud Article du JSON-LD de la page (ou {})."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue   # bloc ld+json invalide (vu sur certains sites) : on passe au suivant
        # Certains sites emballent les données dans une liste sous "@graph".
        noeuds = data.get("@graph", [data]) if isinstance(data, dict) else data
        for noeud in noeuds:
            if "Article" in str(noeud.get("@type", "")):
                return noeud
    return {}


def meta_json_ld(soup):
    """ Extraction des metadatas via le json-ld"""
    article = noeud_json_ld(soup)

    auteur = article.get("author", "")
    if isinstance(auteur, dict):
        auteur = auteur.get("name") or ""         
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
        "free":    free}


def meta_balises(soup, meta):
    """Extraction des métadonnées directement dans les balises HTML (cas sans json_ld)."""
    titre = soup.select_one(meta["titre"])
    auteur = soup.select_one(meta["auteur"])
    date = soup.select_one(meta["date"])
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
    meta = MEDIAS[media]["meta"]

    infos = meta_json_ld(soup) if meta["strategie"] == "json_ld" else meta_balises(soup, meta)
    if meta["corps"] == "json_ld":
        corps = noeud_json_ld(soup).get("articleBody", "")
        infos["contenu"] = re.sub(r"\s+", " ", corps).strip()
    else:
        infos["contenu"] = extraire_corps(media, meta["corps"], soup)
    return infos


def extraire_url(media, url):
    from scraping.moteurs import fermer_session, ouvrir_session, scraper
    from scraping.navigateur import configurer_ublock

    configurer_ublock()
    session = ouvrir_session(media)
    try:
        return extraire(media, scraper(media, session, url))
    finally:
        fermer_session(media, session)


if __name__ == "__main__":
    import sys

    meta = extraire_url(sys.argv[1], sys.argv[2])
    for cle, valeur in meta.items():
        if cle == "contenu":
            print(f"contenu : {len(valeur.split())} mots")
            print(f"  ...{valeur[-400:]}")
        else:
            print(f"{cle:8}: {valeur}")