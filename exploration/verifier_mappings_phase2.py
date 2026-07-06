"""Verifie les scripts de mapping de la phase 2 (Ouest-France via Selenium,
La Provence via pagination page-N, Le Point / La Tribune / archives
Liberation via l'API CDX de la Wayback Machine). A lancer sur le serveur
depuis la racine du depot :

    python -m exploration.verifier_mappings_phase2

Cas nominaux : smoke-run reel de chaque script (MAPPING_LIMITE=2) puis
controle du CSV : en-tete "url", non vide, pas de doublons, URLs conformes
au motif du media, aucune query string residuelle, tout en https. Les CSV
echantillons seront ecrases par les runs complets (celui de liberation
fusionne au lieu d'ecraser).

Cas limites : page CDX vide (zone creuse d'index -> 0 ligne sans erreur),
page-9999 La Provence (vide ou repetition de la page 1, les deux declenchent
l'arret du script).

Code retour : 0 si tout passe, 1 sinon.
"""
import csv
import os
import re
import subprocess
import sys

import requests

MEDIAS = {
    "ouest_france": r"https://www\.ouest-france\.fr/.+",
    "laprovence": r"https://www\.laprovence\.com/article/.+",
    "lepoint": r"https://www\.lepoint\.fr/.+-\d{2}-\d{2}-\d{4}-\d+_\d+\.php$",
    "latribune": r"https://www\.latribune\.fr/(?:.+-\d{6,}\.html|article/.+)$",
    "liberation_archives": r"https://www\.liberation\.fr/.+",
}
SORTIES = {"liberation_archives": "liberation_url.csv"}
UA_NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
resultats = []

# --- cas nominaux : smoke-run de chaque script + controle du CSV ---
env = {**os.environ, "MAPPING_LIMITE": "2"}
for media, motif in MEDIAS.items():
    nom = f"smoke {media}"
    try:
        p = subprocess.run(
            [sys.executable, "-m", f"exploration.mapping_{media}"],
            env=env, capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        resultats.append((nom, False, "timeout 600s"))
        continue
    if p.returncode != 0:
        resultats.append((nom, False, f"code {p.returncode} : {(p.stderr or p.stdout)[-300:]}"))
        continue
    chemin = "exploration/" + SORTIES.get(media, f"{media}_url.csv")
    if not os.path.exists(chemin):
        resultats.append((nom, False, f"{chemin} absent"))
        continue
    with open(chemin, newline="", encoding="utf-8") as f:
        lignes = list(csv.reader(f))
    entete, urls = lignes[0], [l[0] for l in lignes[1:] if l]
    controle = re.compile(motif)
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

# --- cas limite : page CDX en zone creuse -> 0 ligne, sans erreur ---
r = requests.get("http://web.archive.org/cdx/search/cdx",
                 params={"url": "www.liberation.fr", "matchType": "host", "page": 600, "pageSize": "5",
                         "fl": "original", "filter": ["statuscode:200", "mimetype:text/html"],
                         "collapse": "urlkey", "to": "2025"},
                 headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"}, timeout=180)
resultats.append(("limite CDX zone creuse", r.ok and not r.text.strip(),
                  f"HTTP {r.status_code}, {len(r.text.splitlines())} ligne(s)"))

# --- cas limite : La Provence page-9999 -> vide ou repetition de la page 1 ---
motif = re.compile(r'href="(?:https://www\.laprovence\.com)?(/article/[^"#?]+)"')
r1 = requests.get("https://www.laprovence.com/france-monde", headers=UA_NAVIGATEUR, timeout=30)
rh = requests.get("https://www.laprovence.com/france-monde/page-9999", headers=UA_NAVIGATEUR, timeout=30)
p1, ph = set(motif.findall(r1.text)), set(motif.findall(rh.text))
resultats.append(("limite laprovence page-9999", (not ph or ph <= p1) if rh.status_code != 404 else True,
                  f"HTTP {rh.status_code}, {len(ph)} lien(s), inclus dans page 1 : {ph <= p1}"))

# --- recapitulatif ---
print()
echecs = 0
for nom, ok, detail in resultats:
    print(f"{'PASS' if ok else 'FAIL'}  {nom:35s} {detail}")
    echecs += not ok
print(f"\n{len(resultats) - echecs}/{len(resultats)} verifications passees")
sys.exit(1 if echecs else 0)
