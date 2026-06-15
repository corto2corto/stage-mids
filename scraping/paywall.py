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


def est_bloque(contenu, longueur_fin=300):
    if not contenu.strip():
        return True
    return _PATRON.search(contenu[-longueur_fin:]) is not None


if __name__ == "__main__":
    import sys
    from scraping.extraction import extraire_url

    media, url = sys.argv[1], sys.argv[2]
    contenu = extraire_url(media, url)["contenu"]
    print(f"bloqué : {est_bloque(contenu)}")
    print(f"fin    : ...{contenu[-250:]}")
