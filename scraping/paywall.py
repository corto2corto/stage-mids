"""Détection paywall : le contenu extrait est-il bloqué (à retester) ou complet ?

Ce module observe la SORTIE de extraction.py — le contenu déjà extrait — et rien
d'autre (pas de HTML, pas de re-sélection de balises).

Un contenu est BLOQUÉ — donc à noter état 1 (à retester) — si :
1. il est vide (aucun texte extrait : live Figaro, conteneur d'article absent…) ;
2. une expression de blocage apparaît dans la FIN du contenu.

Pourquoi seulement la fin : un message de coupure (« il vous reste X % »,
« réservé aux abonnés »…) est toujours en bout d'article tronqué. Un badge en
tête, ou un article correctement débloqué, n'en a pas à la fin → pas de faux
positif sur du contenu complet.

Usage dans le pipeline :
    meta = extraction.extraire(media, html)
    etat = 1 if est_bloque(meta["contenu"]) else 2
"""

import re

SIGNAUX_BLOCAGE = [
    r"il vous reste\s*[\d.,]+\s*%\s*(de cet article|à découvrir|à lire)",
    r"réservée?s? aux abonnés",
    r"envie de lire la suite",
    r"débloquer votre article",
]
_PATRON = re.compile("|".join(SIGNAUX_BLOCAGE), re.IGNORECASE)

LONGUEUR_FIN = 300   # nombre de caractères de fin de contenu inspectés


def est_bloque(contenu):
    """True si le contenu extrait est bloqué (vide, ou blocage en fin)."""
    if not contenu.strip():
        return True
    return _PATRON.search(contenu[-LONGUEUR_FIN:]) is not None


if __name__ == "__main__":
    import sys

    from scraping.extraction import extraire_url

    media, url = sys.argv[1], sys.argv[2]
    contenu = extraire_url(media, url)["contenu"]
    print(f"bloqué : {est_bloque(contenu)}")
    print(f"fin    : ...{contenu[-LONGUEUR_FIN:]}")
