# PCA JOINTE sur les fenetres de triplets (fenetres_trio_<tag>.npz produit par
# fenetres_triplets.py) : chaque segment de media est z-score sur lui-meme
# (sinon le media le plus volumineux ecraserait les autres), les trois segments
# sont concatenes (vecteurs de 3L) et la PCA de rupture.pca tourne dessus.
# Chaque composante (3L) est presentee en deux lectures :
# - communes : le vecteur redecoupe en 3 segments puis moyenne -> forme commune
# - medias   : les 3 segments superposes -> decalages et asymetries entre medias
# Le signe d'une composante est arbitraire : oriente du cote de la queue lourde
# des projections (cote des archetypes, comme corpus_unifie).
# Sorties :
# - <VOCAB_DIR>/pca_trio_<tag>_s<seuil>.npz : composantes, variance,
#   projections float32, garde (indices dans le npz de triplets)
# - rupture/sorties/pca_trio_<tag>_s<seuil>_{variance,communes,medias}.png
# Usage : python -m rupture.pca_trio [tag] [seuil_ref]     (defauts : j20 4)
import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.graphes import BLEU, GRILLE, ENCRE2
from rupture.pca import pca

COULEURS = {"lemonde": "#1A171B", "lefigaro": "#163860", "lesechos": "#b00005",
            "ouestfrance": "#c8102e", "mediapart": "#fc392b"}
NOMS = {"lemonde": "Le Monde", "lefigaro": "Le Figaro", "lesechos": "Les Échos",
        "ouestfrance": "Ouest-France", "mediapart": "Mediapart"}
SORTIES = f"{os.path.dirname(os.path.abspath(__file__))}/sorties"

tag = sys.argv[1] if len(sys.argv) > 1 else "j20"
seuil = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
debut = time.time()

d = np.load(f"{DOSSIER}/fenetres_trio_{tag}.npz")
medias = [str(m) for m in d["medias"]]
pas, demi = int(d["pas"]), int(d["demi"])
unite = "jours" if pas == 1 else f"blocs de {pas} j"
s_ref = d["surprise"][np.arange(len(d["ref"])), d["ref"]]
m = s_ref >= seuil
F = d["fenetres"][m].astype(np.float64)                     # (n, 3, L)
print(f"{tag} : {len(F)} triplets a reference >= {seuil:g} "
      f"(sur {len(m)}), medias {', '.join(medias)}", flush=True)

# z-score par segment puis concatenation ; un segment plat ecarte le triplet
mu = F.mean(axis=2, keepdims=True)
sd = F.std(axis=2, keepdims=True)
plates = (sd[:, :, 0] == 0).any(axis=1)
garde = np.where(m)[0][~plates]
Z = ((F[~plates] - mu[~plates]) / sd[~plates]).reshape(len(garde), -1)
composantes, variance, proj = pca(Z)
signes = np.sign((proj ** 3).sum(axis=0))
signes[signes == 0] = 1
composantes, proj = composantes * signes[:, None], proj * signes
np.savez_compressed(f"{DOSSIER}/pca_trio_{tag}_s{seuil:g}.npz",
                    composantes=composantes, variance=variance,
                    projections=proj.astype(np.float32), garde=garde)
print(f"  {len(Z)} vecteurs de {Z.shape[1]} ({int(plates.sum())} segments plats "
      f"ecartes), 6 premieres composantes : "
      f"{np.round(variance[:6] * 100, 1)} % de variance", flush=True)

os.makedirs(SORTIES, exist_ok=True)
prefixe = f"{SORTIES}/pca_trio_{tag}_s{seuil:g}"
segments = composantes.reshape(-1, 3, 2 * demi + 1)         # (3L, 3, L)
js = np.arange(-demi, demi + 1)

# figure 1 : variance expliquee (echelle log)
fig, ax = plt.subplots(figsize=(6.4, 3.6))
v = variance[:30] * 100
ax.plot(np.arange(1, 31), v, lw=1.6, color=BLEU)
ax.annotate(f"{v[0]:.1f} %".replace(".", ","), (1, v[0]), xytext=(6, 3),
            textcoords="offset points", fontsize=8, color=ENCRE2)
ax.set_yscale("log")
ax.set_xlabel("rang de la composante")
ax.set_ylabel("variance expliquée (%)")
ax.grid(True, axis="y", lw=.5, color=GRILLE)
ax.set_axisbelow(True)
ax.set_title(f"PCA jointe {tag} (référence ≥ {seuil:g}) — variance par composante",
             fontsize=10, color=ENCRE2)
fig.tight_layout()
fig.savefig(f"{prefixe}_variance.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# figures 2 et 3 : les six premieres composantes, en forme commune (moyenne
# des 3 segments) puis segment par segment (un trait par media)
for nom, dessine in (
        ("communes", lambda ax, k: ax.plot(js, segments[k].mean(axis=0),
                                           lw=1.6, color=BLEU)),
        ("medias", lambda ax, k: [ax.plot(js, segments[k][i], lw=1.3,
                                          color=COULEURS.get(md, "#8a8987"),
                                          label=NOMS.get(md, md) if k == 0 else None)
                                  for i, md in enumerate(medias)])):
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.2), sharex=True, sharey=True)
    for k, ax in enumerate(axes.flat):
        ax.axhline(0, lw=.6, color=GRILLE)
        ax.axvline(0, lw=.6, color=GRILLE)
        dessine(ax, k)
        ax.set_title(f"composante {k + 1} — {variance[k] * 100:.1f} %",
                     fontsize=8.5, color=ENCRE2)
        ax.set_xticks([-demi, 0, demi])
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    if nom == "medias":
        axes[0, 0].legend(frameon=False, fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel(f"{unite} autour de la date commune")
    lecture = ("forme commune (moyenne des 3 segments)" if nom == "communes"
               else "un segment par média")
    fig.suptitle(f"PCA jointe {tag} (référence ≥ {seuil:g}) — {lecture}",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(f"{prefixe}_{nom}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)

print(f"FINI en {time.time() - debut:.0f} s -> pca_trio_{tag}_s{seuil:g}.npz, "
      f"{os.path.relpath(SORTIES)}/pca_trio_{tag}_s{seuil:g}_*.png", flush=True)
