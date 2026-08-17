"""Catalogue des medias a mapper : une entree = un media, decrite par la
methode de collecte de ses URLs d'articles et ses particularites (motif,
options). La plomberie (requetes, ecriture CSV append+dedup, MAPPING_LIMITE)
vit dans mapping.generique ; ici, rien que la config.

Cinq methodes, selon la structure du site (reperee lors de la reco) :

- IndexSitemap : un index liste des sous-sitemaps mensuels/hebdo, chacun
  plein de <loc>. via_curl=True si le CDN bloque python-requests (empreinte
  TLS) ; via_cffi=True si l'anti-bot exige une vraie empreinte Chrome
  (curl_cffi) ; via_firefox=True si le site ne sert les sitemaps qu'a un
  vrai navigateur (DataDome ouest_france) ; filtre = motif que les URLs
  doivent satisfaire pour etre gardees.
- SitemapPagine : un seul sitemap pagine par un parametre numerique. La
  plage vient de `pages` (liste explicite), de `motif_pages` (lue dans le
  sitemap), ou de `max_pages` avec arret automatique apres `arret_apres`
  pages vides/echecs consecutifs (cnews).
- PaginationHtml : des pages liste HTML (?page=N, une par jour, une par
  rubrique...) d'ou on extrait les liens d'articles via motif. Rubriques
  fixes (`sections`) ou lues dans un sitemap (`sections_depuis`) ;
  pagination par parametre (`param`) ou par route (`route_page`, laprovence).
- ArchivesParJour : une page d'archives par jour, listees par une page
  annuelle (20minutes, leprogres). filtre_date_slug ne garde que les liens
  dont la date du slug est celle du jour de la page (encarts "plus lus").
- CdxWayback : l'API CDX de la Wayback Machine liste les captures archivees
  sans toucher au site (DataDome/Next.js infranchissables : lepoint,
  latribune, archives liberation/laprovence). `sortie` fusionne dans le CSV
  d'un autre mapping (append+dedup : union naturelle).
"""
from dataclasses import dataclass, field


# --- 1998..aujourd'hui : firefox recent, evite quelques 403 ---
UA_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
UA_AGENT = "Mozilla/5.0 (recherche academique, mapping-agent)"


@dataclass
class IndexSitemap:
    """Index -> sous-sitemaps -> <loc>. `index` peut etre une liste (L'Express
    en a deux). `motif_sous_sitemap` extrait les sous-sitemaps de l'index
    (prefixe_sous_sitemap prepende si le motif capture un chemin nu) ;
    `filtre` (optionnel) restreint les URLs finales gardees."""
    index: str | list[str]
    motif_sous_sitemap: str
    prefixe_sous_sitemap: str = ""
    via_curl: bool = False
    via_cffi: bool = False
    via_firefox: bool = False
    filtre: str | None = None
    anti_filtre: str | None = None  # motif que les URLs gardees ne doivent PAS contenir
    unescape: bool = False  # html.unescape avant extraction (entites &amp; dans l'index)
    nettoyer: bool = False  # strip ?query et #fragment des URLs collectees
    pause: float = 0.5
    ua: str = UA_AGENT


@dataclass
class SitemapPagine:
    """Un sitemap pagine par un parametre numerique. La plage vient soit de
    `pages` (liste explicite : liberation), soit lue dans le sitemap via
    `motif_pages` (francesoir), soit de `max_pages` avec arret automatique
    apres `arret_apres` pages vides/echecs consecutifs (cnews)."""
    base: str
    param: str                       # nom du parametre de pagination (page, from)
    motif_pages: str | None = None   # lit le nb de pages dans le sitemap
    pages: list[int] | None = None   # ou plage explicite
    max_pages: int | None = None     # ou 1..N avec arret auto (cnews)
    arret_apres: int = 2             # pages vides/echecs consecutifs avant arret
    params_fixes: dict = field(default_factory=dict)  # ex outputType=xml
    via_cffi: bool = False
    filtre: str | None = None
    anti_filtre: str | None = None
    unescape: bool = False
    nettoyer: bool = False
    pause: float = 0.5
    ua: str = UA_AGENT


@dataclass
class PaginationHtml:
    """Pages liste HTML d'ou on extrait des liens d'articles. `sections` :
    dict {section: nb_pages} pour un nb de pages connu (mediapart), liste de
    sections avec arret auto apres 2 pages sans nouveaute (marianne), ou None
    pour une pagination unique (blast) ; `sections_depuis` + `motif_sections`
    lisent la liste dans un sitemap (laprovence). Pagination par parametre
    (`param`) ou par route (`route_page`, ex "/page-{page}", page 1 = base
    nue). `date_debut` : archives par jour (leparisien). `prefixe` est
    prepende aux liens relatifs captures."""
    motif: str
    base: str | None = None
    param: str = "page"
    route_page: str | None = None              # pagination par route (laprovence)
    total_pages: int | None = None             # pagination unique (blast)
    sections: dict | list | None = None        # rubriques (mediapart, marianne)
    sections_depuis: str | None = None         # URL d'un sitemap listant les rubriques
    motif_sections: str | None = None          # regex des chemins de rubrique
    max_pages: int = 600                       # garde-fou / arret auto
    arret_echecs: int = 3                      # echecs consecutifs -> rubrique morte
    date_debut: tuple | None = None            # (annee, mois, jour) -> archives par jour
    url_jour: str | None = None                # gabarit avec {annee} {jjmmaaaa}
    prefixe: str = ""
    pause: float = 0.5
    ua: str = UA_AGENT


@dataclass
class ArchivesParJour:
    """Une page d'archives par jour, listees par une page annuelle. motif_jour
    capture (annee, g2, g3) tels qu'ils apparaissent dans l'URL du jour —
    (mois, jour) pour 20minutes, (jour, mois) pour leprogres — et url_jour les
    replace tels quels. filtre_date_slug : le motif_article a 2 groupes
    (url, date compacte AAAAMMJJ) et seuls les liens dates du jour de la page
    sont gardes (20minutes : encarts "plus lus" d'autres dates)."""
    url_annee: str          # gabarit avec {annee}
    motif_jour: str         # regex -> (annee, g2, g3)
    url_jour: str           # gabarit avec {annee} {g2} {g3}
    motif_article: str
    annee_debut: int        # profondeur d'archive ; fin = annee courante
    filtre_date_slug: bool = False
    prefixe: str = ""       # prepende aux chemins relatifs captures
    via_cffi: bool = True   # les archives datees passent par l'empreinte Chrome
    pause: float = 1.0
    ua: str = UA_FIREFOX


@dataclass
class CdxWayback:
    """API CDX de la Wayback Machine : liste les captures archivees du domaine
    sans toucher au site. `periode` borne la fenetre ({"from": "2010"},
    {"to": "2025"}) ; `sortie` ecrit dans le CSV d'un autre mapping
    (liberation_archives -> liberation_url.csv, union par append+dedup)."""
    domaine: str
    motif_article: str
    periode: dict = field(default_factory=dict)
    sortie: str | None = None
    pause: float = 1.0
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
    # bfmtv, midilibre : sous-sitemaps .xml.gz — decompresses automatiquement
    # par la plomberie (magic bytes), y compris si le serveur les sert deja nus.
    "bfmtv": IndexSitemap(
        index="https://www.bfmtv.com/sitemap_index_arbo_contenu.xml",
        motif_sous_sitemap=r"<loc>(https://www\.bfmtv\.com/sitemaps/rubriquesContenus/\d{4}-\d{2}-\d\.xml\.gz)</loc>",
    ),
    "midilibre": IndexSitemap(
        index="https://www.midilibre.fr/sitemap.xml",
        motif_sous_sitemap=r"<loc>(https://www\.midilibre\.fr/sitemap/sitemap-\d{4}-\d{2}_\d+\.xml\.gz)</loc>",
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
    # closermag : index Yoast WordPress, seuls les post-sitemap*.xml contiennent
    # des articles (~1000 URLs chacun). ATTENTION : le <lastmod> est trompeur
    # (reindexation massive de mai 2023), seul le datePublished json-ld date.
    "closermag": IndexSitemap(
        index="https://www.closermag.fr/sitemap_index.xml",
        motif_sous_sitemap=r"<loc>(https://www\.closermag\.fr/post-sitemap\d*\.xml)</loc>",
        via_cffi=True,
        pause=1.5,
    ),
    # ouest_france : DataDome ne sert les ~179 sitemaps articles qu'a un vrai
    # navigateur (curl et requests recoivent la home) -> Firefox headless.
    # Liseuse "leditiondusoir" (reader.html?t=...#!...) exclue apres nettoyage.
    "ouest_france": IndexSitemap(
        index="https://www.ouest-france.fr/sitemap.xml",
        motif_sous_sitemap=r"sitemap-articles-ouest-france-\d+\.xml",
        prefixe_sous_sitemap="https://www.ouest-france.fr/",
        via_firefox=True,
        nettoyer=True,
        filtre=r"^https://www\.ouest-france\.fr/",
        anti_filtre=r"\.xml$|/leditiondusoir/",
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
    # cnews : sitemap pagine ?page=1..~215 (~2000 URLs/page). Crawl-delay 10 s
    # impose par robots.txt. Rattrapage : re-balayage complet obligatoire, le
    # sitemap n'est pas trie par date.
    "cnews": SitemapPagine(
        base="https://www.cnews.fr/sitemap.xml",
        param="page",
        max_pages=300,  # garde-fou : 215 pages recensees lors de la reco
        via_cffi=True,
        pause=10,
        filtre=r"^https://www\.cnews\.fr/(?:(?!videos/|podcast/|emission/|diaporamas/)[^/]+/)?\d{4}-\d{2}-\d{2}/[^/]+/?$",
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
    # laprovence : rubriques listees dans sitemap_categories.xml, routes /page-N
    # rendues cote serveur (?page= et /page/N ignores). La pagination ne sert
    # que ~5-7 pages par rubrique avant de re-servir la page 1 : l'historique
    # vient de laprovence_archives (CDX), meme CSV.
    "laprovence": PaginationHtml(
        base="https://www.laprovence.com{section}",
        sections_depuis="https://www.laprovence.com/sitemap_categories.xml",
        motif_sections=r"<loc>https://www\.laprovence\.com(/[a-z0-9-]+)</loc>",
        route_page="/page-{page}",
        motif=r'href="(?:https://www\.laprovence\.com)?(/article/[^"#?]+)"',
        prefixe="https://www.laprovence.com",
        max_pages=3000,  # garde-fou (france-monde ~2100 pages annoncees)
        pause=0.4,
        ua=UA_FIREFOX,
    ),

    # === ArchivesParJour ===
    # 20minutes : archives datees /archives/YYYY/MM-DD (liens bruts, sans JS).
    # Chaque page-jour melange des encarts "plus lus" d'autres dates -> filtre
    # par la date -YYYYMMDD- du slug.
    "20minutes": ArchivesParJour(
        url_annee="https://www.20minutes.fr/archives/{annee}",
        motif_jour=r'href="https://www\.20minutes\.fr/archives/(\d{4})/(\d{2})-(\d{2})"',
        url_jour="https://www.20minutes.fr/archives/{annee}/{g2}-{g3}",
        motif_article=r'href="(https://www\.20minutes\.fr/[a-z0-9\-/]+/\d+-(\d{8})-[a-z0-9\-]+)"',
        annee_debut=2006,
        filtre_date_slug=True,
    ),
    # leprogres : archives /archives/YYYY/JJ-MM (ATTENTION jour-mois) ; liens
    # articles relatifs /<rubrique>/YYYY/MM/DD/<slug>. Avant 2018 : rien (410).
    "leprogres": ArchivesParJour(
        url_annee="https://www.leprogres.fr/archives/{annee}",
        motif_jour=r'href="(?:https://www\.leprogres\.fr)?/archives/(\d{4})/(\d{2})-(\d{2})"',
        url_jour="https://www.leprogres.fr/archives/{annee}/{g2}-{g3}",
        motif_article=r'href="(?:https://www\.leprogres\.fr)?(/[^/"]+/\d{4}/\d{2}/\d{2}/[^"]+)"',
        annee_debut=2018,
        prefixe="https://www.leprogres.fr",
        pause=1.5,
    ),

    # === CdxWayback ===
    # lepoint : DataDome bloque tout (meme Firefox headless), aucun sitemap.
    # Fenetre from=2010 (temoin long).
    "lepoint": CdxWayback(
        domaine="www.lepoint.fr",
        motif_article=r"^https://www\.lepoint\.fr/.+-\d{2}-\d{2}-\d{4}-\d+_\d+\.php$",
        periode={"from": "2010"},
    ),
    # latribune : refonte Next.js, listings rendus cote client uniquement.
    # Fenetre from=2018 (rachat CMA CGM en 2023, +/- large). Deux formats.
    "latribune": CdxWayback(
        domaine="www.latribune.fr",
        motif_article=r"^https://www\.latribune\.fr/(?:.+-\d{6,}\.html|article/.+)$",
        periode={"from": "2018"},
    ),
    # liberation_archives : complete liberation_url.csv (le sitemap Arc ne
    # couvre que ~10k articles recents). Fenetre to=2025 (la suite est couverte
    # par le sitemap). Deux formats d'articles au fil des refontes.
    "liberation_archives": CdxWayback(
        domaine="www.liberation.fr",
        motif_article=r"^https://www\.liberation\.fr/(?:.+/\d{4}/\d{2}/\d{2}/[^/]+_\d+/?|[^?]+-\d{8}_[A-Z0-9]+/?)$",
        periode={"to": "2025"},
        sortie="liberation_url.csv",
    ),
    # laprovence_archives : complete laprovence_url.csv (pagination limitee au
    # recent). Le wrapper moderne /actu/en-direct/<id>/article/... est exclu
    # par le motif (doublon du canonique /article/...).
    "laprovence_archives": CdxWayback(
        domaine="www.laprovence.com",
        motif_article=r"^https://www\.laprovence\.com/(?:article/.+|actu/en-direct/\d+/[^/]+\.html)$",
        sortie="laprovence_url.csv",
    ),
}
