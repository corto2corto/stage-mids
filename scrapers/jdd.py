import requests
from bs4 import BeautifulSoup

response = requests.get("https://www.lejdd.fr/Societe/narcotrafic-lombre-des-dealers-plane-sur-les-mairies-173226")
soup = BeautifulSoup(response.text, "html.parser")

paragraphes = soup.find_all("p")

print(response.text[:2000])

# Protection par Cloudflare 
