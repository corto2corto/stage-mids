"""Écriture des résultats : CSV de sortie + mise à jour de l'état en base.

États d'une URL dans la table `urls` :
- 0 : à scraper
- 1 : échec (pas de HTML récupéré)
- 2 : scrapée avec succès
"""

import csv
from scraping import extraction
from scraping.config import DATA_DIR
from scraping.paywall import est_bloque

# éventuellement à supprimer.
COLONNES = ["id", "url", "titre", "auteur", "date", "section", "free", "contenu"]


def ecriture_csv(media, id, url, html):
    """Extrait les métadonnées, écrit dans le CSV et retourne l'état (1 ou 2)."""
    meta = extraction.extraire(media, html)
    if est_bloque(meta["contenu"]):
        return 1
    chemin = DATA_DIR/"csv"/f"{media}.csv"
    with open(chemin, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([id, url, meta["titre"], meta["auteur"], meta["date"], meta["section"], meta["free"], meta["contenu"]])
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
