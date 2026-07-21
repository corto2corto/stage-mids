"""Construction initiale des listes d'URLs d'articles (une par media, CSV).

- generique.py : moteur des cas standard, pilote par les fiches de catalogue.py
    python -m mapping.generique <media>
- <media>.py : scripts dedies aux sites irreductibles (CDX Wayback, Selenium,
  archives par jour, pagination par rubrique)
    python -m mapping.cnews, mapping.ouest_france, ...
- mapper_liens.py : agent pour les sites sans sitemap exploitable
- lancer.sh / lancer_speciaux.sh : enchainements serveur (tmux dedie)
- verifier.py / verifier_speciaux.py : smoke tests des mappings

Les CSV produits restent dans exploration/<media>_url.csv (donnees, hors git).
La mise a jour QUOTIDIENNE des CSV (sitemaps news) vit dans scripts/ :
sitemap_news, rattrapage_sitemaps, verser_nouveaux, collecte.
"""
