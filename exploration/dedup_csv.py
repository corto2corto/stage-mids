"""Dédoublonnage one-shot d'un CSV média : lignes en double quand une même URL a été
scrapée plusieurs fois (constat francesoir du 19/07/2026 : 10 ids, 15 lignes en trop,
toutes strictement identiques à leur première occurrence).

On garde la première ligne de chaque id et on supprime les répétitions strictement
identiques ; un doublon qui diffère de la première ligne est gardé et loggué, jamais
deviné. Réécriture via .tmp puis remplacement atomique — faire une sauvegarde cp avant,
et ne lancer que si le média n'est pas en cours de scrapping (sinon lignes perdues).

    python -m exploration.dedup_csv francesoir
"""

import csv
import os
import sys

from scraping.stockage import COLONNES, DATA_DIR

csv.field_size_limit(10**8)

CHEMIN = DATA_DIR/"csv"/f"{sys.argv[1]}.csv"

gardees = supprimees = 0
empreintes = {}   # id -> empreinte de la première ligne (pas la ligne : trop de RAM)
anomalies = []

with open(CHEMIN, newline="", encoding="utf-8") as src, \
     open(f"{CHEMIN}.tmp", "w", newline="", encoding="utf-8") as dst:
    ecrivain = csv.DictWriter(dst, fieldnames=COLONNES)
    ecrivain.writeheader()
    for ligne in csv.DictReader(src):
        empreinte = hash(tuple(ligne[c] for c in COLONNES))
        premiere = empreintes.get(ligne["id"])
        if premiere is None:
            empreintes[ligne["id"]] = empreinte
            ecrivain.writerow(ligne)
            gardees += 1
        elif empreinte == premiere:
            supprimees += 1
        else:
            anomalies.append(f"id={ligne['id']} : doublon NON identique, gardé")
            ecrivain.writerow(ligne)
            gardees += 1

print(f"gardées : {gardees} | doublons identiques supprimés : {supprimees}")
print(f"anomalies : {len(anomalies)}")
for a in anomalies[:50]:
    print(" ", a)

os.replace(f"{CHEMIN}.tmp", CHEMIN)
print(f"remplacé : {CHEMIN}")
