"""
Inspecte la fin du contenu d'un article et détecte un éventuel paywall, ou bien si l'article est vide.
"""

import re

SIGNAUX_BLOCAGE = [
    r"il vous reste\s*[\d.,]+\s*%\s*(de cet article|à découvrir|à lire)",
    r"réservée?s? aux abonnés",
    r"envie de lire la suite",
    r"débloquer votre article",
]
_PATRON = re.compile("|".join(SIGNAUX_BLOCAGE), re.IGNORECASE)

# supprimer ce genre de variable inutile. 
LONGUEUR_FIN = 300   # nombre de caractères de fin de contenu inspectés


def est_bloque(contenu):
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
