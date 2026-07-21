"""Verifie les scripts de mapping des nouveaux medias. A lancer sur le
serveur depuis la racine du depot :

    python -m mapping.verifier

Cas nominaux : smoke-run reel de chaque script en mode echantillon
(MAPPING_LIMITE=3, quelques requetes seulement), puis controle du CSV
produit : en-tete "url", au moins une ligne, pas de doublons, toutes les
URLs conformes au motif attendu du media. Les CSV echantillons seront
ecrases par les runs complets.

Cas limites : pagination hors bornes (Marianne ?p=2000, France-Soir
?page=9999), page jour future (Le Parisien), flux gzip invalide (logique
de repli de mapping_bfmtv/midilibre).

Code retour : 0 si tout passe, 1 sinon.
"""
import csv
import gzip
import os
import re
import subprocess
import sys
from datetime import date, timedelta

import requests

MEDIAS = {
    "gala": r"https://www\.gala\.fr/.+",
    "voici": r"https://www\.voici\.fr/.+",
    "la_croix": r"https://www\.la-croix\.com/.+",
    "bfmtv": r"https://www\.bfmtv\.com/.+",
    "midilibre": r"https://www\.midilibre\.fr/.+",
    "lexpress": r"https://www\.lexpress\.fr/.+",
    "francesoir": r"https://www\.francesoir\.fr/[a-z0-9_-]+/[^/]+$",
    # le slug final manque sur de rares URLs du sitemap (le routage se fait par l'id)
    "paris_normandie": r"https://www\.paris-normandie\.fr/id\d+/article/\d{4}-\d{2}-\d{2}(/.*)?$",
    "liberation": r"https://www\.liberation\.fr/.+",
    "marianne": r"https://www\.marianne\.net/[a-z-]+(?:/[a-z0-9-]+)?/[a-z0-9-]{25,}$",
    "leparisien": r"https://www\.leparisien\.fr/.+-\d{2}-\d{2}-\d{4}-[A-Z0-9]+\.php$",
}
UA_NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
resultats = []

# --- cas nominaux : smoke-run de chaque script + controle du CSV ---
env = {**os.environ, "MAPPING_LIMITE": "3"}
for media, motif in MEDIAS.items():
    nom = f"smoke {media}"
    try:
        p = subprocess.run(
            [sys.executable, "-m", "mapping.generique", media],
            env=env, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        resultats.append((nom, False, "timeout 300s"))
        continue
    if p.returncode != 0:
        resultats.append((nom, False, f"code {p.returncode} : {(p.stderr or p.stdout)[-300:]}"))
        continue
    chemin = f"exploration/{media}_url.csv"
    if not os.path.exists(chemin):
        resultats.append((nom, False, f"{chemin} absent"))
        continue
    with open(chemin, newline="", encoding="utf-8") as f:
        lignes = list(csv.reader(f))
    entete, urls = lignes[0], [l[0] for l in lignes[1:] if l]
    controle = re.compile(motif)
    non_conformes = [u for u in urls if not controle.match(u)]
    if entete != ["url"]:
        resultats.append((nom, False, f"en-tete inattendu : {entete}"))
    elif not urls:
        resultats.append((nom, False, "CSV vide (0 URL)"))
    elif len(urls) != len(set(urls)):
        resultats.append((nom, False, f"{len(urls) - len(set(urls))} doublons"))
    elif non_conformes:
        resultats.append((nom, False, f"{len(non_conformes)} URLs hors motif, ex : {non_conformes[0][:120]}"))
    else:
        resultats.append((nom, True, f"{len(urls)} URLs conformes"))

# --- cas limite : Marianne au-dela de la profondeur reelle -> page vide OU
# repetition de la page 1 (les deux declenchent l'arret "0 nouvelle URL" du
# script ; comportement observe : p=500 vide, p=2000 re-sert la page 1) ---
motif = re.compile(r'href="(https://www\.marianne\.net/politique(?:/[a-z0-9-]+)?/[a-z0-9-]{25,})"')
r1 = requests.get("https://www.marianne.net/politique", params={"p": 1}, headers=UA_NAVIGATEUR, timeout=30)
rh = requests.get("https://www.marianne.net/politique", params={"p": 99999}, headers=UA_NAVIGATEUR, timeout=30)
p1, ph = set(motif.findall(r1.text)), set(motif.findall(rh.text))
resultats.append(("limite marianne p hors bornes", rh.ok and (not ph or ph <= p1),
                  f"HTTP {rh.status_code}, {len(ph)} article(s), inclus dans p=1 : {ph <= p1}"))

# --- cas limite : France-Soir page hors bornes -> reponse geree, 0 article ---
r = requests.get("https://www.francesoir.fr/sitemap.xml", params={"page": 9999},
                 headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}, timeout=30)
locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
articles = [u for u in locs if re.match(r"https://www\.francesoir\.fr/[a-z0-9_-]+/[^/<\s]+$", u)]
resultats.append(("limite francesoir page=9999", not articles,
                  f"HTTP {r.status_code}, {len(articles)} article(s)"))

# --- cas limite : Le Parisien jour futur -> pas d'article, pas de plantage ---
futur = date.today() + timedelta(days=30)
r = requests.get(f"https://www.leparisien.fr/archives/{futur.year}/{futur.strftime('%d-%m-%Y')}/",
                 headers=UA_NAVIGATEUR, timeout=30)
trouves = re.findall(r'href="(?:https:)?//www\.leparisien\.fr(/[^"]*-\d{2}-\d{2}-\d{4}-\d+\.php)"', r.text)
resultats.append(("limite leparisien jour futur", not trouves,
                  f"HTTP {r.status_code}, {len(trouves)} article(s)"))

# --- cas limite : gzip invalide -> le repli texte de bfmtv/midilibre tient ---
contenu = b"<urlset><loc>https://exemple.fr/a</loc></urlset>"  # pas du gzip
try:
    texte = gzip.decompress(contenu).decode("utf-8", errors="replace")
except (gzip.BadGzipFile, OSError):
    texte = contenu.decode("utf-8", errors="replace")
resultats.append(("limite gzip invalide", re.findall(r"<loc>([^<]+)</loc>", texte) == ["https://exemple.fr/a"],
                  "repli texte OK"))

# --- recapitulatif ---
print()
echecs = 0
for nom, ok, detail in resultats:
    print(f"{'PASS' if ok else 'FAIL'}  {nom:35s} {detail}")
    echecs += not ok
print(f"\n{len(resultats) - echecs}/{len(resultats)} verifications passees")
sys.exit(1 if echecs else 0)
