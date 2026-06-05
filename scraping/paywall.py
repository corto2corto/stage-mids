"""Détection paywall : un article est-il bloqué (à retester) ou complet ?

Logique unique, valable pour TOUS les journaux (pas de réglage par média) :
un article est BLOQUÉ — donc à noter état 1 (à retester) — si l'un des deux cas :

1. Corps vide : aucun paragraphe extrait (ex. un live Figaro, ou un conteneur
   d'article absent de la page).
2. Une expression de blocage apparaît dans les 3 DERNIÈRES balises du corps.

Pourquoi seulement la fin : un message de coupure (« il vous reste X % »,
« réservé aux abonnés »…) est toujours le DERNIER élément d'un article tronqué.
Un badge en tête de page, ou un article correctement débloqué, n'en a pas en fin
→ on évite les faux positifs sur du contenu complet.
"""

import re

from bs4 import BeautifulSoup

from scraping import extraction

# Expressions de blocage, tous journaux confondus (casse ignorée). À n'inclure
# QUE si on est sûr qu'elles signalent une coupure, où qu'elles apparaissent.
SIGNAUX_BLOCAGE = [
    r"il vous reste\s*[\d.,]+\s*%\s*(de cet article|à découvrir|à lire)",  # le_monde, le_figaro
    r"réservée?s? aux abonnés",          # telerama, les_echos, paris_match, le_nouvel_obs
    r"envie de lire la suite",           # le_monde (archives)
    r"débloquer votre article",          # nice_matin
]
_PATRON = re.compile("|".join(SIGNAUX_BLOCAGE), re.IGNORECASE)

N_FIN = 3   # nombre de dernières balises inspectées


def _paragraphes(media, soup):
    """Textes non vides des <p> du corps (même sélection que extraction.py)."""
    regle = extraction.MEDIAS[media]["corps"]
    if regle == "article":
        conteneur = soup.find("article")
        elements = conteneur.find_all("p") if conteneur else []
    else:
        sel = soup.select(regle)
        elements = sel[0].find_all("p") if len(sel) == 1 and sel[0].name != "p" else sel
    return [t for p in elements if (t := p.get_text(" ", strip=True))]


def est_bloque(media, html):
    """True si l'article est bloqué (corps vide, ou blocage en fin) → à retester."""
    paras = _paragraphes(media, BeautifulSoup(html, "html.parser"))
    if not paras:
        return True
    return _PATRON.search(" ".join(paras[-N_FIN:])) is not None
