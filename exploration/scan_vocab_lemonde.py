# Recensement du vocabulaire unigram Le Monde (phase 3, dataset de sauts) :
# une ligne (mot, jours_actifs, total) par token, ecrite au fil de l'eau dans
# un CSV. Scan complet par tranches de w1 — la PK (w1, date) fait de chaque
# tranche un parcours d'index borne, jamais une requete geante silencieuse.
# Les tranches sont inegales (les petits ids = mots de 1944, tres denses) :
# la progression s'affiche tranche par tranche avec duree et debit.
import csv
import sqlite3
import time

DB = "/data/elias/stage-mids/data/corpus/lemonde_ngram.db"
SORTIE = "/data/elias/stage-mids/data/vocab_lemonde_unigram.csv"
PAS = 5_000

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
max_id = conn.execute("SELECT MAX(id) FROM token").fetchone()[0]
n_tranches = (max_id - 1) // PAS + 1
debut_scan = time.time()
n_mots = 0
n_lignes = 0

with open(SORTIE, "w", newline="") as f:
    ecrivain = csv.writer(f)
    ecrivain.writerow(["mot", "jours_actifs", "total"])
    for i, borne in enumerate(range(1, max_id + 1, PAS), start=1):
        t0 = time.time()
        lignes = conn.execute(
            "SELECT t.word, COUNT(*), SUM(u.n) FROM unigram u JOIN token t ON t.id = u.w1 "
            "WHERE u.w1 BETWEEN ? AND ? GROUP BY u.w1",
            (borne, borne + PAS - 1)).fetchall()
        ecrivain.writerows(lignes)
        f.flush()
        duree = time.time() - t0
        n_mots += len(lignes)
        n_lignes += sum(l[1] for l in lignes)
        ecoule = time.time() - debut_scan
        print(f"[{i}/{n_tranches}] w1 {borne}-{min(borne + PAS - 1, max_id)} : "
              f"{len(lignes)} mots en {duree:.1f} s | cumul {n_mots} mots, "
              f"{n_lignes / 1e6:.0f} M lignes lues, {ecoule / 60:.1f} min", flush=True)
        if duree > 300:
            print(f"ATTENTION : tranche anormalement longue ({duree:.0f} s)", flush=True)

print(f"FINI : {n_mots} mots -> {SORTIE} en {(time.time() - debut_scan) / 60:.1f} min", flush=True)
