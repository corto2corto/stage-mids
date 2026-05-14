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

# Maintenant, on récupère le XML disponible sur web.archive 

xml = requests.get(res[0], timeout=30).content

root = ET.fromstring(xml)

articles = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")

for articles in articles[:5]:
    print(articles.text)



