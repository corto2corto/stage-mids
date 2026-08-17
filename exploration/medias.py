"""Catalogue des medias a mapper : une entree = un media, decrite par la
methode de collecte de ses URLs d'articles et ses particularites (motif,
options). La plomberie (requetes, ecriture CSV, checkpoints, MAPPING_LIMITE)
vit dans exploration.mapping ; ici, rien que la config.

Quatre methodes, selon la structure du site (reperee lors de la reco) :

- IndexSitemap : un index liste des sous-sitemaps mensuels/hebdo, chacun
  plein de <loc>. gzip=True si les sous-sitemaps sont gzippes ; via_curl=True
  si le CDN bloque python-requests (empreinte TLS) ; filtre = motif que les
  URLs doivent satisfaire pour etre gardees.
- SitemapPagine : un seul sitemap pagine par un parametre numerique
  (?page=1..N ou ?from=0..N pas de 100) ; chaque page est pleine de <loc>.
- PaginationHtml : des pages liste HTML (?page=N, une par jour, une par
  rubrique, une par jour listee dans une page annuelle...) d'ou on extrait
  les liens d'articles via motif.
- ArchivesCDX : le site est inaccessible au crawl (DataDome, rendu JS) ou son
  historique n'est plus expose ; on lit l'index des captures de la Wayback
  Machine, qui liste les URLs archivees sans toucher au site.
"""
from dataclasses import dataclass, field


# --- 1998..aujourd'hui : firefox recent, evite quelques 403 ---
UA_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
UA_AGENT = "Mozilla/5.0 (recherche academique, mapping-agent)"


@dataclass
class IndexSitemap:
    """Index -> sous-sitemaps -> <loc>. `index` peut etre une liste (L'Express
    en a deux). `motif_sous_sitemap` extrait les sous-sitemaps de l'index ;
    `filtre` (optionnel) restreint les URLs finales gardees."""
    index: str | list[str]
    motif_sous_sitemap: str
    gzip: bool = False
    via_curl: bool = False
    filtre: str | None = None
    anti_filtre: str | None = None  # motif que les URLs gardees ne doivent PAS contenir
    unescape: bool = False  # html.unescape avant extraction (entites &amp; dans l'index)
    ua: str = UA_AGENT


@dataclass
class SitemapPagine:
    """Un sitemap pagine par un parametre numerique. La plage vient soit de
    `pages` (liste explicite : liberation), soit lue dans le sitemap via
    `motif_pages` (francesoir). `arret_pages_vides` arrete apres N pages
    consecutives sans <loc> quand la plage est un garde-fou large (cnews) ;
    `pause` surcharge la politesse par defaut (cnews : Crawl-delay 10 s)."""
    base: str
    param: str                       # nom du parametre de pagination (page, from)
    motif_pages: str | None = None   # lit le nb de pages dans le sitemap
    pages: list[int] | None = None   # ou plage explicite
    params_fixes: dict = field(default_factory=dict)  # ex outputType=xml
    filtre: str | None = None
    anti_filtre: str | None = None
    unescape: bool = False
    arret_pages_vides: int = 0       # arret auto apres N pages vides (0 = jamais)
    pause: float = 0.5               # politesse envers le serveur
    ua: str = UA_AGENT


@dataclass
class PaginationHtml:
    """Pages liste HTML d'ou on extrait des liens d'articles. `sections` :
    dict {section: nb_pages} pour un nb de pages connu (mediapart), liste de
    sections avec arret auto sur `max_pages` sans nouveaute (marianne), ou None
    pour une pagination unique (blast). `dates` : archives par jour (leparisien).
    `prefixe` est prepende aux liens relatifs captures.

    Variantes de pagination des rubriques : `sections_sitemap` lit la liste des
    rubriques dans un sitemap au lieu de la coder en dur (laprovence), et
    `gabarit_page` remplace le parametre ?page=N par un segment d'URL
    (laprovence : /page-N ; la page 1 est l'URL nue).

    Archives annuelles (20minutes, leprogres) : `annees` + `url_annee` listent
    les pages-jour via `motif_annee`, chaque page-jour etant ensuite lue avec
    `motif`. `filtre_jour=True` ne garde que les articles dont le slug porte la
    date de la page (20minutes : les pages melangent des encarts "plus lus")."""
    motif: str
    base: str | None = None
    param: str = "page"
    total_pages: int | None = None            # pagination unique (blast)
    sections: dict | list | None = None       # rubriques (mediapart, marianne)
    sections_sitemap: str | None = None       # sitemap listant les rubriques (laprovence)
    motif_sections: str | None = None         # extrait les rubriques de ce sitemap
    gabarit_page: str | None = None           # ex "/page-{page}" au lieu de ?page=N
    max_pages: int = 600                       # garde-fou / arret auto
    date_debut: tuple | None = None            # (annee, mois, jour) -> archives par jour
    url_jour: str | None = None                # gabarit avec {annee} {jjmmaaaa}
    motif_jour: str | None = None              # variante du motif pour un jour
    annees: tuple | None = None                # (debut, fin) -> archives par annee
    url_annee: str | None = None               # gabarit avec {annee}
    motif_annee: str | None = None             # extrait les pages-jour de la page annuelle
    ordre_jour: str = "mj"                     # "mj" = /MM-DD (20minutes), "jm" = /JJ-MM (leprogres)
    filtre_jour: bool = False                  # ne garder que les articles dates du jour
    pause: float = 1.0                         # politesse (surcharge PAUSE)
    prefixe: str = ""
    ua: str = UA_AGENT


@dataclass
class ArchivesCDX:
    """Index des captures de la Wayback Machine (API CDX). `domaine` est
    interroge en matchType=host ; `motif_article` filtre les URLs gardees
    (les captures contiennent tout : pages de rubrique, assets...).
    `periode` restreint la fenetre ({"from": "2010"} ou {"to": "2025"}).
    `fusionner=True` : le CSV existant est charge et complete au lieu d'etre
    ecrase -- pour les mappings d'archives qui completent un mapping sitemap
    deja fait (liberation, laprovence)."""
    domaine: str
    motif_article: str
    periode: dict = field(default_factory=dict)
    fusionner: bool = False
    sortie: str | None = None   # CSV cible si different de <media>_url.csv
    ua: str = UA_AGENT


CATALOGUE = {
    # === IndexSitemap ===
    "gala": IndexSitemap(
        index="https://www.gala.fr/sitemaps/articles.xml",
        motif_sous_sitemap=r"<loc>(https://www\.gala\.fr/sitemaps/articles/\d{4}-\d{2}\.xml)</loc>",
    ),
    "la_croix": IndexSitemap(
        index="https://www.la-croix.com/feeds/sitemaps/sitemaps_articles.xml",
        motif_sous_sitemap=r"<loc>(https://www\.la-croix\.com/feeds/sitemaps/articles/\d{4}-\d{2}\.xml)</loc>",
    ),
    "voici": IndexSitemap(
        index="https://www.voici.fr/sitemap/articles.xml",
        motif_sous_sitemap=r"<loc>(https://www\.voici\.fr/sitemap/articles/page-\d+\.xml)</loc>",
    ),
    "bfmtv": IndexSitemap(
        index="https://www.bfmtv.com/sitemap_index_arbo_contenu.xml",
        motif_sous_sitemap=r"<loc>(https://www\.bfmtv\.com/sitemaps/rubriquesContenus/\d{4}-\d{2}-\d\.xml\.gz)</loc>",
        gzip=True,
    ),
    "midilibre": IndexSitemap(
        index="https://www.midilibre.fr/sitemap.xml",
        motif_sous_sitemap=r"<loc>(https://www\.midilibre\.fr/sitemap/sitemap-\d{4}-\d{2}_\d+\.xml\.gz)</loc>",
        gzip=True,
    ),
    "lexpress": IndexSitemap(
        index=[
            "https://www.lexpress.fr/arc/outboundfeeds/sitemap-by-week-2010-2020.xml",
            "https://www.lexpress.fr/arc/outboundfeeds/sitemap-by-week-2020-now.xml",
        ],
        motif_sous_sitemap=r"<loc>(https://www\.lexpress\.fr/arc/outboundfeeds/sitemap-all/weeks/[0-9-]+/\?outputType=xml)</loc>",
        anti_filtre=r"/arc/outboundfeeds/",
        unescape=True,
    ),
    # paris_normandie : reco du 07/07/2026 — Akamai bloque desormais UA_FIREFOX
    # (403 sur l'index et la news) et laisse passer l'UA academique.
    "paris_normandie": IndexSitemap(
        index="https://www.paris-normandie.fr/sites/default/files/sitemaps/www_paris_normandie_fr/sitemapindex.xml",
        motif_sous_sitemap=r"<loc>([^<]+\.xml)</loc>",
        via_curl=True,
        filtre=r"/article/",
    ),

    # closermag : index Yoast WordPress ; parmi les 8 types de fichiers
    # references (post/page/category/author...), seuls les post-sitemap*.xml
    # contiennent des articles (~1000 URLs chacun, ~220 fichiers).
    # Le <lastmod> est trompeur (reindexation massive de mai 2023 sur tout
    # l'historique) : ne pas s'y fier pour dater, seul le datePublished
    # json-ld dans la page fait foi.
    "closermag": IndexSitemap(
        index="https://www.closermag.fr/sitemap_index.xml",
        motif_sous_sitemap=r"<loc>(https://www\.closermag\.fr/post-sitemap\d*\.xml)</loc>",
    ),

    # === SitemapPagine ===
    # cnews : ~215 pages de sitemap, ~2000 URLs chacune, dont ~45 % d'articles
    # textuels. On garde /{rubrique}/{YYYY-MM-DD}/{slug}, en excluant videos,
    # podcast, emission et diaporamas. Au debut de l'archive (2012-02-17) une
    # dizaine d'articles n'ont pas de segment rubrique : elle est optionnelle.
    # robots.txt impose un Crawl-delay de 10 s -> ~36 min pour les 215 pages.
    "cnews": SitemapPagine(
        base="https://www.cnews.fr/sitemap.xml",
        param="page",
        pages=list(range(1, 301)),  # garde-fou : 215 pages recensees lors de la reco
        filtre=r"^https://www\.cnews\.fr/(?:(?!videos/|podcast/|emission/|diaporamas/)[^/]+/)?\d{4}-\d{2}-\d{2}/[^/]+/?$",
        pause=10.0,
        arret_pages_vides=2,
    ),
    "francesoir": SitemapPagine(
        base="https://www.francesoir.fr/sitemap.xml",
        param="page",
        motif_pages=r"sitemap\.xml\?page=(\d+)",
        filtre=r"^https://www\.francesoir\.fr/[a-z0-9_-]+/[^/<\s]+$",
    ),
    "liberation": SitemapPagine(
        base="https://www.liberation.fr/arc/outboundfeeds/sitemap/",
        param="from",
        pages=list(range(0, 10000, 100)),
        params_fixes={"outputType": "xml"},
        filtre=r"liberation\.fr",
        anti_filtre=r"/arc/outboundfeeds/",
        unescape=True,
    ),

    # === PaginationHtml ===
    "blast": PaginationHtml(
        base="https://www.blast-info.fr/articles",
        motif=r'href="(/articles/\d{4}/[^"]+)"',
        total_pages=320,
        prefixe="https://www.blast-info.fr",
    ),
    "marianne": PaginationHtml(
        base="https://www.marianne.net/{section}",
        param="p",
        # {section} est injecte dans le motif pour ne garder que les articles de la rubrique
        motif=r'href="(https://www\.marianne\.net/{section}(?:/[a-z0-9-]+)?/[a-z0-9-]{{25,}})"',
        sections=["politique", "societe", "economie", "monde", "culture", "art-de-vivre", "agora"],
        max_pages=600,
        ua=UA_FIREFOX,
    ),
    "mediapart": PaginationHtml(
        base="https://www.mediapart.fr/journal/{section}",
        motif=r'href="(/journal/[a-z-]+/\d{6}/[a-z0-9-]+)"',
        sections={
            "international": 625, "france": 625, "politique": 356, "economie": 580,
            "ecologie": 224, "culture-idees": 457, "enquetes": 472, "series": 40,
            "fil-dactualites": 1000,
        },
        prefixe="https://www.mediapart.fr",
    ),
    "leparisien": PaginationHtml(
        motif=r'href="(?:https:)?//www\.leparisien\.fr(/[^"]*-\d{2}-\d{2}-\d{4}-[A-Z0-9]+\.php)"',
        date_debut=(2010, 1, 1),
        url_jour="https://www.leparisien.fr/archives/{annee}/{jjmmaaaa}/",
        prefixe="https://www.leparisien.fr",
        ua=UA_FIREFOX,
    ),
    # laprovence : rubriques listees dans sitemap_categories.xml, paginees par
    # /page-N (repere lors de la reco : ?page= et /page/N sont ignores, seul
    # /page-N pagine vraiment ; ~48 liens /article/ par page). Le sitemap liste
    # aussi des rubriques disparues (404 systematique) -> arret sur 3 echecs.
    # Ne donne que le recent (~5-7 pages par rubrique) : l'historique vient de
    # laprovence_archives ci-dessous.
    "laprovence": PaginationHtml(
        base="https://www.laprovence.com{section}",
        motif=r'href="(?:https://www\.laprovence\.com)?(/article/[^"#?]+)"',
        sections_sitemap="https://www.laprovence.com/sitemap_categories.xml",
        motif_sections=r"<loc>https://www\.laprovence\.com(/[a-z0-9-]+)</loc>",
        gabarit_page="/page-{page}",
        max_pages=3000,  # france-monde annonce ~84k articles soit ~2100 pages
        prefixe="https://www.laprovence.com",
        pause=0.4,
        ua=UA_FIREFOX,
    ),
    # 20minutes : pages d'archives datees /archives/YYYY/MM-DD (liens HTML
    # bruts, sans JS ni pagination). Chaque page annuelle liste les 365/366
    # jours. Les pages-jour melangent les articles du jour avec des encarts
    # "plus lus" d'autres dates -> filtre_jour ne garde que les slugs portant
    # la date de la page. ~7 400 pages-jour de 2006 a 2026, ~3 h de crawl.
    "20minutes": PaginationHtml(
        motif=r'href="(https://www\.20minutes\.fr/[a-z0-9\-/]+/\d+-(\d{8})-[a-z0-9\-]+)"',
        annees=(2006, 2026),
        url_annee="https://www.20minutes.fr/archives/{annee}",
        motif_annee=r'href="https://www\.20minutes\.fr/archives/(\d{4})/(\d{2})-(\d{2})"',
        url_jour="https://www.20minutes.fr/archives/{annee}/{mm}-{jj}",
        filtre_jour=True,
    ),
    # leprogres : meme principe, mais les pages-jour sont en /archives/YYYY/JJ-MM
    # (jour-mois, verifie par smoke-test) alors que les URLs d'articles sont en
    # /rubrique/YYYY/MM/DD/slug. Pas de filtre par date : une page-jour melange
    # occasionnellement des articles de la veille, mais la deduplication est
    # globale -- ni doublon ni erreur. Avant 2018 : rien (410).
    "leprogres": PaginationHtml(
        motif=r'href="(?:https://www\.leprogres\.fr)?(/[^/"]+/\d{4}/\d{2}/\d{2}/[^"]+)"',
        annees=(2018, 2026),
        url_annee="https://www.leprogres.fr/archives/{annee}",
        motif_annee=r'href="(?:https://www\.leprogres\.fr)?/archives/(\d{4})/(\d{2})-(\d{2})"',
        url_jour="https://www.leprogres.fr/archives/{annee}/{jj}-{mm}",
        ordre_jour="jm",
        prefixe="https://www.leprogres.fr",
        pause=1.5,
    ),

    # === ArchivesCDX ===
    # lepoint : DataDome bloque robots.txt, /archives/ et les rubriques meme en
    # Firefox headless (interstitiel), et le site n'expose aucun sitemap.
    # Fenetre from=2010 (temoin long). Article : ...-JJ-MM-AAAA-ID_NN.php
    "lepoint": ArchivesCDX(
        domaine="www.lepoint.fr",
        motif_article=r"^https://www\.lepoint\.fr/.+-\d{2}-\d{2}-\d{4}-\d+_\d+\.php$",
        periode={"from": "2010"},
    ),
    # latribune : site refondu (Next.js) rendu cote client, page-N repond "Page
    # non trouvee", aucun endpoint API identifiable, >60 s en Selenium. Fenetre
    # from=2018 (rachat CMA CGM en 2023, +/- large). Deux formats : ancien
    # slug-ID.html et nouveau /article/...
    "latribune": ArchivesCDX(
        domaine="www.latribune.fr",
        motif_article=r"^https://www\.latribune\.fr/(?:.+-\d{6,}\.html|article/.+)$",
        periode={"from": "2018"},
    ),
    # liberation_archives : complete liberation_url.csv (limite aux ~10k articles
    # recents du sitemap Arc). Les pages /archives/ refusent curl/requests (403
    # sans meme poser de cookie DataDome) et depassent 60 s en Selenium. Fenetre
    # to=2025 (la suite est couverte par le sitemap). A lancer APRES liberation.
    "liberation_archives": ArchivesCDX(
        domaine="www.liberation.fr",
        motif_article=r"^https://www\.liberation\.fr/(?:.+/\d{4}/\d{2}/\d{2}/[^/]+_\d+/?|[^?]+-\d{8}_[A-Z0-9]+/?)$",
        periode={"to": "2025"},
        fusionner=True,
        sortie="exploration/liberation_url.csv",
    ),
    # laprovence_archives : complete laprovence_url.csv (~12k URLs recentes).
    # Deux formats au fil des refontes : /article/<rubrique>/<id>/<slug> (ancien
    # avec .html, nouveau sans) et /actu/en-direct/<id>/<slug>.html (anciennes
    # breves). Le wrapper moderne /actu/en-direct/<id>/article/... est exclu
    # (doublon du canonique /article/...). A lancer APRES laprovence.
    "laprovence_archives": ArchivesCDX(
        domaine="www.laprovence.com",
        motif_article=r"^https://www\.laprovence\.com/(?:article/.+|actu/en-direct/\d+/[^/]+\.html)$",
        fusionner=True,
        sortie="exploration/laprovence_url.csv",
    ),
}
