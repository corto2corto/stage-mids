"""Explore la base Algolia des articles du groupe Ouest-France : 39 M
d'enregistrements, 1990-2026, 8 titres (Ouest-France, Courrier de l'Ouest,
Presse Ocean, Le Maine Libre, Le Marin, Agence API, Voiles et Voiliers, fl).

Le texte integral des articles est dans le champ "texte", mais seulement sur
l'index articles_bydate_desc : l'index articles ne le renvoie jamais, meme
avec attributesToRetrieve ["*"]. Il est servi y compris pour les articles
payants, donc sans scraping ni contournement de paywall. Les enregistrements
papier (print=1) ont un texte vide : filtrer print=0.

Deux limites a connaitre :
- une requete ne rend jamais plus de 1000 resultats (browse est refuse), donc
  pour extraire un corpus il faut decouper : jour, puis source, puis zone geo,
  jusqu'a passer sous 1000 ;
- nbHits est approximatif sur les gros volumes (exhaustiveNbHits=False) et
  exact sur les petits ; les comptes par facette, eux, sont toujours exacts.

La cle API tourne toutes les 24 h. La relever dans les outils reseau du
navigateur sur ouest-france.fr (en-tete x-algolia-api-key d'une requete
"queries" vers *-dsn.algolia.net), puis :
    export OF_ALGOLIA_KEY="..."
    python -m exploration.sonder_algolia_of
"""
import json
import os
import urllib.request

APP_ID = "C8KP7JV01T"
CLE = os.environ["OF_ALGOLIA_KEY"]


def interroger(corps, index="articles"):
    """Une requete Algolia. Le Referer est obligatoire, sinon la cle est refusee."""
    requete = urllib.request.Request(
        f"https://{APP_ID}-dsn.algolia.net/1/indexes/{index}/query",
        data=json.dumps(corps).encode(),
        headers={
            "X-Algolia-Application-Id": APP_ID,
            "X-Algolia-API-Key": CLE,
            "Referer": "https://www.ouest-france.fr/",
            "Content-Type": "application/json",
        },
    )
    return json.loads(urllib.request.urlopen(requete, timeout=15).read())


# Ce qu'on peut filtrer : Algolia liste ses facettes avec "*"
reponse = interroger({"query": "", "hitsPerPage": 0, "facets": ["*"], "maxValuesPerFacet": 1})
print("Attributs filtrables :", ", ".join(sorted(reponse.get("facets") or {})))
print("Total de l'index     :", reponse["nbHits"])
print()

# Volume par annee et par titre (comptes exacts : ce sont des facettes)
reponse = interroger({"query": "", "hitsPerPage": 0,
                      "facets": ["anneePublication", "source"], "maxValuesPerFacet": 200})
annees = reponse["facets"]["anneePublication"]
print("Articles par annee :")
for annee in sorted(annees, key=int):
    print(f"  {annee} : {annees[annee]:>9}")
print()
print("Articles par titre :")
for titre, nombre in sorted(reponse["facets"]["source"].items(), key=lambda x: -x[1]):
    print(f"  {titre:>4} : {nombre:>9}")
print()

# Une recherche par mot-cle, comme la barre de recherche du site
reponse = interroger({"query": "rachat", "hitsPerPage": 3,
                      "filters": "anneePublication=2024 AND source:of"})
print(f"Recherche 'rachat' en 2024 dans Ouest-France ({reponse['nbHits']} resultats) :")
for article in reponse["hits"]:
    print(f"  [{article['jourPublication']}/{article['moisPublication']}] "
          f"payant={article.get('payant')} {article['titre'][:70]}")
    print(f"    {article['url'][:100]}")
print()

# Decoupage pour extraire un corpus : une journee tient-elle sous le plafond ?
filtre = "anneePublication=2026 AND moisPublication=8 AND jourPublication=5"
reponse = interroger({"query": "", "hitsPerPage": 0, "filters": filtre})
print(f"Journee du 05/08/2026 : {reponse['nbHits']} articles "
      f"(exact : {reponse.get('exhaustiveNbHits')})")
for titre in ["of", "co", "po", "ml"]:
    reponse = interroger({"query": "", "hitsPerPage": 0, "filters": f"{filtre} AND source:{titre}"})
    plafond = "" if reponse["nbHits"] <= 1000 else "  <-- depasse 1000, redecouper par zonesGeo"
    print(f"  source:{titre:<4} : {reponse['nbHits']:>6}{plafond}")
print()

# Le texte integral : present sur articles_bydate_desc, absent sur articles
for index in ["articles", "articles_bydate_desc"]:
    article = interroger({"query": "", "hitsPerPage": 1, "filters": "payant=1 AND print=0",
                          "attributesToRetrieve": ["*"]}, index=index)["hits"][0]
    texte = article.get("texte")
    mots = len(texte.split()) if isinstance(texte, str) else 0
    print(f"{index:22} article payant -> texte : {mots} mots")
