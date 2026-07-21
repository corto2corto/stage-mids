"""Construction initiale des listes d'URLs d'articles (une par media, CSV).

- generique.py : le moteur — 5 methodes de collecte (IndexSitemap,
  SitemapPagine, PaginationHtml, ArchivesParJour, CdxWayback), sortie CSV
  en append+dedup (jamais d'ecrasement)
    python -m mapping.generique <media>
- catalogue.py : une fiche de config par media (23 medias)
- mapper_liens.py : agent pour les sites sans sitemap exploitable (a part)
- lancer.sh : enchainement serveur (tmux dedie)
    bash mapping/lancer.sh gala bfmtv cnews ...
- verifier.py : controles a sec (--sec, sans reseau) + smoke tests dans un
  dossier temporaire (les CSV de prod ne sont jamais touches)

Les CSV produits restent dans exploration/<media>_url.csv (donnees, hors git).
La mise a jour QUOTIDIENNE des CSV (sitemaps news) vit dans scripts/ :
sitemap_news, rattrapage_sitemaps, verser_nouveaux, collecte.
"""
