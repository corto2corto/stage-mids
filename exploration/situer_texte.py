"""Situe un bout de texte dans le HTML : affiche la balise qui le contient
et la chaîne de ses parents (tag.class), pour repérer quoi cibler.

Lancement :
    python exploration/situer_texte.py exploration/html/les_echos.html "Laurent Dandrieu"
"""

import sys
from pathlib import Path
from bs4 import BeautifulSoup


def chemin_parents(tag):
    """Renvoie 'html > body > ... > tag.classe' en remontant les parents."""
    morceaux = []
    for parent in reversed(list(tag.parents)):
        if parent.name in ("[document]", None):
            continue
        classes = ".".join(parent.get("class", []))
        morceaux.append(f"{parent.name}.{classes}" if classes else parent.name)
    classes = ".".join(tag.get("class", []))
    morceaux.append(f"{tag.name}.{classes}" if classes else tag.name)
    return " > ".join(morceaux)


chemin = Path(sys.argv[1])
recherche = sys.argv[2]
soup = BeautifulSoup(chemin.read_text(encoding="utf-8"), "html.parser")

# Élément le plus profond (le plus précis) contenant le texte recherché
trouve = False
for tag in soup.find_all(True):
    if tag.string and recherche in tag.string:
        trouve = True
        print(chemin_parents(tag))
        print(f"   -> texte : {tag.string.strip()[:80]!r}")
        print()

if not trouve:
    print(f"Texte {recherche!r} introuvable dans une balise feuille.")
    print("(il est peut-être éclaté sur plusieurs balises enfants)")
