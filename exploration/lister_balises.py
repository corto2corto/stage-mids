"""Liste tous les couples (tag, class) uniques d'un fichier HTML.

Lancement : python exploration/lister_balises.py exploration/html/le_monde.html
"""

import sys
from pathlib import Path
from bs4 import BeautifulSoup

chemin = Path(sys.argv[1])
soup = BeautifulSoup(chemin.read_text(encoding="utf-8"), "html.parser")

# Les <meta> portent leur info dans name/property/content (pas dans class) :
# on les affiche en entier pour repérer les métadonnées standardisées
# (og:title, description, article:published_time, etc.).
print("=== META ===")
for tag in soup.find_all("meta"):
    print(tag)

print("\n=== TAGS (tag + class) ===")
vus = set()
for tag in soup.find_all(True):
    if tag.name == "meta":
        continue
    classes = " ".join(tag.get("class", []))
    cle = f"<{tag.name}> {classes}".strip()
    if cle not in vus:
        vus.add(cle)
        print(cle)
