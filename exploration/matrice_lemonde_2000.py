# Matrice de correlation mot x mot du Monde sur 2000-2025 (chantier A1).
# Repond a « quels mots parlent des memes jours ». Pas de valeurs propres ici :
# la matrice se lit ligne par ligne (le voisinage d'un mot).
#
# Les trois pieges de volume, et leur parade :
#  1. volume du mot (guerre >> francisco) -> on fait une CORRELATION, pas une
#     covariance : chaque mot est ramene a un ecart-type de 1, tous pesent pareil.
#  2. volume du jour (journal epais = tous les mots montent) -> l'attendu du jour
#     est mu_w * N_t, donc le residu ne depend plus de l'epaisseur du journal.
#  3. bruit de comptage des mots rares (correlations tirees vers 0) -> plancher de
#     vocabulaire : au top-600, fiabilite m/(m+r) ~ 0,7-0,9 sur 2000-2025 (corpus
#     plus dense qu'en moyenne 1944-2025), atenuation limitee.
#
# Selection du vocabulaire : top-K par occurrences sur la periode, parmi les
# noms / noms propres / adjectifs (vocab_categories.csv, Lexique + spaCy), moins
# un residu de mots vides mal etiquetes par le classifieur grammatical (mesure a
# l'oeil sur le top-800 reel : « ans, fois, mois, cours, part, certains, mieux,
# mis, pris, declare »…) et les noms de jours/mois (lundi, mars…) qui sont des
# noms communs valides mais purement calendaires, sans charge thematique. Les
# mots absents de vocab_categories.csv sont GARDES (sinon on perd le vocabulaire
# recent : immigration, ukraine, macron, covid sont sous la coupe du recensement
# 1944-2025 existant, cf. vocab_lemonde_2000.py).
#
# Residu : Pearson (X - mu*N) / sqrt(mu*N), winsorise a +/- CLIP (sans quoi une
# poignee de journees geantes — mars 2020 — piloterait les correlations).
#
# Usage (sur gallica) : python -m exploration.matrice_lemonde_2000 [K]
import os
import sqlite3
import sys
import time

import numpy as np
import pandas as pd

from scripts.tokenisation import MOTS_OUTILS

K = int(sys.argv[1]) if len(sys.argv) > 1 else 600
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
ICI = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = os.path.join(ICI, "..", "campagne_pca", "data", "vocab_categories.csv")
DEBUT, FIN = 20000101, 20251231
N_MIN = 5_000   # jours a corpus quasi vide ecartes (convention V2 de rupture/pca.py)
CLIP = 8.0
GARDEES = ("nom", "nom_propre", "adj")
TESTS = ("immigration", "chômage", "guerre", "climat", "covid", "hôpital")

# noms de jours/mois : calendaires, pas thematiques
TEMPOREL = set("""
lundi mardi mercredi jeudi vendredi samedi dimanche
janvier février fevrier mars avril mai juin juillet août aout septembre
octobre novembre décembre decembre
""".split())
# residu de mots vides / meta-discursifs / quantifieurs qui passent le filtre
# grammatical (verifie a l'oeil sur le top-800 candidats reel, 1944-2025 :
# adjectifs/participes generiques mal classes, quantifieurs, superlatifs de
# comparaison narrative plutot que de contenu)
VIDE = set("""
ans an fois mois annee années année cours part temps unis certains mis pris
déclaré declare mieux reste doute effet cas fin debut début plan
autre autres ainsi sorte façon facon genre type manière maniere
plusieurs quatre cinq six sept huit neuf dix onze douze cent mille
seul seule seuls seules propre propres meme mêmes tel telle
grand grande grands grandes petit petite petits petites nouveau nouvelle
nouveaux nouvelles dernier derniere dernière derniers dernieres
premier première premiere premiers premieres deuxieme deuxième troisième
seconde second bon bonne belle beau vrai
""".split())
# locutions vagues / mots-outils grammaticalises restant dans nom/adj : sens
# spatial-metaphorique ou meta-narratif, quasi jamais tete d'un theme (repere
# a l'oeil sur le top-800 reel — Corto, 14/08/2026 : « éliminer porte, mal,
# suite etc., tolerer 10-20 % max de ce genre de mot »)
LOCUTION = set("""
devant face côté moment mise porte mal soir passé suite sens coup vue tête
main mains bout sein terme termes cadre sort fond dessus travers propos
quant outre part parti donné donne données vu vue longue long large haut
bas gros petit noir blanc rouge simple double triple demi total ensemble
milieu derrière niveau ligne série forme point points chose choses
matin midi nuit tard veille durant retour départ passage voie chemin
manque appel note titre exemple raison raisons ajouté ajoute estime
indiqué chargé compris connu réalisé signé nommé tenu voulu venu trouvé
choisi réussi entendu atteint ouvert continue précise
""".split())
# tokens corrompus de tokenisation (« uvre » = OEUVRE mal decoupe, etc.) et
# verbes a l'infinitif/substantives mal classes par le classifieur grammatical
RESIDU = set("""
uvre mm ur dû vis né vite
savoir donner parler aller sortir porter devenir vivre laisse lire
""".split())

debut = time.time()

# 1. Selection du vocabulaire sur la periode
v = pd.read_csv(f"{DOSSIER}/vocab_lemonde_2000.csv", dtype={"mot": str}, keep_default_na=False)
avant = len(v)
v = v[~v["mot"].isin(set(MOTS_OUTILS))]
v = v[~v["mot"].str.match(r"[0-9]")]
v = v[v["mot"].str.len() > 1]
v = v[~v["mot"].str.contains("'")]   # formes elidees residuelles : l'origine, n'aurait
for liste in (TEMPOREL, VIDE, LOCUTION, RESIDU):
    v = v[~v["mot"].isin(liste)]
apres_listes = len(v)
cat = pd.read_csv(CATEGORIES, dtype={"mot": str}, keep_default_na=False
                  ).set_index("mot")["categorie"]
c = v["mot"].map(cat)
v = v[c.isin(GARDEES) | c.isna()]
v = v.sort_values("total", ascending=False).head(K)
inconnus = int(v["mot"].map(cat).isna().sum())
print(f"vocabulaire : {avant} mots recenses -> {apres_listes} apres listes de rejet "
      f"-> top-{K} retenu ({inconnus} hors table de categories, gardes) ; "
      f"du plus frequent « {v['mot'].iloc[0]} » ({v['total'].iloc[0]} occ.) "
      f"au dernier « {v['mot'].iloc[-1]} » ({v['total'].iloc[-1]} occ.)", flush=True)

# 2. Axe temps et ids des tokens
conn = sqlite3.connect(f"file:{DOSSIER}/corpus/lemonde_ngram.db?mode=ro", uri=True)
t = pd.read_sql_query("SELECT date, total FROM total_unigram WHERE date BETWEEN ? AND ? "
                      "ORDER BY date", conn, params=(DEBUT, FIN))
dates = t["date"].to_numpy(np.int64)
N = t["total"].to_numpy(np.float64)
mots = v["mot"].to_numpy().astype(str)
colonne = {m: j for j, m in enumerate(mots)}
tok = pd.read_sql_query("SELECT id, word FROM token", conn)
tok = tok[tok["word"].isin(colonne)]
colmap = np.full(int(tok["id"].max()) + 1, -1, np.int32)
colmap[tok["id"].to_numpy()] = [colonne[w] for w in tok["word"]]
ids = np.sort(tok["id"].to_numpy())
print(f"{len(dates)} jours de parution, {len(ids)} ids a lire", flush=True)

# 3. Une passe sur unigram par tranches d'ids
X = np.zeros((len(dates), len(mots)), np.int32)
PAS = 500
for i in range(0, len(ids), PAS):
    tranche = ids[i:i + PAS]
    df = pd.read_sql_query(
        f"SELECT w1, date, n FROM unigram WHERE w1 IN ({','.join(map(str, tranche))}) "
        "AND date BETWEEN ? AND ?", conn, params=(DEBUT, FIN))
    lignes = np.searchsorted(dates, df["date"].to_numpy())
    np.add.at(X, (lignes, colmap[df["w1"].to_numpy()]), df["n"].to_numpy())
    print(f"[{i // PAS + 1}/{(len(ids) - 1) // PAS + 1}] {time.time() - debut:.0f} s", flush=True)

# 4. Nettoyage des jours quasi vides, puis residus
garde = N >= N_MIN
print(f"{int((~garde).sum())} jours a moins de {N_MIN} mots ecartes", flush=True)
X, N, dates = X[garde], N[garde], dates[garde]
mu = X.sum(axis=0) / N.sum()
attendu = np.outer(N, mu)
R = (X - attendu) / np.sqrt(attendu)
n_clip = int((np.abs(R) > CLIP).sum())
print(f"residus : {n_clip} valeurs winsorisees a +/-{CLIP} "
      f"({100 * n_clip / R.size:.3f} %), max avant clip {np.abs(R).max():.0f}", flush=True)
R = np.clip(R, -CLIP, CLIP)

# 5. La matrice
C = np.corrcoef(R, rowvar=False)
hors_diag = C[~np.eye(len(C), dtype=bool)]
print(f"\nmatrice {C.shape[0]} x {C.shape[0]} | correlation moyenne "
      f"{hors_diag.mean():+.4f} (force du mode commun) | "
      f"quantiles 1/50/99 % : {np.percentile(hors_diag, 1):+.3f} / "
      f"{np.percentile(hors_diag, 50):+.3f} / {np.percentile(hors_diag, 99):+.3f} | "
      f"bruit attendu sur un coefficient : {1 / np.sqrt(len(dates)):.3f}", flush=True)

np.savez_compressed(f"{DOSSIER}/correlation_lemonde_2000_top{K}.npz",
                    C=C.astype(np.float32), mots=mots, mu=mu, dates=dates, N=N)

# 6. Controle a l'oeil : le voisinage de quelques mots
for mot in TESTS:
    if mot not in colonne:
        print(f"\n{mot} : hors du top-{K}", flush=True)
        continue
    j = colonne[mot]
    ordre = np.argsort(-C[j])
    voisins = [f"{mots[i]} {C[j, i]:.2f}" for i in ordre if i != j][:20]
    print(f"\n{mot} ({mu[j] * 1e5:.1f} occ. / 100 000 mots)\n  " + ", ".join(voisins), flush=True)

print(f"\nFINI en {(time.time() - debut) / 60:.1f} min -> "
      f"correlation_lemonde_2000_top{K}.npz", flush=True)
