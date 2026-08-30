# Fenetres de TRIPLETS pour la PCA jointe (concatenee) sur trois medias : pour
# chaque mot du vocabulaire commun, on apparie les pics des trois journaux
# (meme evenement a --tol jours calendaires pres), on fixe la DATE COMMUNE au
# pic le plus fort du triplet, puis on extrait la meme fenetre de 2*demi+1
# blocs autour de cette date dans chacun des trois medias. La PCA (pca_trio.py)
# tourne ensuite sur la concatenation des trois segments.
#
# Appariement = NMS inter-medias (meme logique gloutonne que nms.py, appliquee
# au pool des trois medias) : les pics d'un mot sont parcourus par surprise
# decroissante ; un pic vivant de surprise >= --ref devient reference si chacun
# des deux autres medias a un pic (surprise >= --suiveur) a moins de --tol
# jours ; le triplet retenu supprime alors tous les pics des trois medias a
# moins d'une largeur de fenetre de la date commune (fenetres jamais
# recouvrantes pour un mot) ; une reference sans suiveurs ne supprime
# qu'elle-meme (un pic voisin un peu plus faible peut reussir a son tour).
# Le suiveur retenu par media est le plus fort dans la tolerance.
# La date commune (--centre) est celle du pic de reference (defaut), ou la
# MEDIANE des trois dates de pic — regle symetrique qui ne privilegie aucun
# media dans le centrage des fenetres.
#
# Grille (--grille) :
# - calendaire (defaut) : blocs de `pas` jours CALENDAIRES ancres sur la date
#   commune (bloc central centre dessus) — les trois segments sont synchrones,
#   les decalages entre medias restent visibles. Un bloc sans parution ou
#   quasi vide (N < vide_frac x mediane journaliere x pas) est interpole
#   lineairement (principe du nettoyage V2 de pca.py) et compte ; une fenetre
#   est ecartee si un bloc central manque ou si un segment depasse
#   --interp-max de blocs interpoles.
# - parution : blocs de `pas` jours de PARUTION du media, ancres sur le jour
#   de parution le plus proche de la date commune (grille historique — les
#   segments ne sont plus strictement synchrones d'un media a l'autre).
#
# Sortie <VOCAB_DIR>/fenetres_trio_<tag>.npz (tag = j20, 3j15, + _par) :
#   fenetres  float32 (n, 3, L)   f_t pour 10^5 par media, blocs -demi..demi
#   mot, date (commune YYYYMMDD), ref (indice du media de reference),
#   surprise (n, 3), decalage (n, 3, jours calendaires pic - date commune),
#   n_interp (n, 3), medias, pas, demi, tol, grille
# Les effectifs a reference >= 4/5/6 sont affiches pour choisir le seuil.
# Mode --solo (campagne « pics sans appariement ») : tout pic >= --ref devient
# une fenetre, sans exiger de pic dans les deux autres medias ; ceux-ci sont
# quand meme extraits autour de la date du pic, et leur pic echo (>= --suiveur
# a <= --tol jours) est enregistre quand il existe (surprise 0 sinon). Le NMS
# inter-medias est conserve : un evenement repris par plusieurs journaux ne
# donne qu'une fenetre.
#
# Usage (sur gallica) :
#   python -m rupture.fenetres_triplets --pas 1 --demi 20
#   python -m rupture.fenetres_triplets --pas 3 --demi 15
#   python -m rupture.fenetres_triplets --pas 1 --demi 20 --solo --ref 5
import argparse
import os
import time

import numpy as np
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--medias", nargs=3, default=["lemonde", "lefigaro", "ouestfrance"])
p.add_argument("--pas", type=int, default=1, help="jours par bloc (impair)")
p.add_argument("--demi", type=int, default=20, help="blocs de chaque cote du centre")
p.add_argument("--tol", type=int, default=7, help="tolerance d'appariement (jours cal.)")
p.add_argument("--grille", choices=["calendaire", "parution"], default="calendaire")
p.add_argument("--pics", default="_s3", help="suffixe des csv de pics_masse")
p.add_argument("--ref", type=float, default=4.0, help="surprise min. de la reference")
p.add_argument("--suiveur", type=float, default=3.0, help="surprise min. des suiveurs")
p.add_argument("--interp-max", type=float, default=0.5, dest="interp_max",
               help="part max. de blocs interpoles par segment")
p.add_argument("--vide-frac", type=float, default=0.1, dest="vide_frac",
               help="bloc quasi vide si N < vide_frac x mediane journaliere x pas")
p.add_argument("--centre", choices=["ref", "mediane"], default="ref",
               help="date commune : pic de reference (defaut) ou mediane des 3 dates")
p.add_argument("--solo", action="store_true",
               help="pas d'appariement requis : tout pic >= --ref devient une fenetre, "
                    "meme si les deux autres medias n'ont pas de pic (surprise 0 et "
                    "decalage 0 pour un media muet) ; le NMS inter-medias est conserve")
p.add_argument("--suffixe", default="",
               help="ajoute au tag de sortie (ex. _t3 pour une variante de tolerance)")
a = p.parse_args()
assert a.pas % 2 == 1, "pas impair attendu (bloc centrable sur la date commune)"
assert not (a.solo and a.centre == "mediane"), "centre mediane sans objet en solo"
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
L = 2 * a.demi + 1
PORTEE = L * a.pas                       # largeur d'une fenetre en jours cal.
tag = (f"{a.pas}j{a.demi}" if a.pas > 1 else f"j{a.demi}") \
    + ("_par" if a.grille == "parution" else "") \
    + ("_solo" if a.solo else "") + a.suffixe
debut_t = time.time()


def en_jours(dates):
    """YYYYMMDD -> jours depuis 1970 (int64)."""
    return (pd.to_datetime(pd.Series(dates).astype(str), format="%Y%m%d")
            .to_numpy().astype("datetime64[D]").astype(np.int64))


# 1. Series journalieres et vocabulaire commun (ordre du premier media)
series = []
for m in a.medias:
    d = np.load(f"{DOSSIER}/vocab_series_{m}.npz")
    series.append(dict(X=d["X"], N=d["N"].astype(np.int64),
                       jours=en_jours(d["dates"]), mots=d["mots"].astype(str)))
ens = set(series[0]["mots"]) & set(series[1]["mots"]) & set(series[2]["mots"])
commun = np.array([m for m in series[0]["mots"] if m in ens])
colonne = {m: j for j, m in enumerate(commun)}
debut = max(s["jours"][0] for s in series)          # periode commune aux trois
fin = min(s["jours"][-1] for s in series)
print(f"{' + '.join(a.medias)} : vocabulaire commun {len(commun)} mots, periode "
      f"commune {np.datetime64(int(debut), 'D')} -> {np.datetime64(int(fin), 'D')}, "
      f"blocs de {a.pas} j x {L}, grille {a.grille}", flush=True)

# 2. Pics des trois medias (grille de detection = celle du pas demande),
# restreints au vocabulaire commun, au seuil suiveur et a la periode commune
suffixe = "" if a.pas == 1 else f"{a.pas}j"
pics = []
for i, m in enumerate(a.medias):
    q = pd.read_csv(f"{DOSSIER}/pics_{m}{suffixe}{a.pics}.csv")
    q = q[q["mot"].isin(ens) & (q["surprise"] >= a.suiveur)]
    q["jour"] = en_jours(q["date"].to_numpy())
    q = q[(q["jour"] >= debut) & (q["jour"] <= fin)]
    q["media"] = i
    pics.append(q[["mot", "date", "jour", "surprise", "media"]])
    print(f"  {m:12s} {len(q):7d} pics utilisables ({suffixe or 'journalier'})",
          flush=True)
pics = pd.concat(pics, ignore_index=True)

# 3. NMS inter-medias par mot -> triplets (date commune, suiveurs retenus)
triplets = []            # (mot, date, ref, jour_commun, surprises, decalages)
autres = {0: (1, 2), 1: (0, 2), 2: (0, 1)}
for mot, g in pics.groupby("mot", sort=False):
    jours, surs, dates_g = [], [], []
    for i in range(3):
        gm = g[g["media"] == i].sort_values("jour")
        jours.append(gm["jour"].to_numpy())
        surs.append(gm["surprise"].to_numpy())
        dates_g.append(gm["date"].to_numpy())
    vivant = [np.ones(len(j), bool) for j in jours]
    pool = sorted(((surs[m][k], m, k) for m in range(3) for k in range(len(surs[m]))),
                  reverse=True)
    for s, m, k in pool:
        if s < a.ref:
            break                                   # pool trie : que du plus faible
        if not vivant[m][k]:
            continue
        t = jours[m][k]
        surprise = np.zeros(3, np.float32)
        jours_trio = np.zeros(3, np.int64)
        dates_trio = np.zeros(3, np.int64)
        surprise[m], jours_trio[m], dates_trio[m] = s, t, int(dates_g[m][k])
        ok = True
        for m2 in autres[m]:                        # suiveur le plus fort a <= tol
            lo = np.searchsorted(jours[m2], t - a.tol)
            hi = np.searchsorted(jours[m2], t + a.tol + 1)
            if lo == hi:
                if a.solo:                          # media muet : surprise 0,
                    jours_trio[m2] = t              # decalage 0 par convention
                    continue
                ok = False
                break
            j2 = lo + int(np.argmax(surs[m2][lo:hi]))
            surprise[m2] = surs[m2][j2]
            jours_trio[m2], dates_trio[m2] = jours[m2][j2], int(dates_g[m2][j2])
        if not ok:
            vivant[m][k] = False                    # seul le pic rejete meurt
            continue
        if a.centre == "mediane":                   # la mediane de 3 dates est
            m_c = int(np.argsort(jours_trio)[1])    # l'une des trois
        else:
            m_c = m
        t_c, date_c = int(jours_trio[m_c]), int(dates_trio[m_c])
        decalage = (jours_trio - t_c).astype(np.int16)
        triplets.append((mot, date_c, m, t_c, surprise, decalage))
        for m3 in range(3):                         # zone morte = une fenetre
            lo = np.searchsorted(jours[m3], t_c - PORTEE + 1)
            hi = np.searchsorted(jours[m3], t_c + PORTEE)
            vivant[m3][lo:hi] = False
if not triplets:
    raise SystemExit("aucun triplet apparie : verifier medias, pics et seuils")
n = len(triplets)
mot_t = np.array([t[0] for t in triplets])
date_t = np.array([t[1] for t in triplets], np.int32)
ref_t = np.array([t[2] for t in triplets], np.int8)
jour_t = np.array([t[3] for t in triplets], np.int64)
surprise_t = np.stack([t[4] for t in triplets])
decalage_t = np.stack([t[5] for t in triplets])
col_t = np.array([colonne[m] for m in mot_t])
print(f"appariement : {n} triplets ({len(pics)} pics en entree), "
      f"{time.time() - debut_t:.0f} s", flush=True)

# 4. Extraction des trois segments, blocs ancres sur la date commune
off = (np.arange(-a.demi, a.demi + 1)[:, None] * a.pas
       + (np.arange(a.pas) - a.pas // 2)[None, :])                 # (L, pas)
fenetres = np.zeros((n, 3, L), np.float32)
n_interp = np.zeros((n, 3), np.int16)
garde = np.ones(n, bool)
for i, (m, s) in enumerate(zip(a.medias, series)):
    if a.grille == "calendaire":
        # grille calendaire dense restreinte a la periode utile, N = 0 ailleurs
        cal0 = debut - PORTEE - a.pas
        ncal = fin + PORTEE + a.pas - cal0 + 1
        lignes = (s["jours"] >= cal0) & (s["jours"] < cal0 + ncal)
        idx_mots = pd.Series(range(len(s["mots"])), index=s["mots"])[commun].to_numpy()
        Xc = np.zeros((ncal, len(commun)), np.int32)
        Xc[s["jours"][lignes] - cal0] = s["X"][np.where(lignes)[0]][:, idx_mots]
        Nc = np.zeros(ncal, np.int64)
        Nc[s["jours"][lignes] - cal0] = s["N"][lignes]
        pos = jour_t - cal0
        n_median = np.median(s["N"][lignes][s["N"][lignes] > 0])
    else:
        # grille de parution du media, ancree au jour le plus proche du centre
        idx_mots = pd.Series(range(len(s["mots"])), index=s["mots"])[commun].to_numpy()
        Xc, Nc = s["X"][:, idx_mots], s["N"]
        pos = np.searchsorted(s["jours"], jour_t)
        pos = np.clip(pos, 1, len(s["jours"]) - 1)
        pos -= (jour_t - s["jours"][pos - 1]) < (s["jours"][pos] - jour_t)
        bord = (pos - a.demi * a.pas - a.pas // 2 < 0) \
            | (pos + a.demi * a.pas + a.pas // 2 >= len(s["jours"]))
        garde &= ~bord
        pos = np.clip(pos, a.demi * a.pas + a.pas // 2,
                      len(s["jours"]) - 1 - a.demi * a.pas - a.pas // 2)
        n_median = np.median(s["N"][s["N"] > 0])
    idx = pos[:, None, None] + off[None]                    # (n, L, pas)
    Xb = Xc[idx, col_t[:, None, None]].sum(axis=2, dtype=np.int64)
    Nb = Nc[idx].sum(axis=2)
    vide = Nb < a.vide_frac * n_median * a.pas              # blocs a interpoler
    f = 1e5 * Xb / np.maximum(Nb, 1)
    x = np.arange(L)
    for j in np.where(vide.any(axis=1))[0]:
        bon = ~vide[j]
        if bon.any():
            f[j, vide[j]] = np.interp(x[vide[j]], x[bon], f[j, bon])
    fenetres[:, i] = f
    n_interp[:, i] = vide.sum(axis=1)
    garde &= ~vide[:, a.demi] & (vide.mean(axis=1) <= a.interp_max)
    print(f"  {m:12s} mediane N/j {int(n_median)}, blocs interpoles "
          f"{vide.mean() * 100:.1f} %, centres vides {int(vide[:, a.demi].sum())}",
          flush=True)

ecartes = int((~garde).sum())
fenetres, mot_t, date_t, ref_t = fenetres[garde], mot_t[garde], date_t[garde], ref_t[garde]
surprise_t, decalage_t, n_interp = surprise_t[garde], decalage_t[garde], n_interp[garde]

chemin = f"{DOSSIER}/fenetres_trio_{tag}.npz"
np.savez_compressed(chemin, fenetres=fenetres, mot=mot_t, date=date_t, ref=ref_t,
                    surprise=surprise_t, decalage=decalage_t, n_interp=n_interp,
                    medias=np.array(a.medias), pas=a.pas, demi=a.demi, tol=a.tol,
                    grille=a.grille)
s_ref = surprise_t[np.arange(len(ref_t)), ref_t]
effectifs = ", ".join(f">= {s} : {int((s_ref >= s).sum())}" for s in (4, 5, 6))
print(f"FINI : {len(fenetres)} triplets gardes ({ecartes} ecartes par les filtres), "
      f"effectifs par seuil de reference ({effectifs}), "
      f"{os.path.getsize(chemin) / 1e6:.0f} Mo en {(time.time() - debut_t) / 60:.1f} min "
      f"-> {chemin}", flush=True)
