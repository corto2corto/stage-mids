# Vocabulaire par fenetres glissantes (etude d'une alternative au top global
# de masse.py, qui classe par jours actifs sur toute l'archive et exclut donc
# tout mot recent — « macron » : 4 051 jours actifs contre une coupe a 7 391).
# Fenetres d'UN AN glissant par pas de 6 mois : chaque jour est agrege par
# semestre, une fenetre = deux semestres consecutifs, donc une seule passe sur
# unigram suffit (les jours actifs d'une fenetre = somme des deux semestres,
# exact car la PK (w1, date) garantit une ligne par jour et par mot).
# La largeur est parametrable en semestres (defaut 2 = un an, qui neutralise
# le vocabulaire saisonnier ; 1 = fenetres de 6 mois, pour comparer) ; la
# sortie d'une largeur non standard porte un suffixe _<L>sem.
# Dans chaque fenetre, top-K par jours actifs (memes exclusions que masse.py :
# mots outils, chiffres, mots d'une lettre) via un tas de taille K ; la sortie
# est l'UNION des tops : un mot y entre des qu'il compte quelque part.
# Les fenetres de bord (premiere et derniere) sont partielles : les rangs y
# restent comparables, tous les mots ont la meme fenetre tronquee.
# Scan complet par tranches de w1, parcours d'index borne comme scan_vocab.py.
# Usage (sur gallica) : python -m exploration.scan_vocab_fenetre [media] [K] [largeur]
# Sortie : data/vocab_<media>_fenetres.csv — mot, fenetres (nb de tops ou il
# figure), ja_max (meilleurs jours actifs de fenetre), premiere, derniere.
import csv
import heapq
import sqlite3
import sys
import time

from scripts.tokenisation import MOTS_OUTILS

media = sys.argv[1] if len(sys.argv) > 1 else "lemonde"
K = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
LARGEUR = int(sys.argv[3]) if len(sys.argv) > 3 else 2  # en semestres
DB = f"/data/elias/stage-mids/data/corpus/{media}_ngram.db"
SORTIE = (f"/data/elias/stage-mids/data/vocab_{media}_fenetres"
          f"{'' if LARGEUR == 2 else f'_{LARGEUR}sem'}.csv")
PAS = 5_000
STOP = set(MOTS_OUTILS)

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
max_id = conn.execute("SELECT MAX(id) FROM token").fetchone()[0]
n_tranches = (max_id - 1) // PAS + 1
debut_scan = time.time()
n_mots = 0
tops = {}  # semestre de debut de fenetre -> tas [(jours_actifs, mot)] de taille K

for i, borne in enumerate(range(1, max_id + 1, PAS), start=1):
    t0 = time.time()
    lignes = conn.execute(
        "SELECT t.word, (u.date/10000)*2 + ((u.date/100)%100 > 6), COUNT(*) "
        "FROM unigram u JOIN token t ON t.id = u.w1 "
        "WHERE u.w1 BETWEEN ? AND ? GROUP BY u.w1, 2",
        (borne, borne + PAS - 1)).fetchall()
    # jours actifs par (mot, semestre), puis par fenetre = 2 semestres
    par_mot = {}
    for mot, sem, ja in lignes:
        if len(mot) > 1 and mot not in STOP and not mot[0].isdigit():
            par_mot.setdefault(mot, {})[sem] = ja
    for mot, sems in par_mot.items():
        for s in range(min(sems) - LARGEUR + 1, max(sems) + 1):  # fenetres touchees
            ja_f = sum(sems.get(s + j, 0) for j in range(LARGEUR))
            tas = tops.setdefault(s, [])
            if len(tas) < K:
                heapq.heappush(tas, (ja_f, mot))
            elif ja_f > tas[0][0]:
                heapq.heapreplace(tas, (ja_f, mot))
    n_mots += len(par_mot)
    print(f"[{i}/{n_tranches}] w1 {borne}-{min(borne + PAS - 1, max_id)} : "
          f"{len(par_mot)} mots en {time.time() - t0:.1f} s | cumul {n_mots} mots, "
          f"{len(tops)} fenetres, {(time.time() - debut_scan) / 60:.1f} min", flush=True)

# Union des tops : pour chaque mot, dans combien de fenetres il figure et ou
info = {}  # mot -> [fenetres, ja_max, premiere, derniere]
for s in sorted(tops):
    for ja_f, mot in tops[s]:
        if mot in info:
            info[mot][0] += 1
            info[mot][1] = max(info[mot][1], ja_f)
            info[mot][3] = s
        else:
            info[mot] = [1, ja_f, s, s]

etiquette = lambda s: f"{s // 2}-{'01' if s % 2 == 0 else '07'}"
with open(SORTIE, "w", newline="") as f:
    ecrivain = csv.writer(f)
    ecrivain.writerow(["mot", "fenetres", "ja_max", "premiere", "derniere"])
    for mot, (n, ja, p, d) in sorted(info.items(), key=lambda kv: (-kv[1][0], -kv[1][1])):
        ecrivain.writerow([mot, n, ja, etiquette(p), etiquette(d)])

coupes = [tops[s][0][0] for s in sorted(tops)]
print(f"FINI : union de {len(info)} mots sur {len(tops)} fenetres "
      f"({etiquette(min(tops))} -> {etiquette(max(tops))}), coupes de {min(coupes)} "
      f"a {max(coupes)} jours actifs -> {SORTIE} "
      f"en {(time.time() - debut_scan) / 60:.1f} min", flush=True)
