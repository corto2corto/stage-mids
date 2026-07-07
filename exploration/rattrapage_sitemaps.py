"""Rattrapage one-shot des anciens médias : leurs CSV d'URLs sont figés depuis
fin mai / début juin 2026 (pause du mapping). On reparcourt leurs sitemaps
d'articles en ne téléchargeant que les sous-sitemaps susceptibles de couvrir
BORNE -> aujourd'hui (lastmod donné par l'index, sinon date dans l'URL du
sous-sitemap, sinon on télécharge dans le doute), puis on ajoute au CSV du
média les URLs qui y manquent. Réexécutable (déduplication contre le CSV,
jamais de réécriture) ; la base n'est pas touchée.

    python -m exploration.rattrapage_sitemaps                # tous les médias
    python -m exploration.rattrapage_sitemaps le_figaro      # un seul

À lancer depuis la racine du dépôt.
"""
import re
import sys
import time

from tqdm import tqdm

from exploration.collecte import (PAUSE, UA, ajouter, filtrer, locs,
                                  recuperer, sous_sitemaps, trouver_csv,
                                  urls_connues)

BORNE = "2026-03"  # on remonte jusqu'à mars 2026 (marge sur le trou réel, fin mai)
MOTIF_DATE_URL = re.compile(r"(20\d{2})[-/_.]?(\d{2})")

# Une fiche par ancien média : index = sitemap(s) d'entrée (str ou liste).
# Options : motif_sous_sitemap / anti_sous_sitemap (restreint les sous-sitemaps
# suivis, ex. exclure les sitemaps de catégories), filtre / anti_filtre (sur
# les URLs d'articles), via_curl, ua.
# Structures relevées lors de la reco des sitemaps du 07/07/2026.
FICHES = {
    # Partout où les sous-sitemaps portent une date dans leur nom, on
    # sélectionne par motif_sous_sitemap plutôt que par lastmod : plusieurs
    # index re-tamponnent leurs lastmod en bloc (le_monde : ~1900 fichiers
    # marqués 2026, le_telegramme : tous au 05/07), ce qui ferait tout
    # retélécharger. Motifs = mars 2026 -> fin 2026, à élargir si réutilisé.
    "le_figaro": {"index": "https://sitemaps.lefigaro.fr/lefigaro.fr/articles.xml",
                  "motif_sous_sitemap": r"/articles/2026-(0[3-9]|1[0-2])-"},  # 1 fichier/jour
    # le_capital : pages non datées et sans lastmod dans l'index ; les pages
    # hautes sont les plus récentes (page-548 = début juillet), on prend la
    # tranche 500+ (très large pour un trou de 6 semaines).
    "le_capital": {"index": "https://www.capital.fr/sitemap/articles.xml",
                   "motif_sous_sitemap": r"/page-5\d{2}\.xml"},
    "le_nouvel_observateur": {"index": "https://www.nouvelobs.com/sitemap/sitemap-index-articles.xml",
                              "motif_sous_sitemap": r"/edito/2026-(0[3-9]|1[0-2])\.xml"},  # mensuel
    "le_monde": {"index": "https://www.lemonde.fr/sitemap_index.xml",
                 "motif_sous_sitemap": r"/articles/2026-(0[3-9]|1[0-2])-"},  # 1 fichier/semaine (lundi)
    # les_echos, le_telegramme : le CDN bloque l'empreinte TLS de
    # python-requests (constaté au run du 07/07), curl passe.
    "les_echos": {"index": "https://sitemap.lesechos.fr/sitemap_index.xml",
                  "via_curl": True},  # sitemapN.xml.gz non datés, lastmod
    "telerama": {"index": "https://www.telerama.fr/sitemaps/sitemap_index.php",
                 "motif_sous_sitemap": r"/articles/2026-"},  # semestriel : 2026-01-01 + 2026-07-01
    "l_opinion": {"index": "https://www.lopinion.fr/sitemap.xml",
                  "motif_sous_sitemap": r"sitemap-2026(0[3-9]|1[0-2])\.xml"},  # mensuel AAAAMM
    "challenges": {"index": "https://www.challenges.fr/sitemap.xml",
                   "motif_sous_sitemap": r"sitemap-2026-(0[3-9]|1[0-2])\.xml"},  # mensuel, gzip
    "paris_match": {"index": "https://www.parismatch.com/sitemap.xml"},  # ?page=N non datés, lastmod
    "atlantico": {"index": "https://atlantico.fr/sitemap-index.xml",
                  "motif_sous_sitemap": r"/sitemaps/2026-(0[3-9]|1[0-2])\.xml"},  # mensuel
    "la_depeche": {"index": "https://www.ladepeche.fr/sitemap.xml",
                   "motif_sous_sitemap": r"sitemap-2026-(0[3-9]|1[0-2])_"},  # mensuel en parts, gzip
    "le_telegramme": {"index": "https://www.letelegramme.fr/sitemaps/sitemap.xml",
                      "motif_sous_sitemap": r"urlset_2026-(0[3-9]|1[0-2])",
                      "via_curl": True},  # mensuel, gzip

    # nice_matin, le_journal_du_dimanche, sud_ouest : anti-bots stricts, seule
    # l'empreinte Chrome de curl_cffi passe (sondé le 07/07, comme le moteur basic).
    # nice_matin : pages numérotées à l'envers (1 = le plus récent, ~1000 URLs
    # par page), lastmod d'index tous re-tamponnés -> pages 1 à 40 (~4-5 mois).
    "nice_matin": {"index": "https://www.nicematin.com/sitemap.xml",
                   "motif_sous_sitemap": r"/sitemap_articles_([1-9]|[1-3]\d|40)\.xml",
                   "via_cffi": True},
    "le_journal_du_dimanche": {"index": "https://www.lejdd.fr/sitemap.xml",
                               "via_cffi": True},  # 15 pages, lastmod fiables
    "sud_ouest": {"index": "https://www.sudouest.fr/sitemap.xml",
                  "motif_sous_sitemap": r"articles-2026-(0[3-9]|1[0-2])",
                  "via_cffi": True},  # mensuel daté

    # Exclu : valeurs_actuelles — post-sitemaps figés au 20/10/2025, aucun
    # contenu 2026 dans les sitemaps classiques -> autre source à trouver.
}


def couvre_borne(loc, lastmod):
    """Un sous-sitemap peut-il contenir des articles >= BORNE ? Un sitemap dont
    le contenu n'a pas changé depuis BORNE ne peut rien apporter de plus récent.
    Sans lastmod ni date dans l'URL, on le garde dans le doute."""
    if lastmod:
        return lastmod[:7] >= BORNE
    m = MOTIF_DATE_URL.search(loc)
    if m:
        return f"{m.group(1)}-{m.group(2)}" >= BORNE
    return True


medias = sys.argv[1:] or list(FICHES)
inconnus = [m for m in medias if m not in FICHES]
if inconnus:
    raise SystemExit(f"média(s) sans fiche : {', '.join(inconnus)}\nmedias : {', '.join(FICHES)}")

total = 0
for media in medias:
    fiche = FICHES[media]
    chemin = trouver_csv(media)
    if chemin is None:
        print(f"{media:<24} AUCUN CSV : média pas encore mappé, ignoré")
        continue

    index = fiche["index"] if isinstance(fiche["index"], list) else [fiche["index"]]
    ua = fiche.get("ua", UA)
    via_curl = fiche.get("via_curl", False)
    via_cffi = fiche.get("via_cffi", False)

    # parcours de l'index : on descend dans les sous-sitemaps retenus par la
    # borne, un <sitemapindex> intermédiaire est développé au tour suivant
    a_voir = [(u, None) for u in index]
    urls, sitemaps_lus, profondeur = set(), 0, 0
    while a_voir and profondeur < 4:
        suivants = []
        for loc, lastmod in tqdm(a_voir, desc=f"{media} (niveau {profondeur})"):
            if not couvre_borne(loc, lastmod):
                continue
            motif_sm = fiche.get("motif_sous_sitemap")
            if profondeur and motif_sm and not re.search(motif_sm, loc):
                continue
            anti_sm = fiche.get("anti_sous_sitemap")
            if profondeur and anti_sm and re.search(anti_sm, loc):
                continue
            texte = recuperer(loc, ua=ua, via_curl=via_curl, via_cffi=via_cffi)
            if texte is None:
                print(f"{loc} : échec, ignoré")
                continue
            sitemaps_lus += 1
            if "<sitemapindex" in texte[:2000]:
                suivants += sous_sitemaps(texte)
            else:
                urls.update(filtrer(locs(texte),
                                    fiche.get("filtre"), fiche.get("anti_filtre")))
            time.sleep(PAUSE)
        a_voir = suivants
        profondeur += 1

    nouvelles = urls - urls_connues(chemin)
    if nouvelles:
        ajouter(chemin, nouvelles)
    print(f"{media:<24} {sitemaps_lus} sitemaps lus, {len(urls)} URLs vues, "
          f"{len(nouvelles)} ajoutées ({chemin})")
    total += len(nouvelles)

print(f"\nTerminé : {total} URLs ajoutées.")
