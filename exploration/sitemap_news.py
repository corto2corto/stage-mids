"""Collecte des sitemaps news : pour chaque média, lit sa (ses) sitemap(s)
news — qui ne consignent que les articles récents (~48 h en général) — et
ajoute au CSV d'URLs du média celles qui y manquent. Conçu pour tourner tous
les jours ; réexécutable à volonté (déduplication contre le CSV, jamais de
réécriture) ; la base urls.db n'est pas touchée.

Si l'URL configurée est un index (<sitemapindex>), ses sous-sitemaps sont
développés automatiquement (ouest_france, leparisien, le_telegramme).

Config issue de la reco des sitemaps du 07/07/2026 (robots.txt des 32 médias,
détail dans le journal). Médias sans entrée : voir les commentaires en fin de
config.

    python -m exploration.sitemap_news              # tous les médias
    python -m exploration.sitemap_news le_figaro    # un seul

À lancer depuis la racine du dépôt.
"""
import sys
import time

from exploration.collecte import (PAUSE, UA_FIREFOX, ajouter, filtrer, locs,
                                  recuperer, sous_sitemaps, trouver_csv,
                                  urls_connues)

# Une entrée par média : url = sitemap(s) news (str ou liste). Options :
# filtre / anti_filtre (motifs sur les URLs gardées), via_curl, ua.
NEWS = {
    # --- anciens médias (CSV dans data/urls/) ---
    "le_figaro":  {"url": "https://www.lefigaro.fr/sitemap_news.xml"},
    # le_capital : sitemap/news.xml du robots = page html meta-refresh, la vraie :
    "le_capital": {"url": "https://www.capital.fr/sitemap/google-news.xml"},
    "le_nouvel_observateur": {"url": "https://www.nouvelobs.com/sitemap/sitemap-articles-news.xml"},
    "le_monde":   {"url": "https://www.lemonde.fr/sitemap_news.xml"},
    # les_echos, le_telegramme, ouest_france, paris_normandie : le CDN bloque
    # l'empreinte TLS de python-requests (constaté au run du 07/07), curl passe.
    "les_echos":  {"url": "https://www.lesechos.fr/sitemap_news.xml", "via_curl": True},
    "telerama":   {"url": "https://www.telerama.fr/sitemaps/sitemap_news.php"},
    "valeurs_actuelles": {"url": "https://www.valeursactuelles.com/news-sitemap.xml"},
    # l_opinion : news-sitemap.xml du robots = 301 vers celle-ci :
    "l_opinion":  {"url": "https://www.lopinion.fr/news-sitemap-content.xml"},
    "challenges": {"url": "https://www.challenges.fr/sitemap.news.xml"},
    "paris_match": {"url": "https://www.parismatch.com/sitemap/news.xml"},
    "atlantico":  {"url": "https://atlantico.fr/news-sitemap.xml"},  # domaine sans www
    "la_depeche": {"url": "https://www.ladepeche.fr/sitemap-news.xml"},  # ~1000 dernières URLs
    "le_telegramme": {"url": "https://www.letelegramme.fr/sitemaps/sitemap-news.xml",
                      "via_curl": True},  # mini-index
    # nice_matin, le_journal_du_dimanche, sud_ouest : anti-bots stricts, seule
    # l'empreinte Chrome de curl_cffi passe (sondé le 07/07, comme le moteur basic).
    "nice_matin": {"url": "https://www.nicematin.com/googlenews.xml", "via_cffi": True},
    "le_journal_du_dimanche": {"url": "https://www.lejdd.fr/sitemap/news.xml", "via_cffi": True},
    "sud_ouest": {"url": "https://www.sudouest.fr/sitemap-news.xml", "via_cffi": True},

    # --- nouveaux médias (CSV dans exploration/) ---
    # mediapart : la news du robots (« editor choice », 33 URLs) n'est pas
    # exhaustive ; les sitemaps par rubrique remontent à ~6 mois. Le filtre
    # garde les articles datés (/journal/<rubrique>/JJMMAA/...).
    "mediapart":  {"url": [f"https://www.mediapart.fr/journal/{r}/sitemap.xml"
                           for r in ("international", "france", "politique",
                                     "economie", "ecologie", "culture-idees")],
                   "filtre": r"/journal/[a-z-]+/\d{6}/"},
    "gala":       {"url": "https://www.gala.fr/sitemaps/news.xml"},
    # voici : sitemap/news.xml du robots = 301 meta-refresh, la vraie :
    "voici":      {"url": "https://www.voici.fr/sitemap/google-news.xml"},
    "bfmtv":      {"url": "https://www.bfmtv.com/sitemap_news.xml"},  # plafond 1000, ~36 h
    "ouest_france": {"url": "https://www.ouest-france.fr/googlenews.xml",
                     "via_curl": True},  # index de 4 fichiers
    # leparisien : index de 2 pages ; la 2e mélange de vieux articles re-modifiés
    # (tri lastmod), sans conséquence grâce à la déduplication par URL.
    "leparisien": {"url": "https://www.leparisien.fr/arc/outboundfeeds/news-sitemap-index/?outputType=xml"},
    "la_croix":   {"url": "https://www.la-croix.com/feeds/sitemaps/sitemap_news.xml"},
    "laprovence": {"url": "https://www.laprovence.com/googlenews.xml", "via_curl": True},
    "marianne":   {"url": "https://www.marianne.net/sitemap_news.xml", "ua": UA_FIREFOX},
    # midilibre : sitemap-news polluée par des articles 2013-2020 (reco 07/07) ;
    # sans gravité pour la collecte, la déduplication écarte le déjà-connu.
    "midilibre":  {"url": "https://www.midilibre.fr/sitemap-news.xml"},
    # paris_normandie : Akamai bloque désormais UA_FIREFOX, l'UA académique passe
    "paris_normandie": {"url": "https://www.paris-normandie.fr/sites/default/files/sitemaps/www_paris_normandie_fr/sitemapnews-0.xml",
                        "via_curl": True},
    "latribune":  {"url": "https://www.latribune.fr/sitemap-actualites.xml"},  # plafond 100
    # liberation : plafond 100, fenêtre ~23 h -> interroger au moins 1x/jour
    "liberation": {"url": "https://www.liberation.fr/arc/outboundfeeds/sitemap_news.xml?outputType=xml"},

    # --- sans entrée pour l'instant (reco 07/07/2026) ---
    # cnews : Cloudflare bloque curl ; via_cffi à essayer quand le média sera mappé.
    # francesoir : pas de sitemap news, sitemap classique paginé non trié par date.
    # 20minutes : mapping en cours (session tmux du 07/07), à activer une fois le
    #   CSV posé : {"url": "https://www.20minutes.fr/sitemap-news.xml"}
}

medias = sys.argv[1:] or list(NEWS)
inconnus = [m for m in medias if m not in NEWS]
if inconnus:
    raise SystemExit(f"média(s) sans sitemap news : {', '.join(inconnus)}\nmedias : {', '.join(NEWS)}")

total = 0
for media in medias:
    fiche = NEWS[media]
    chemin = trouver_csv(media)
    if chemin is None:
        print(f"{media:<24} AUCUN CSV : média pas encore mappé, ignoré")
        continue
    ua = fiche.get("ua")
    options = {"via_curl": fiche.get("via_curl", False),
               "via_cffi": fiche.get("via_cffi", False), **({"ua": ua} if ua else {})}
    urls = []
    for u in ([fiche["url"]] if isinstance(fiche["url"], str) else fiche["url"]):
        texte = recuperer(u, **options)
        if texte is None:
            print(f"{media:<24} sitemap inaccessible : {u}")
            continue
        if "<sitemapindex" in texte[:2000]:  # index -> développer les sous-sitemaps
            for sm, _ in sous_sitemaps(texte):
                time.sleep(PAUSE)
                t = recuperer(sm, **options)
                if t is None:
                    print(f"{media:<24} sous-sitemap inaccessible : {sm}")
                    continue
                urls += locs(t)
        else:
            urls += locs(texte)
        time.sleep(PAUSE)
    urls = set(filtrer(urls, fiche.get("filtre"), fiche.get("anti_filtre")))
    nouvelles = urls - urls_connues(chemin)
    if nouvelles:
        ajouter(chemin, nouvelles)
    print(f"{media:<24} {len(urls):>5} dans la sitemap news, {len(nouvelles):>5} ajoutées")
    total += len(nouvelles)

print(f"\nTerminé : {total} URLs ajoutées.")
