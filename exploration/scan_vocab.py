# Recensement du vocabulaire unigram d'un media (generalisation de
# scan_vocab_lemonde.py pour la campagne PCA) : une ligne (mot, jours_actifs,
# total) par token, ecrite au fil de l'eau dans un CSV. Scan complet par
# tranches de w1 — la PK (w1, date) fait de chaque tranche un parcours
# d'index borne, jamais une requete geante silencieuse.
# Une annee de debut peut etre donnee pour restreindre le recensement a une
# periode (le classement par frequence change : le vocabulaire recent remonte,
# cf. vocab_lemonde_2000.py). La sortie porte alors l'annee au lieu du suffixe
# « unigram ».
# Usage (sur gallica) : python -m exploration.scan_vocab [media] [annee_debut]
import csv
import sqlite3
import sys
import time

media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
annee = int(sys.argv[2]) if len(sys.argv) > 2 else None
DB = f"/data/elias/stage-mids/data/corpus/{media}_ngram.db"
SORTIE = f"/data/elias/stage-mids/data/vocab_{media}_{annee or 'unigram'}.csv"
PERIODE = "" if annee is None else f" AND u.date >= {annee * 10000 + 101}"
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
            f"WHERE u.w1 BETWEEN ? AND ?{PERIODE} GROUP BY u.w1",
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
