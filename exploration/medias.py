"""Catalogue des medias a mapper : une entree = un media, decrite par la
methode de collecte de ses URLs d'articles et ses particularites (motif,
options). La plomberie (requetes, ecriture CSV, checkpoints, MAPPING_LIMITE)
vit dans exploration.mapping ; ici, rien que la config.

Trois methodes, selon la structure du site (reperee lors de la reco) :

- IndexSitemap : un index liste des sous-sitemaps mensuels/hebdo, chacun
  plein de <loc>. gzip=True si les sous-sitemaps sont gzippes ; via_curl=True
  si le CDN bloque python-requests (empreinte TLS) ; filtre = motif que les
  URLs doivent satisfaire pour etre gardees.
- SitemapPagine : un seul sitemap pagine par un parametre numerique
  (?page=1..N ou ?from=0..N pas de 100) ; chaque page est pleine de <loc>.
- PaginationHtml : des pages liste HTML (?page=N, une par jour, une par
  rubrique...) d'ou on extrait les liens d'articles via motif.
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
    `motif_pages` (francesoir)."""
    base: str
    param: str                       # nom du parametre de pagination (page, from)
    motif_pages: str | None = None   # lit le nb de pages dans le sitemap
    pages: list[int] | None = None   # ou plage explicite
    params_fixes: dict = field(default_factory=dict)  # ex outputType=xml
    filtre: str | None = None
    anti_filtre: str | None = None
    unescape: bool = False
    ua: str = UA_AGENT


@dataclass
class PaginationHtml:
    """Pages liste HTML d'ou on extrait des liens d'articles. `sections` :
    dict {section: nb_pages} pour un nb de pages connu (mediapart), liste de
    sections avec arret auto sur `max_pages` sans nouveaute (marianne), ou None
    pour une pagination unique (blast). `dates` : archives par jour (leparisien).
    `prefixe` est prepende aux liens relatifs captures."""
    motif: str
    base: str | None = None
    param: str = "page"
    total_pages: int | None = None            # pagination unique (blast)
    sections: dict | list | None = None       # rubriques (mediapart, marianne)
    max_pages: int = 600                       # garde-fou / arret auto
    date_debut: tuple | None = None            # (annee, mois, jour) -> archives par jour
    url_jour: str | None = None                # gabarit avec {annee} {jjmmaaaa}
    motif_jour: str | None = None              # variante du motif pour un jour
    prefixe: str = ""
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
    "paris_normandie": IndexSitemap(
        index="https://www.paris-normandie.fr/sites/default/files/sitemaps/www_paris_normandie_fr/sitemapindex.xml",
        motif_sous_sitemap=r"<loc>([^<]+\.xml)</loc>",
        via_curl=True,
        filtre=r"/article/",
        ua=UA_FIREFOX,
    ),

    # === SitemapPagine ===
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
}
