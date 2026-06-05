"""Extraction des métadonnées et du corps d'un article à partir de son HTML.

Chaque média est routé via le dico MEDIAS, qui dit pour ce média :
- "meta"  : d'où viennent les métadonnées (titre, auteur, date, section, free)
            -> "json_ld" (schema.org NewsArticle) ou "corps" (lu dans le HTML) ;
- "corps" : comment récupérer le texte de l'article (sélecteur CSS du conteneur,
            ou règle spéciale pour les médias sans conteneur unique).
"""

import json

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
    """Métadonnées lues dans le JSON-LD (NewsArticle). Renvoie un dict, vide si absent."""
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
    """Métadonnées lues dans le HTML (JDD : pas de JSON-LD, méta pauvres).

    L'auteur est dans <a class="author"> ; le <span class="author no-link"> qui
    le précède n'est qu'un préfixe ("Propos recueillis par") qu'on ignore.
    """
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


def extraire_corps(regle, soup):
    """Texte de l'article : <p> ciblés par la règle du média, joints par des espaces."""
    if regle == "article":
        # Nice Matin : pas de conteneur unique, on prend les <p> de tout l'article.
        conteneur = soup.find("article")
        paragraphes = conteneur.find_all("p") if conteneur else []
    else:
        # Sélecteur CSS : soit un conteneur dont on prend les <p>,
        # soit directement des <p> (ex. "p.node__paragraphe" pour le Nobs).
        elements = soup.select(regle)
        if len(elements) == 1 and elements[0].name != "p":
            paragraphes = elements[0].find_all("p")
        else:
            paragraphes = elements

    return " ".join(p.get_text() for p in paragraphes)


def extraire(media, html):
    """Renvoie les métadonnées + le contenu d'un article sous forme de dict."""
    soup = BeautifulSoup(html, "html.parser")
    config = MEDIAS[media]

    meta = meta_json_ld(soup) if config["meta"] == "json_ld" else meta_corps(soup)
    meta["contenu"] = extraire_corps(config["corps"], soup)
    return meta