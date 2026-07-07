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


def recuperer(url, ua=UA, via_curl=False, timeout=60):
    """Contenu texte d'une URL (fichier .gz décompressé si besoin), None si échec.
    via_curl : certains CDN bloquent l'empreinte TLS de python-requests."""
    if via_curl:
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


def urls_connues(chemin):
    with open(chemin, newline="", encoding="utf-8") as f:
        return {ligne["url"] for ligne in csv.DictReader(f)}


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
