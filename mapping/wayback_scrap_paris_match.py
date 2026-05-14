import requests, re
import time 
from xml.etree import ElementTree as ET

# On cherche tous les historiques de paris_match.com/sitemap
r = requests.get("http://web.archive.org/cdx/search/cdx?url=parismatch.com/sitemap/*&output=json&collapse=urlkey")
data = r.json()

# On conserve seulement ceux du type sitemap/année-moi.xml 
motif = re.compile(r"https://www.parismatch.com/sitemap/\d{4}-\d{2}\.xml$")

# La ligne [1] contient le timestamp, la [2] l'URL
res = [(lignes[1],lignes[2]) for lignes in data if motif.search(lignes[2])]

# Transformation en URLs Wayback directement utilisables
res = [f"https://web.archive.org/web/{timestamp}id_/{url}" for (timestamp, url) in res]

# Cette fois, on le fait sur les 3 premiers URLs utilisables
for page in res[:3]:
    # Maintenant, on récupère le XML disponible sur web.archive 
    xml = requests.get(page, timeout=30).content

    # Construction d'un arbre avec les balises 
    root = ET.fromstring(xml)

    # .// pour dire "récupère toutes les balises locs"
    articles_url = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")

    # Impression des URL
    for url in articles_url[:5]:
        print(url.text)



