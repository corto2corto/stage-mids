"""Plomberie commune aux collectes par sitemap (exploration.sitemap_news,
exploration.rattrapage_sitemaps) : requêtes, parsing des sitemaps, ajout
incrémental aux CSV d'URLs.

Les CSV d'URLs (data/urls/<media>_url.csv pour les anciens médias,
exploration/<media>_url.csv pour les nouveaux) ne sont JAMAIS réécrits :
on ajoute les URLs manquantes à la fin (append). La base urls.db n'est
pas touchée par ces scripts.
"""
import csv
import gzip
import html
import re
import subprocess
from pathlib import Path

import requests

UA = "Mozilla/5.0 (recherche academique, mapping-agent)"
UA_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
UA_CHROME = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PAUSE = 1.0  # politesse envers le serveur du média
MOTIF_LOC = re.compile(r"<loc>([^<]+)</loc>")
MOTIF_SITEMAP = re.compile(r"<sitemap>(.*?)</sitemap>", re.S)
MOTIF_LASTMOD = re.compile(r"<lastmod>([^<]+)</lastmod>")
DOSSIERS_CSV = [Path("data/urls"), Path("exploration")]


_SESSION_CFFI = None


def _cffi():
    """Session curl_cffi partagée, créée au premier besoin (import paresseux :
    curl_cffi n'est installé que sur le serveur)."""
    global _SESSION_CFFI
    if _SESSION_CFFI is None:
        from curl_cffi import requests as cffi_requests
        _SESSION_CFFI = cffi_requests.Session(impersonate="chrome")
        _SESSION_CFFI.headers["Accept-Language"] = "fr-FR,fr;q=0.8,en-US;q=0.5,en;q=0.3"
    return _SESSION_CFFI


def recuperer(url, ua=UA, via_curl=False, via_cffi=False, timeout=60):
    """Contenu texte d'une URL (fichier .gz décompressé si besoin), None si échec.
    via_curl : certains CDN bloquent l'empreinte TLS de python-requests.
    via_cffi : anti-bots plus stricts (Cloudflare/Datadome/Akamai) — imite un
    vrai Chrome comme le moteur basic (cf scraping/basic.py)."""
    if via_cffi:
        try:
            r = _cffi().get(url, timeout=timeout)
        except Exception:
            return None
        if r.status_code != 200 or not r.content:
            return None
        brut = r.content
    elif via_curl:
        p = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "--compressed", "-A", ua,
             "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
             "-H", "Accept-Language: fr-FR,fr;q=0.9", url],
            capture_output=True, timeout=timeout + 30)
        if p.returncode != 0 or not p.stdout:
            return None
        brut = p.stdout
    else:
        try:
            r = requests.get(url, headers={"User-Agent": ua}, timeout=timeout)
            r.raise_for_status()
        except requests.RequestException:
            return None
        brut = r.content
    if brut[:2] == b"\x1f\x8b":  # sous-sitemap .xml.gz servi tel quel
        try:
            brut = gzip.decompress(brut)
        except OSError:
            pass
    return brut.decode("utf-8", errors="replace")


def locs(texte):
    """URLs des <loc> d'un sitemap, entités XML déséchappées (&amp; -> &)."""
    return [html.unescape(u).strip() for u in MOTIF_LOC.findall(texte)]


def sous_sitemaps(texte):
    """Liste [(loc, lastmod|None), ...] des blocs <sitemap> d'un index."""
    resultat = []
    for bloc in MOTIF_SITEMAP.findall(texte):
        loc = MOTIF_LOC.search(bloc)
        if not loc:
            continue
        lastmod = MOTIF_LASTMOD.search(bloc)
        resultat.append((html.unescape(loc.group(1)).strip(),
                         lastmod.group(1)[:10] if lastmod else None))
    return resultat


def filtrer(urls, filtre=None, anti_filtre=None):
    if filtre:
        f = re.compile(filtre)
        urls = [u for u in urls if f.search(u)]
    if anti_filtre:
        a = re.compile(anti_filtre)
        urls = [u for u in urls if not a.search(u)]
    return urls


def trouver_csv(media):
    """Chemin du CSV d'URLs existant du média, None s'il n'existe pas (média
    pas encore mappé : on n'invente jamais un CSV)."""
    for d in DOSSIERS_CSV:
        chemin = d / f"{media}_url.csv"
        if chemin.exists():
            return chemin
    return None


def url_article(champs):
    """URL d'article d'une ligne CSV : le dernier champ qui commence par http.
    Gère les deux formats de nos CSV — ancien 'sitemap,url' (2 colonnes,
    l'article est en 2e) et nouveau 'url' (1 colonne) — ainsi que nos ajouts,
    toujours écrits en 1 colonne. Renvoie None si aucun champ n'est une URL
    (ligne vide, octet résiduel d'un crash, déchet)."""
    for c in reversed(champs):
        c = c.strip()
        if c.startswith("http"):
            return c
    return None


# Motifs sûrs de non-articles, validés sur échantillons le 11-12/07/2026
# (cf exploration/regles_non_articles.md). Jamais de motif « mot dans le slug »
# (video, rss, auteur… abondent dans des titres d'articles légitimes) :
# uniquement sous-domaine, segment de chemin ou extension de fichier.
EXTENSIONS_FICHIER = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".mp3", ".mp4", ".xml")
ARTEFACTS = ("image:media", "httpRequest", "%20http")
SEGMENTS_EXCLUS = {
    "le_monde": ("lemonde.fr/resultats-", "/live/", "/visuel/"),
    "le_nouvel_observateur": ("/galeries-photos/",),
    "les_echos": ("/internal/",),
    "le_journal_du_dimanche": ("lejdd.fr/sommaire/",),
}


def est_non_article(media, url):
    """Vrai si l'URL porte un motif sûr de non-article : à écarter avant la base."""
    sans_requete = url.split("?")[0]
    morceaux = sans_requete.split("/")           # ['https:', '', hôte, chemin...]
    hote = morceaux[2] if len(morceaux) > 2 else ""
    chemin = "/".join(morceaux[3:])
    if not chemin.strip("/"):                    # racine du site seule
        return True
    if hote.startswith(("video.", "podcasts.")):
        return True
    if sans_requete.lower().rstrip("/").endswith(EXTENSIONS_FICHIER):
        return True
    if any(a in url for a in ARTEFACTS):
        return True
    return any(seg in sans_requete for seg in SEGMENTS_EXCLUS.get(media, ()))


def lire_urls(chemin):
    """Ensemble des URLs d'articles d'un CSV, tous formats confondus."""
    urls = set()
    with open(chemin, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)  # en-tête (url ou sitemap,url)
        for champs in r:
            u = url_article(champs)
            if u:
                urls.add(u)
    return urls


def urls_connues(chemin):
    return lire_urls(chemin)


def ajouter(chemin, urls):
    """Ajoute des URLs à la fin du CSV existant, sans réécrire les lignes en place."""
    with open(chemin, "rb+") as f:  # si la dernière ligne n'a pas de saut, la clore
        f.seek(0, 2)
        if f.tell():
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\r\n")
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for u in sorted(urls):
            w.writerow([u])
