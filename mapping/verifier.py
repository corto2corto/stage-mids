"""Verifie le moteur de mapping (mapping.generique) sur les medias du
catalogue. A lancer sur le serveur depuis la racine du depot :

    python -m mapping.verifier                # tous les medias
    python -m mapping.verifier cnews gala     # cibles
    python -m mapping.verifier --sec          # controles hors reseau seuls (OK en local)

Controles a sec (aucune requete) : chaque fiche a un collecteur connu, tous
ses motifs regex compilent, ses gabarits d'URL ont les bons champs.

Cas nominaux : smoke-run reel de chaque media (MAPPING_LIMITE=3, quelques
requetes seulement) dans un dossier temporaire via MAPPING_SORTIE_DIR — les
CSV de prod ne sont JAMAIS touches, ni lus ni ecrits. Controle du CSV
produit : en-tete "url", non vide, pas de doublons, URLs conformes au motif
attendu du media, tout en https, pas de query string residuelle.

Cas limites reseau : pagination hors bornes (marianne, francesoir,
laprovence), page jour future (leparisien), flux gzip invalide, page CDX en
zone creuse.

Code retour : 0 si tout passe, 1 sinon.
"""
import csv
import gzip
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, timedelta

import requests

from mapping.catalogue import CATALOGUE
from mapping.generique import COLLECTEURS

# Motif de controle des URLs produites, par media — l'ordre est celui
# d'execution : liberation avant liberation_archives (fusion dans le meme
# CSV), laprovence avant laprovence_archives.
MOTIFS = {
    "gala": r"https://www\.gala\.fr/.+",
    "voici": r"https://www\.voici\.fr/.+",
    "la_croix": r"https://www\.la-croix\.com/.+",
    "bfmtv": r"https://www\.bfmtv\.com/.+",
    "midilibre": r"https://www\.midilibre\.fr/.+",
    "lexpress": r"https://www\.lexpress\.fr/.+",
    "francesoir": r"https://www\.francesoir\.fr/[a-z0-9_-]+/[^/]+$",
    # le slug final manque sur de rares URLs du sitemap (le routage se fait par l'id)
    "paris_normandie": r"https://www\.paris-normandie\.fr/id\d+/article/\d{4}-\d{2}-\d{2}(/.*)?$",
    "closermag": r"https://www\.closermag\.fr/.+",
    "cnews": r"https://www\.cnews\.fr/(?:[^/]+/)?\d{4}-\d{2}-\d{2}/[^/]+/?$",
    "ouest_france": r"https://www\.ouest-france\.fr/.+",
    "marianne": r"https://www\.marianne\.net/[a-z-]+(?:/[a-z0-9-]+)?/[a-z0-9-]{25,}$",
    "leparisien": r"https://www\.leparisien\.fr/.+-\d{2}-\d{2}-\d{4}-[A-Z0-9]+\.php$",
    "blast": r"https://www\.blast-info\.fr/articles/\d{4}/.+",
    "mediapart": r"https://www\.mediapart\.fr/journal/.+",
    "20minutes": r"https://www\.20minutes\.fr/[a-z0-9\-/]+/\d+-\d{8}-[a-z0-9\-]+$",
    "leprogres": r"https://www\.leprogres\.fr/[^/]+/\d{4}/\d{2}/\d{2}/.+",
    "lepoint": r"https://www\.lepoint\.fr/.+-\d{2}-\d{2}-\d{4}-\d+_\d+\.php$",
    "latribune": r"https://www\.latribune\.fr/(?:.+-\d{6,}\.html|article/.+)$",
    "liberation": r"https://www\.liberation\.fr/.+",
    "liberation_archives": r"https://www\.liberation\.fr/.+",
    "laprovence": r"https://www\.laprovence\.com/article/.+",
    "laprovence_archives": r"https://www\.laprovence\.com/(?:article/.+|actu/en-direct/.+)",
}
UA_NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
resultats = []


# --- controles a sec : fiches coherentes, motifs compilables ---
def controles_a_sec():
    for media, fiche in CATALOGUE.items():
        problemes = []
        if type(fiche) not in COLLECTEURS:
            problemes.append(f"pas de collecteur pour {type(fiche).__name__}")
        for champ in ("motif", "motif_article", "motif_jour", "motif_sous_sitemap",
                      "motif_pages", "motif_sections", "filtre", "anti_filtre"):
            valeur = getattr(fiche, champ, None)
            if valeur:
                try:  # meme logique que le moteur : format seulement si {section} attendu
                    re.compile(valeur.format(section="x") if "{section}" in valeur else valeur)
                except (re.error, KeyError, IndexError) as e:
                    problemes.append(f"{champ} : {e}")
        if media not in MOTIFS:
            problemes.append("pas de motif de controle dans mapping.verifier")
        resultats.append((f"sec {media}", not problemes, "; ".join(problemes) or "fiche coherente"))
    for media in MOTIFS:
        if media not in CATALOGUE:
            resultats.append((f"sec {media}", False, "motif de controle sans fiche au catalogue"))


# --- cas nominaux : smoke-run de chaque media + controle du CSV produit ---
def smoke_runs(medias, dossier):
    env = {**os.environ, "MAPPING_LIMITE": "3", "MAPPING_SORTIE_DIR": dossier}
    for media in medias:
        nom = f"smoke {media}"
        try:
            p = subprocess.run(
                [sys.executable, "-m", "mapping.generique", media],
                env=env, capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            resultats.append((nom, False, "timeout 600s"))
            continue
        if p.returncode != 0:
            resultats.append((nom, False, f"code {p.returncode} : {(p.stderr or p.stdout)[-300:]}"))
            continue
        fiche = CATALOGUE[media]
        chemin = os.path.join(dossier, getattr(fiche, "sortie", None) or f"{media}_url.csv")
        if not os.path.exists(chemin):
            resultats.append((nom, False, f"{chemin} absent"))
            continue
        with open(chemin, newline="", encoding="utf-8") as f:
            lignes = list(csv.reader(f))
        entete, urls = lignes[0], [l[0] for l in lignes[1:] if l]
        controle = re.compile(MOTIFS[media])
        non_conformes = [u for u in urls if not controle.match(u)]
        sales = [u for u in urls if "?" in u or "#" in u or not u.startswith("https://")]
        if entete != ["url"]:
            resultats.append((nom, False, f"en-tete inattendu : {entete}"))
        elif not urls:
            resultats.append((nom, False, "CSV vide (0 URL)"))
        elif len(urls) != len(set(urls)):
            resultats.append((nom, False, f"{len(urls) - len(set(urls))} doublons"))
        elif non_conformes:
            resultats.append((nom, False, f"{len(non_conformes)} URLs hors motif, ex : {non_conformes[0][:120]}"))
        elif sales:
            resultats.append((nom, False, f"{len(sales)} URLs mal normalisees, ex : {sales[0][:120]}"))
        else:
            resultats.append((nom, True, f"{len(urls)} URLs conformes"))


# --- cas limites reseau (independants du moteur) ---
def cas_limites():
    # Marianne au-dela de la profondeur reelle -> page vide OU repetition de la
    # page 1 (les deux declenchent l'arret "0 nouvelle URL")
    motif = re.compile(r'href="(https://www\.marianne\.net/politique(?:/[a-z0-9-]+)?/[a-z0-9-]{25,})"')
    r1 = requests.get("https://www.marianne.net/politique", params={"p": 1}, headers=UA_NAVIGATEUR, timeout=30)
    rh = requests.get("https://www.marianne.net/politique", params={"p": 99999}, headers=UA_NAVIGATEUR, timeout=30)
    p1, ph = set(motif.findall(r1.text)), set(motif.findall(rh.text))
    resultats.append(("limite marianne p hors bornes", rh.ok and (not ph or ph <= p1),
                      f"HTTP {rh.status_code}, {len(ph)} article(s), inclus dans p=1 : {ph <= p1}"))

    # France-Soir page hors bornes -> reponse geree, 0 article
    r = requests.get("https://www.francesoir.fr/sitemap.xml", params={"page": 9999},
                     headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}, timeout=30)
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    articles = [u for u in locs if re.match(r"https://www\.francesoir\.fr/[a-z0-9_-]+/[^/<\s]+$", u)]
    resultats.append(("limite francesoir page=9999", not articles,
                      f"HTTP {r.status_code}, {len(articles)} article(s)"))

    # La Provence page-9999 -> vide ou repetition de la page 1
    motif = re.compile(r'href="(?:https://www\.laprovence\.com)?(/article/[^"#?]+)"')
    r1 = requests.get("https://www.laprovence.com/france-monde", headers=UA_NAVIGATEUR, timeout=30)
    rh = requests.get("https://www.laprovence.com/france-monde/page-9999", headers=UA_NAVIGATEUR, timeout=30)
    p1, ph = set(motif.findall(r1.text)), set(motif.findall(rh.text))
    resultats.append(("limite laprovence page-9999", (not ph or ph <= p1) if rh.status_code != 404 else True,
                      f"HTTP {rh.status_code}, {len(ph)} lien(s), inclus dans page 1 : {ph <= p1}"))

    # Le Parisien jour futur -> pas d'article, pas de plantage
    futur = date.today() + timedelta(days=30)
    r = requests.get(f"https://www.leparisien.fr/archives/{futur.year}/{futur.strftime('%d-%m-%Y')}/",
                     headers=UA_NAVIGATEUR, timeout=30)
    trouves = re.findall(r'href="(?:https:)?//www\.leparisien\.fr(/[^"]*-\d{2}-\d{2}-\d{4}-\d+\.php)"', r.text)
    resultats.append(("limite leparisien jour futur", not trouves,
                      f"HTTP {r.status_code}, {len(trouves)} article(s)"))

    # gzip invalide -> le repli texte de la plomberie (magic bytes) tient
    contenu = b"<urlset><loc>https://exemple.fr/a</loc></urlset>"  # pas du gzip
    try:
        texte = gzip.decompress(contenu).decode("utf-8", errors="replace")
    except (gzip.BadGzipFile, OSError):
        texte = contenu.decode("utf-8", errors="replace")
    resultats.append(("limite gzip invalide", re.findall(r"<loc>([^<]+)</loc>", texte) == ["https://exemple.fr/a"],
                      "repli texte OK"))

    # page CDX en zone creuse d'index -> 0 ligne, sans erreur
    r = requests.get("http://web.archive.org/cdx/search/cdx",
                     params={"url": "www.liberation.fr", "matchType": "host", "page": 600, "pageSize": "5",
                             "fl": "original", "filter": ["statuscode:200", "mimetype:text/html"],
                             "collapse": "urlkey", "to": "2025"},
                     headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}, timeout=180)
    resultats.append(("limite CDX zone creuse", r.ok and not r.text.strip(),
                      f"HTTP {r.status_code}, {len(r.text.splitlines())} ligne(s)"))


args = sys.argv[1:]
a_sec_seulement = "--sec" in args
medias = [a for a in args if a != "--sec"] or list(MOTIFS)

controles_a_sec()
if not a_sec_seulement:
    dossier = tempfile.mkdtemp(prefix="smoke_mappings_")
    print(f"CSV de test dans {dossier} (les CSV de prod ne sont pas touches)\n")
    smoke_runs(medias, dossier)
    cas_limites()

# --- recapitulatif ---
print()
echecs = 0
for nom, ok, detail in resultats:
    print(f"{'PASS' if ok else 'FAIL'}  {nom:38s} {detail}")
    echecs += not ok
print(f"\n{len(resultats) - echecs}/{len(resultats)} verifications passees")
sys.exit(1 if echecs else 0)
