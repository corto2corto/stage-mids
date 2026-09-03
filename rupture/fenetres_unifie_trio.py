# Fenetres de trio V2 : les dates viennent du CORPUS UNIFIE, pas d'un
# appariement entre les trois journaux. Pour chaque pic unifie garde par le NMS
# (campagne_pca/data/pics_unifie/pics_unifie<3j>_bnb_nms.csv, surprise >= --seuil),
# on extrait la meme fenetre de 2*demi+1 blocs calendaires autour de sa date
# dans chacun des trois medias (grille calendaire ancree sur la date, blocs
# vides interpoles — meme mecanique que fenetres_triplets.py), puis la PCA
# tourne sur la concatenation des trois segments z-scores (rejouee dans le qmd).
#
# Pas d'exigence de pic dans les trois titres : un pic unifie peut etre porte
# par d'autres medias, un des trois peut etre muet. Deux filtres :
# - NMS de largeur de fenetre par mot (le NMS unifie a une portee de 31 j,
#   plus courte qu'une fenetre ±20 j) : fenetres jamais recouvrantes ;
# - segment PLAT (ecart-type nul sur la fenetre, le mot n'apparait pas) :
#   la fenetre est ecartee (le z-score n'a pas de sens sur une constante).
# Echo : pour chaque media, son pic propre le plus fort (pics_<media>_s3, surprise
# >= --suiveur) a moins de --tol jours de la date unifiee, surprise 0 sinon.
#
# Sortie <VOCAB_DIR>/fenetres_trioV2_<tag>.npz (tag = j20, 3j15) :
#   fenetres float32 (n, 3, L)   f_t pour 10^5 par media, blocs -demi..demi
#   mot, date (YYYYMMDD du pic unifie), surprise (pic unifie), X_t, N_t,
#   echo (n, 3 surprise propre), decalage (n, 3 jours pic propre - date),
#   n_interp (n, 3), medias, pas, demi, tol, seuil, n_plat, n_nms
# Usage (sur gallica) :
#   python -m rupture.fenetres_unifie_trio --pas 1 --demi 20
#   python -m rupture.fenetres_unifie_trio --pas 3 --demi 15
import argparse
import os
import time

import numpy as np
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--medias", nargs=3, default=["lemonde", "lefigaro", "ouestfrance"])
p.add_argument("--pas", type=int, default=1, help="jours par bloc (impair)")
p.add_argument("--demi", type=int, default=20, help="blocs de chaque cote du centre")
p.add_argument("--seuil", type=float, default=5.0, help="surprise min. du pic unifie")
p.add_argument("--tol", type=int, default=7, help="tolerance de l'echo (jours cal.)")
p.add_argument("--suiveur", type=float, default=3.0, help="surprise min. d'un echo")
p.add_argument("--interp-max", type=float, default=0.5, dest="interp_max",
               help="part max. de blocs interpoles par segment")
p.add_argument("--vide-frac", type=float, default=0.1, dest="vide_frac",
               help="bloc quasi vide si N < vide_frac x mediane journaliere x pas")
p.add_argument("--suffixe", default="", help="ajoute au tag de sortie")
a = p.parse_args()
assert a.pas % 2 == 1, "pas impair attendu (bloc centrable sur la date)"
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
PICS_UNIFIE = os.path.join(os.path.dirname(__file__), "..", "campagne_pca", "data",
                           "pics_unifie")
L = 2 * a.demi + 1
PORTEE = L * a.pas                       # largeur d'une fenetre en jours cal.
suffixe = "" if a.pas == 1 else f"{a.pas}j"
tag = (f"{a.pas}j{a.demi}" if a.pas > 1 else f"j{a.demi}") + a.suffixe
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
      f"blocs de {a.pas} j x {L}", flush=True)

# 2. Pics unifies gardes par le NMS, au seuil, dans le vocabulaire commun et la
# periode commune (une fenetre entiere doit tenir dans la periode)
u = pd.read_csv(f"{PICS_UNIFIE}/pics_unifie{suffixe}_bnb_nms.csv")
n_total = len(u)
u = u[(u["supprime_nms"] == 0) & (u["surprise"] >= a.seuil)]
n_seuil = len(u)
u = u[u["mot"].isin(ens)].copy()
u["jour"] = en_jours(u["date"].to_numpy())
u = u[(u["jour"] - PORTEE // 2 >= debut) & (u["jour"] + PORTEE // 2 <= fin)]
print(f"pics unifies ({suffixe or 'journalier'}) : {n_total} lus, {n_seuil} gardes par "
      f"le NMS a surprise >= {a.seuil:g}, {len(u)} dans le vocabulaire commun et la "
      f"periode", flush=True)

# 3. NMS de largeur de fenetre par mot : par surprise decroissante, un pic
# garde tue ses voisins a moins d'une fenetre (fenetres jamais recouvrantes)
u = u.sort_values("surprise", ascending=False).reset_index(drop=True)
garde_nms = np.ones(len(u), bool)
for mot, g in u.groupby("mot", sort=False):
    idx, jours = g.index.to_numpy(), g["jour"].to_numpy()   # ordre surprise decr.
    vivant = np.ones(len(idx), bool)
    for k in range(len(idx)):
        if vivant[k]:
            vivant &= np.abs(jours - jours[k]) >= PORTEE
            vivant[k] = True
    garde_nms[idx] = vivant
n_nms = int((~garde_nms).sum())
u = u[garde_nms].sort_values(["mot", "jour"]).reset_index(drop=True)
n = len(u)
mot_t, date_t = u["mot"].to_numpy(str), u["date"].to_numpy(np.int32)
jour_t = u["jour"].to_numpy(np.int64)
surprise_t = u["surprise"].to_numpy(np.float32)
X_t, N_t = u["X_t"].to_numpy(np.int64), u["N_t"].to_numpy(np.int64)
col_t = np.array([colonne[m] for m in mot_t])
print(f"NMS largeur de fenetre ({PORTEE} j) : {n_nms} pics ecartes, {n} fenetres a "
      f"extraire, {time.time() - debut_t:.0f} s", flush=True)

# 4. Echo par media : pic propre le plus fort a <= tol jours de la date unifiee
echo = np.zeros((n, 3), np.float32)
decalage = np.zeros((n, 3), np.int16)
for i, m in enumerate(a.medias):
    q = pd.read_csv(f"{DOSSIER}/pics_{m}{suffixe}_s3.csv")
    q = q[q["mot"].isin(ens) & (q["surprise"] >= a.suiveur)]
    q["jour"] = en_jours(q["date"].to_numpy())
    par_mot = {mot: (g["jour"].to_numpy(), g["surprise"].to_numpy())
               for mot, g in q.sort_values("jour").groupby("mot", sort=False)}
    for k in range(n):
        if mot_t[k] not in par_mot:
            continue
        jours, surs = par_mot[mot_t[k]]
        lo = np.searchsorted(jours, jour_t[k] - a.tol)
        hi = np.searchsorted(jours, jour_t[k] + a.tol + 1)
        if lo < hi:
            j = lo + int(np.argmax(surs[lo:hi]))
            echo[k, i], decalage[k, i] = surs[j], jours[j] - jour_t[k]
    print(f"  {m:12s} echo present dans {(echo[:, i] > 0).mean() * 100:.1f} % des "
          f"fenetres", flush=True)

# 5. Extraction des trois segments, blocs calendaires ancres sur la date
off = (np.arange(-a.demi, a.demi + 1)[:, None] * a.pas
       + (np.arange(a.pas) - a.pas // 2)[None, :])                 # (L, pas)
fenetres = np.zeros((n, 3, L), np.float32)
n_interp = np.zeros((n, 3), np.int16)
garde = np.ones(n, bool)
plat = np.zeros((n, 3), bool)
for i, (m, s) in enumerate(zip(a.medias, series)):
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
    plat[:, i] = f.std(axis=1) == 0
    garde &= ~vide[:, a.demi] & (vide.mean(axis=1) <= a.interp_max)
    print(f"  {m:12s} mediane N/j {int(n_median)}, blocs interpoles "
          f"{vide.mean() * 100:.1f} %, centres vides {int(vide[:, a.demi].sum())}, "
          f"segments plats {int(plat[:, i].sum())}", flush=True)

n_filtres = int((~garde).sum())
n_plat = int((garde & plat.any(axis=1)).sum())
garde &= ~plat.any(axis=1)
fenetres, mot_t, date_t, surprise_t = fenetres[garde], mot_t[garde], date_t[garde], surprise_t[garde]
X_t, N_t, echo, decalage, n_interp = X_t[garde], N_t[garde], echo[garde], decalage[garde], n_interp[garde]

chemin = f"{DOSSIER}/fenetres_trioV2_{tag}.npz"
np.savez_compressed(chemin, fenetres=fenetres, mot=mot_t, date=date_t,
                    surprise=surprise_t, X_t=X_t, N_t=N_t, echo=echo,
                    decalage=decalage, n_interp=n_interp, medias=np.array(a.medias),
                    pas=a.pas, demi=a.demi, tol=a.tol, seuil=a.seuil,
                    n_plat=n_plat, n_nms=n_nms)
effectifs = ", ".join(f">= {s} : {int((surprise_t >= s).sum())}" for s in (5, 6, 8))
print(f"FINI : {len(fenetres)} fenetres gardees ({n_filtres} ecartees par les filtres "
      f"de blocs vides, {n_plat} par un segment plat), effectifs par seuil "
      f"({effectifs}), {os.path.getsize(chemin) / 1e6:.0f} Mo en "
      f"{(time.time() - debut_t) / 60:.1f} min -> {chemin}", flush=True)
