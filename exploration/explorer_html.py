"""Explore le HTML d'un article pour trouver OÙ sont ses métadonnées et son
corps — c'est-à-dire ce qu'il faut écrire dans la fiche du média
(scraping/medias.py : "strategie" et "corps").

    python -m exploration.explorer_html exploration/html/<fichier>.html
    python -m exploration.explorer_html exploration/html/<fichier>.html "un bout du texte"

Quatre sections :
- JSON-LD : le nœud Article de schema.org. Socle à privilégier (strategie
  "json_ld"), exposé par la grande majorité des médias. Pièges connus :
  auteur générique (« admin », « Le Monde ») et articleBody souvent absent
  ou tronqué — d'où le champ "corps" séparé dans la fiche.
- META : les balises normalisées (Open Graph & co), socle de repli quand le
  JSON-LD manque, et parfois seule source du free/payant. Les noms de balises
  payant/gratuit varient d'un site à l'autre (og:article:content_tier,
  ad:postAccess, pbstck_context:paywall...) : elles sont marquées d'un « ! ».
- CORPS : les conteneurs classés par quantité de texte dans leurs <p> directs,
  puis les classes de <p> les plus fréquentes. Le premier donne le conteneur
  (div.fig-content-body), le second le paragraphe (p.article__paragraph) —
  les deux moitiés du champ "corps".
- TITRES : les <h1> avec leurs classes.

Le 2e argument facultatif situe un bout de texte connu dans l'arbre (chemin de
ses parents) : indispensable sur les sites à classes hashées (Les Échos), où il
faut remonter du texte visible vers la balise à cibler.
"""
import re
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from scraping.extraction import noeud_json_ld

CHEMIN = Path(sys.argv[1])
RECHERCHE = sys.argv[2] if len(sys.argv) > 2 else None

soup = BeautifulSoup(CHEMIN.read_text(encoding="utf-8"), "html.parser")

# Balises <meta> sans intérêt pour l'extraction (affichage, réseaux sociaux,
# vérifications de propriété) : écartées pour laisser voir les autres.
META_BRUIT = re.compile(r"^(viewport|charset|theme-color|msapplication|apple-|format-detection|"
                        r"twitter:(card|site|creator|image)|fb:|google|robots|.*-verification)")
# Ce qui trahit une balise « article payant / gratuit » — nom imprévisible.
META_ACCES = re.compile(r"paywall|content_tier|postaccess|access|premium|free|abo", re.I)


def selecteur(tag):
    """'div.article__content' — la balise sous la forme d'un sélecteur CSS."""
    classes = ".".join(tag.get("class", []))
    return f"{tag.name}.{classes}" if classes else tag.name


print(f"=== {CHEMIN.name} — {len(soup.get_text(' ').split())} mots dans la page ===\n")

print("=== JSON-LD (nœud Article) ===")
article = noeud_json_ld(soup)
if not article:
    print("  AUCUN nœud Article — s'appuyer sur les <meta> et les balises.")
for cle, valeur in article.items():
    texte = re.sub(r"\s+", " ", str(valeur))
    if cle == "articleBody":
        print(f"  {cle:22} {len(texte.split())} mots : {texte[:120]!r}...")
    else:
        print(f"  {cle:22} {texte[:150]}")

print("\n=== META ===")
for tag in soup.find_all("meta"):
    nom = tag.get("property") or tag.get("name") or ""
    contenu = tag.get("content", "")
    if not nom or not contenu or META_BRUIT.match(nom):
        continue
    marque = "!" if META_ACCES.search(nom) else " "
    print(f" {marque} {nom:34} {contenu[:110]}")

print("\n=== CORPS : conteneurs les plus riches en <p> ===")
conteneurs = Counter()
classes_p = Counter()
for p in soup.find_all("p"):
    poids = len(p.get_text(" ").split())
    conteneurs[selecteur(p.parent)] += poids
    classes_p[selecteur(p)] += poids
for cible, mots in conteneurs.most_common(8):
    print(f"  {mots:>6} mots  {cible}")

print("\n=== CORPS : classes de <p> ===")
for cible, mots in classes_p.most_common(8):
    print(f"  {mots:>6} mots  {cible}")

print("\n=== TITRES (h1) ===")
for h1 in soup.find_all("h1"):
    print(f"  {selecteur(h1):50} {h1.get_text(strip=True)[:80]!r}")

if RECHERCHE:
    print(f"\n=== OÙ EST {RECHERCHE!r} ===")
    trouve = False
    for tag in soup.find_all(True):
        if tag.string and RECHERCHE in tag.string:
            trouve = True
            # Chemin complet depuis la racine : montre les conteneurs à cibler.
            parents = [selecteur(p) for p in reversed(list(tag.parents))
                       if p.name not in ("[document]", None)]
            print(" > ".join(parents + [selecteur(tag)]))
            print(f"   -> {tag.string.strip()[:80]!r}\n")
    if not trouve:
        print("  Introuvable dans une balise feuille (texte éclaté sur plusieurs enfants ?)")
