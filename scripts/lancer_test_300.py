"""Lance le pipeline complet, de bout en bout, sur un nombre borné d'URLs.

But : un premier test grandeur nature. On réutilise les briques de `scraping/`
sans y toucher :
  - un Firefox par média est ouvert UNE fois, puis réutilisé d'une vague à
    l'autre (ce qui amortit le téléchargement des listes uBlock) ;
  - chaque vague traite une URL par média : scraping, extraction, contrôle du
    paywall, écriture du CSV et mise à jour de l'état en base ;
  - on enchaîne les vagues jusqu'à CIBLE URLs (300 par défaut).

Le run est interruptible : l'état est commité vague par vague, et les URLs non
traitées restent à etat=0 — un relancement reprend tout seul là où on s'est
arrêté.

Pré-requis (sur le serveur) : la base et les CSV de sortie doivent déjà exister
(`scripts/2_creer_bdd.py`, `scripts/3_importer_csv.py`, `scripts/creer_csv.py`).

    python -m scripts.lancer_test_300          # 300 URLs
    python -m scripts.lancer_test_300 500      # ou un autre total
"""

import sqlite3
import sys
import time

from scraping.batch import new_batch
from scraping.navigateur import configurer_ublock
from scraping.pipeline import ouvrir_multi_firefox, scraper_batch
from scraping.stockage import DATA_DIR, ecriture_csv, maj_bdd

CIBLE_DEFAUT = 300   # nombre d'URLs à traiter au total


def traiter_vague(conn, batch, navigateurs):
    """Scrape une vague, écrit CSV + état, renvoie le nombre d'URLs traitées.

    Un échec de scraping (html=None) ou d'extraction laisse l'URL en etat=1 :
    l'article n'est pas écrit dans le CSV mais l'URL est marquée comme traitée.
    Une vague = une seule transaction (commit groupé en fin de vague).
    """
    # On ne scrape que les médias présents dans cette vague (un navigateur peut
    # rester ouvert mais inactif si son média n'a plus d'URL à etat=0).
    actifs = {media: navigateurs[media] for media in batch if media in navigateurs}
    resultats = scraper_batch(batch, actifs)

    for media, (id, url, html) in resultats.items():
        if html is None:
            etat = 1
            print(f"  {media:<24} id={id}  ECHEC (pas de HTML)")
        else:
            try:
                etat = ecriture_csv(media, id, url, html)
            except Exception as e:   # un article mal formé ne doit pas tuer le run
                etat = 1
                print(f"  {media:<24} id={id}  ECHEC extraction ({type(e).__name__})")
            else:
                marque = "succès" if etat == 2 else "bloqué/vide"
                print(f"  {media:<24} id={id}  etat={etat} ({marque})")
        maj_bdd(conn, id, etat)

    conn.commit()
    return len(resultats)


def main(cible=CIBLE_DEFAUT):
    debut = time.time()

    configurer_ublock()
    conn = sqlite3.connect(DATA_DIR / "urls.db")

    # Premier batch : il donne l'ensemble des médias encore à traiter, donc ceux
    # pour lesquels il faut ouvrir un navigateur (aucun média ne peut en gagner
    # en cours de route).
    batch = new_batch()
    if not batch:
        print("Aucune URL à etat=0 — rien à faire.")
        conn.close()
        return

    print(f"Ouverture d'un Firefox pour : {', '.join(sorted(batch))}")
    navigateurs = ouvrir_multi_firefox(batch)

    traitees = 0
    vague = 0
    try:
        while batch and traitees < cible:
            # Dernière vague : ne pas dépasser la cible (on rogne le batch).
            restant = cible - traitees
            if len(batch) > restant:
                batch = dict(list(batch.items())[:restant])

            vague += 1
            print(f"\n=== Vague {vague}  ({traitees}/{cible} URLs traitées) ===")
            traitees += traiter_vague(conn, batch, navigateurs)

            batch = new_batch()
    finally:
        for driver in navigateurs.values():
            driver.quit()
        conn.close()

    print(f"\n{traitees} URLs traitées en {time.time() - debut:.1f}s.")
    print("Évaluation des résultats : python -m scripts.suivi echecs")


if __name__ == "__main__":
    cible = int(sys.argv[1]) if len(sys.argv) > 1 else CIBLE_DEFAUT
    main(cible)
