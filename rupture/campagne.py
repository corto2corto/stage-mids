# Campagne PCA 48 h (31/07/2026) : evalue UNE configuration d'hyperparametres
# en rejouant la fin de la chaine en memoire, sans toucher aux sorties
# officielles de data/. Depuis pics_<media><pics>.csv et
# vocab_series_<media>.npz : filtre par seuil de surprise et par categorie
# grammaticale -> NMS (portee 2*demi+1) -> fenetres +/-demi -> nettoyage V2
# -> z-score -> PCA -> metriques de concentration du spectre.
# Ecrit dans <VOCAB_DIR>/campagne/ : une ligne dans resultats.csv, plus
# spectre_<tag>.csv et composantes_<tag>.csv (8 premieres).
# Les categories grammaticales viennent de campagne_pca/vocab_categories.csv
# (classification spaCy + Lexique faite sur le Mac, committee).
# Usage : python -m rupture.campagne <media> [--demi 15] [--seuil 4]
#         [--filtre tous|sans_verbes|noms|noms_propres] [--nettoie 5000]
#         [--pics ""]   (ex. --pics _s3 pour lire pics_<media>_s3.csv)
import argparse
import os
import time

import numpy as np
import pandas as pd

from rupture.nms import nms
from rupture.pca import nettoyer, normaliser, pca

ICI = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = os.path.join(ICI, "..", "campagne_pca", "vocab_categories.csv")
COLONNES = ("horodatage,tag,media,demi,seuil,filtre,nettoie,pics,"
            "n_pics_seuil,n_mots,n_nms,n_bords,n_centres_ecartes,n_plates,"
            "n_fenetres,D,K50,K50_frac,rang_eff,rang_eff_frac,"
            "cum3,cum6,cum10,gain6,cum6_nul,exces6,v1,v2,v3,v4,v5,v6,duree_s")

p = argparse.ArgumentParser()
p.add_argument("media")
p.add_argument("--demi", type=int, default=15)
p.add_argument("--seuil", type=float, default=4.0)
p.add_argument("--filtre", default="tous",
               choices=("tous", "sans_verbes", "noms", "noms_propres"))
p.add_argument("--nettoie", type=int, default=5000)
p.add_argument("--pics", default="")
p.add_argument("--sous_ech", type=int, default=0,
               help="sous-echantillonner les fenetres a N (tirage seede) — "
                    "compare les configs a taille d'echantillon egale")
a = p.parse_args()

DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
CAMP = f"{DOSSIER}/campagne"
os.makedirs(CAMP, exist_ok=True)
tag = (f"{a.media}_d{a.demi}_s{a.seuil:g}_{a.filtre}_n{a.nettoie}"
       + (f"_e{a.sous_ech}" if a.sous_ech else ""))
debut = time.time()

d = np.load(f"{DOSSIER}/vocab_series_{a.media}.npz")
X, dates, N = d["X"], d["dates"], d["N"]
position = {int(dt): i for i, dt in enumerate(dates)}
colonne = {m: j for j, m in enumerate(d["mots"])}

pics = pd.read_csv(f"{DOSSIER}/pics_{a.media}{a.pics}.csv")
pics = pics[pics["surprise"] >= a.seuil]
if a.filtre != "tous":
    cat = pd.read_csv(CATEGORIES).set_index("mot")["categorie"]
    c = pics["mot"].map(cat)
    inconnus = int(c.isna().sum())
    if a.filtre == "sans_verbes":
        pics = pics[c != "verbe"]
    elif a.filtre == "noms":
        pics = pics[c.isin(("nom", "nom_propre"))]
    else:
        pics = pics[c == "nom_propre"]
    if inconnus:
        print(f"  {inconnus} pics de mots hors categories", flush=True)
n_pics_seuil = len(pics)

# NMS glouton par mot, portee = largeur de fenetre (aucun recouvrement)
portee = 2 * a.demi + 1
pics = pics.assign(pos=pics["date"].map(position))
gardes = []
for mot, g in pics.groupby("mot", sort=False):
    idx, _ = nms(g["pos"].to_numpy(), g["surprise"].to_numpy(), portee)
    gardes.append(g.index.to_numpy()[idx])
pics = pics.loc[np.concatenate(gardes)] if gardes else pics
n_nms = len(pics)

# fenetres +/-demi (vectorise, comme fenetres_masse.py)
pos = pics["pos"].to_numpy()
col = pics["mot"].map(colonne).to_numpy(int)
complet = (pos - a.demi >= 0) & (pos + a.demi < len(dates))
n_bords = int((~complet).sum())
pos, col = pos[complet], col[complet]
lignes = pos[:, None] + np.arange(-a.demi, a.demi + 1)
F = (1e5 * X[lignes, col[:, None]] / N[lignes]).astype(np.float64)

n_centres = 0
if a.nettoie:
    F, garde_n, _, _ = nettoyer(F, N[lignes], a.nettoie, a.demi)
    n_centres = len(lignes) - len(garde_n)

F, garde_z = normaliser(F, "z")
n_plates = (len(lignes) - n_centres) - len(F)
if a.sous_ech and len(F) > a.sous_ech:
    F = F[np.random.default_rng(1).choice(len(F), a.sous_ech, replace=False)]
composantes, variance, _ = pca(F)

# temoin nul : chaque colonne melangee independamment (memes marges, structure
# temporelle detruite) — a petit echantillon le spectre nul depasse le spectre
# plat (Marchenko-Pastur), exces6 = cum6/cum6_nul est le gain honnete
rng = np.random.default_rng(0)
Fn = F.copy()
for j in range(Fn.shape[1]):
    rng.shuffle(Fn[:, j])
_, v_nul, _ = pca(Fn)

# metriques de concentration (D-1 dimensions utiles apres z-score)
D = 2 * a.demi + 1
rang = D - 1
cum = np.cumsum(variance)
K50 = int(np.searchsorted(cum, 0.5) + 1)
rang_eff = float(1.0 / (variance**2).sum())
cum3, cum6, cum10 = (float(cum[min(k, rang, len(cum)) - 1]) for k in (3, 6, 10))
gain6 = cum6 / (min(6, rang) / rang)
cum6_nul = float(np.cumsum(v_nul)[min(6, rang, len(v_nul)) - 1])
exces6 = cum6 / cum6_nul
v6 = list(variance[:6]) + [0.0] * max(0, 6 - len(variance))
n_mots = pics.loc[pics.index[complet], "mot"].nunique() if len(pics) else 0
duree = time.time() - debut

ligne = (f"{time.strftime('%Y-%m-%dT%H:%M:%S')},{tag},{a.media},{a.demi},"
         f"{a.seuil:g},{a.filtre},{a.nettoie},{a.pics},"
         f"{n_pics_seuil},{n_mots},{n_nms},{n_bords},{n_centres},{n_plates},"
         f"{len(F)},{D},{K50},{K50 / rang:.4f},{rang_eff:.2f},"
         f"{rang_eff / rang:.4f},{cum3:.4f},{cum6:.4f},{cum10:.4f},"
         f"{gain6:.3f},{cum6_nul:.4f},{exces6:.3f}," +
         ",".join(f"{v:.6f}" for v in v6) + f",{duree:.0f}")
if not os.path.exists(f"{CAMP}/resultats.csv"):
    with open(f"{CAMP}/resultats.csv", "w") as f:
        f.write(COLONNES + "\n")
with open(f"{CAMP}/resultats.csv", "a") as f:
    f.write(ligne + "\n")

# n < D possible sur les configs extremes : variance et composantes n'ont
# alors que min(n, D) entrees, on ecrit ce qui existe
pd.DataFrame({"variance": variance}, index=np.arange(1, len(variance) + 1)
             ).rename_axis("rang").to_csv(f"{CAMP}/spectre_{tag}.csv",
                                          float_format="%.8f")
k8 = min(8, len(composantes))
pd.DataFrame(composantes[:k8], index=np.arange(1, k8 + 1),
             columns=[f"j{j:+d}" for j in range(-a.demi, a.demi + 1)]
             ).rename_axis("composante").to_csv(
    f"{CAMP}/composantes_{tag}.csv", float_format="%.8f")

print(f"{tag} : {n_pics_seuil} pics -> {n_nms} apres NMS -> {len(F)} fenetres "
      f"({n_bords} bords, {n_centres} centres vides, {n_plates} plates) | "
      f"K50={K50} ({K50 / rang:.2f}), rang_eff={rang_eff:.1f}, "
      f"cum6={cum6 * 100:.1f} %, gain6={gain6:.2f}, exces6={exces6:.2f} | "
      f"{duree:.0f} s", flush=True)
