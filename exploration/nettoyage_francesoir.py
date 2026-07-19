"""Nettoyage one-shot de data/csv/francesoir.csv (défauts constatés le 11/07/2026,
extracteur corrigé le 19/07/2026 dans medias.py + extraction.py) :

- date : texte affiché « Publié le 30 septembre 2022 - 14:20 » → ISO 2022-09-30T14:20:00
  (francesoir n'expose aucune date en métadonnées, cf extraction.date_francesoir) ;
- contenu : troncature au bloc dons « L'article vous a plu ? … », premier des blocs du
  site (dons, newsletter, manifeste) que l'ancien sélecteur embarquait en fin de corps ;
- les pages /afp-afp-france/ sans article (dépêches retirées du site : titre et date
  vides, contenu = blocs du site uniquement) : contenu vidé, ids/urls listés dans
  data/backup/francesoir_sans_article_20260719.csv pour un marquage etat=5 ultérieur.

Toute ligne hors motif est écrite telle quelle et logguée, jamais devinée ; s'il y en a,
le CSV original est laissé en place (.tmp conservé pour inspection). Sinon remplacement
atomique du CSV par le fichier temporaire.

Dry-run du 19/07/2026 sur les 85 509 lignes : 83 138 dates au motif + 2 371 vides ;
83 138 contenus avec le bloc dons (1 seule occurrence) + 2 371 pages sans article.

À lancer depuis la racine, scrapping en pause :
    python -m exploration.nettoyage_francesoir
"""

import csv
import os

from scraping.extraction import date_francesoir
from scraping.stockage import COLONNES, DATA_DIR

csv.field_size_limit(10**8)

CHEMIN = DATA_DIR/"csv"/"francesoir.csv"
LISTE_SANS_ARTICLE = DATA_DIR/"backup"/"francesoir_sans_article_20260719.csv"
MARQUEUR_PROMO = "L'article vous a plu ? Il a mobilisé notre rédaction"
DEBUT_SANS_ARTICLE = "Soutenez l'indépendance de Faites un don"

dates_converties = dates_vides = tronquees = sans_article = 0
anomalies = []

with open(CHEMIN, newline="", encoding="utf-8") as src, \
     open(f"{CHEMIN}.tmp", "w", newline="", encoding="utf-8") as dst, \
     open(LISTE_SANS_ARTICLE, "w", newline="", encoding="utf-8") as vides:
    ecrivain = csv.DictWriter(dst, fieldnames=COLONNES)
    ecrivain.writeheader()
    ecrivain_vides = csv.writer(vides)
    ecrivain_vides.writerow(["id", "url"])

    for ligne in csv.DictReader(src):
        date_iso = date_francesoir(ligne["date"])
        if date_iso != ligne["date"]:
            ligne["date"] = date_iso
            dates_converties += 1
        elif not ligne["date"]:
            dates_vides += 1
        else:
            anomalies.append(f"date hors motif   id={ligne['id']} date={ligne['date'][:60]!r}")

        contenu = ligne["contenu"]
        if MARQUEUR_PROMO in contenu:
            ligne["contenu"] = contenu[:contenu.index(MARQUEUR_PROMO)].rstrip()
            tronquees += 1
        elif contenu.startswith(DEBUT_SANS_ARTICLE):
            ligne["contenu"] = ""
            sans_article += 1
            ecrivain_vides.writerow([ligne["id"], ligne["url"]])
        else:
            anomalies.append(f"contenu hors motif id={ligne['id']} fin={contenu[-80:]!r}")

        ecrivain.writerow(ligne)

print(f"dates converties  : {dates_converties} | vides (laissées) : {dates_vides}")
print(f"contenus tronqués : {tronquees} | sans article (vidés) : {sans_article}")
print(f"anomalies         : {len(anomalies)}")
for a in anomalies[:50]:
    print(" ", a)

if anomalies:
    print(f"CSV original laissé en place, {CHEMIN}.tmp conservé pour inspection")
else:
    os.replace(f"{CHEMIN}.tmp", CHEMIN)
    print(f"remplacé : {CHEMIN}")
