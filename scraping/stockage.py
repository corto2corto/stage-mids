"""Écriture des résultats : CSV de sortie + mise à jour de l'état en base.

États d'une URL dans la table `urls` :
- 0 : à scraper
- 1 : échec (retenté une fois quand le média n'a plus de nouveautés, cf batch.prochaine_url)
- 2 : scrapée avec succès
- 3 : déjà couverte par le corpus historique (posé par le script de dédup, hors pipeline)
- 4 : échec confirmé (retenté et re-échoué : plus jamais repris)
- 5 : hors corpus (pages de service, média en pause…) — posé à la main, jamais scrapé
"""

import csv
import os
from pathlib import Path

from scraping import extraction
from scraping.paywall import est_bloque

# Emplacement des données (base urls.db + CSV de sortie). Surchargeable par
# STAGE_DATA_DIR pour lancer le pipeline sur une base de test isolée, sans
# toucher la prod. batch.py et pipeline.py importent ce DATA_DIR.
DATA_DIR = Path(os.environ.get("STAGE_DATA_DIR", "/data/elias/stage-mids/data"))

COLONNES = ["id", "url", "titre", "auteur", "date", "section", "free", "contenu"]


def ecriture_csv(media, id, url, html):
    """Extrait les métadonnées, écrit dans le CSV et retourne l'état (1 ou 2)."""
    meta = extraction.extraire(media, html)
    if est_bloque(meta["contenu"]):
        return 1
    chemin = DATA_DIR/"csv"/f"{media}.csv"
    nouveau = not chemin.exists() or chemin.stat().st_size == 0
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLONNES)
        if nouveau:
            writer.writeheader()
        writer.writerow({"id": id, "url": url, **meta})
    return 2


def maj_bdd(conn, id, etat=2):
    """Met à jour l'état d'une URL. Le commit est géré par l'appelant (par batch)."""
    conn.execute("UPDATE urls SET etat = ? WHERE id = ?", (etat, id))


if __name__ == "__main__":
    import sys

    from scraping.extraction import extraire_url

    media, url = sys.argv[1], sys.argv[2]
    meta = extraire_url(media, url)
    etat = 1 if est_bloque(meta["contenu"]) else 2

    print(f"état : {etat} ({'BLOQUÉ → non écrit' if etat == 1 else 'OK → serait écrit'})")
    print("ligne CSV (DRY-RUN, rien n'est écrit) :")
    ligne = ["?", url, meta["titre"], meta["auteur"], meta["date"], meta["section"], meta["free"], meta["contenu"][:150] + "…"]
    for col, val in zip(COLONNES, ligne):
        print(f"  {col:8}: {val}")
