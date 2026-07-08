"""Verse dans urls.db les URLs présentes dans les CSV mais absentes de la base,
média par média. One-shot après le rattrapage sitemaps du 07/07/2026, puis
resynchronisation à la demande. Petit frère de charger_nouveaux_medias.py :
lui initialise les médias ABSENTS de la base, celui-ci complète les médias
déjà chargés. Garde-fous :

- uniquement des INSERT (etat=0) : jamais d'UPDATE ni de DELETE, les lignes
  et états existants ne sont pas touchés ;
- un média absent de la base est ignoré (rôle de charger_nouveaux_medias) ;
- les médias en pause sont ignorés ;
- une transaction par média (tout ou rien) ; réexécutable, la différence se
  recalcule à chaque run (un média déjà versé donne 0 à insérer) ;
- sauvegarde automatique de urls.db (VACUUM INTO horodaté) avant la première
  écriture — sautée s'il n'y a rien à verser ;
- compte au passage les doublons (media, url) préexistants en base (lignes
  lues vs distinctes) : doit être 0 partout avant de créer l'index unique.

À lancer depuis la racine du dépôt, scrapping en pause de préférence :
    python -m exploration.verser_nouveaux            # tous les médias
    python -m exploration.verser_nouveaux le_figaro  # un seul
"""
import csv
import os
import sqlite3
import sys
import time
from pathlib import Path

from exploration.collecte import url_article
from scraping.medias import MEDIAS
from scraping.stockage import DATA_DIR

SOURCES = [Path("data/urls"), Path("exploration")]

# sud_ouest : zone disque illisible sous son CSV (07/07, lectures figées en
# état D) — à réintégrer une fois le fichier régénéré depuis la base.
EXCLUS = {"sud_ouest"}

conn = sqlite3.connect(DATA_DIR / "urls.db", timeout=60)
medias = sys.argv[1:] or sorted(MEDIAS)
total = 0
doublons_total = 0
sauvegarde_faite = False
for media in medias:
    if media in EXCLUS:
        print(f"{media:<24} exclu (CSV illisible, cf. EXCLUS) : ignoré", flush=True)
        continue
    if MEDIAS[media].get("pause"):
        print(f"{media:<24} en pause : ignoré", flush=True)
        continue
    chemin = next((d / f"{media}_url.csv" for d in SOURCES
                   if (d / f"{media}_url.csv").exists()), None)
    if not chemin:
        print(f"{media:<24} aucun CSV : ignoré", flush=True)
        continue
    lignes = [l[0] for l in conn.execute("SELECT url FROM urls WHERE media=?", (media,))]
    if not lignes:
        print(f"{media:<24} absent de la base : passer par charger_nouveaux_medias", flush=True)
        continue
    en_base = set(lignes)
    doublons = len(lignes) - len(en_base)
    doublons_total += doublons
    # Extraction universelle de l'URL d'article (gère 'sitemap,url' et 'url',
    # cf. collecte.url_article) ; une ligne sans URL (vide, déchet, octet de
    # crash) est comptée en `ignorees`, jamais insérée (sinon NOT NULL sur url).
    du_csv_set, ignorees = set(), 0
    with open(chemin, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)  # en-tête
        for champs in r:
            u = url_article(champs)
            if u:
                du_csv_set.add(u)
            else:
                ignorees += 1
    du_csv = du_csv_set
    nouvelles = [u for u in du_csv if u not in en_base]
    if nouvelles and not sauvegarde_faite:  # VACUUM INTO refuse d'écraser : nom horodaté
        if os.environ.get("VERSER_SKIP_BACKUP"):
            print("sauvegarde sautée (VERSER_SKIP_BACKUP) — backup déjà disponible", flush=True)
        else:
            cible = DATA_DIR / f"urls.db.avant_versement-{time.strftime('%Y%m%d-%H%M%S')}"
            print(f"sauvegarde de urls.db vers {cible} (quelques minutes)...", flush=True)
            conn.execute(f"VACUUM INTO '{cible}'")
        sauvegarde_faite = True
    if nouvelles:
        with conn:  # une transaction par média : tout ou rien
            conn.executemany("INSERT INTO urls (media, url, etat) VALUES (?, ?, 0)",
                             [(media, u) for u in nouvelles])
    suffixe = f", {ignorees} ignorées" if ignorees else ""
    print(f"{media:<24} {len(en_base):>8} en base ({doublons} doublons), "
          f"{len(du_csv):>8} au CSV{suffixe}, {len(nouvelles):>6} insérées", flush=True)
    total += len(nouvelles)

print(f"\nTerminé : {total} URLs insérées ; {doublons_total} doublons (media,url) préexistants en base.")
conn.close()
