# Planche « archetypes » d'une seule composante : les 12 sauts reels les plus
# alignes sur elle (meme chaine que figures_config.py, vue 4 restreinte a une comp).
# Usage : .venv/bin/python -m campagne_pca.figures_comp3 <media> --demi D --seuil S
#         --pas_jours P --prefixe nom --media_nom "Le Monde" --couleur ... --accent ...
import argparse
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import nettoyer, normaliser, pca

GRILLE, ENCRE2 = "#e1e0d9", "#52514e"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

ap = argparse.ArgumentParser()
ap.add_argument("media")
ap.add_argument("--demi", type=int, required=True)
ap.add_argument("--seuil", type=float, required=True)
ap.add_argument("--pas_jours", type=int, required=True)
ap.add_argument("--prefixe", required=True)
ap.add_argument("--media_nom", required=True)
ap.add_argument("--couleur", required=True)
ap.add_argument("--accent", required=True)
ap.add_argument("--comp", type=int, default=3, help="numero de la composante (1-based)")
ap.add_argument("--pics", default="")
ap.add_argument("--nettoie", type=int, default=0)
ap.add_argument("--vol_q", type=float, default=50,
                 help="quantile de volume (occurrences brutes, max de la fenetre) sous "
                      "lequel une fenetre est ecartee du CHOIX DES ARCHETYPES ; "
                      "0 = pas de filtre. N'affecte pas la PCA.")
ap.add_argument("--vol_min", type=int, default=50,
                 help="plancher absolu d'occurrences au pic pour un archetype, combine "
                      "au quantile par un max")
a = ap.parse_args()

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)
MEDIA, DEMI, SEUIL, PAS_JOURS, PREFIXE = a.media, a.demi, a.seuil, a.pas_jours, a.prefixe
BLEU, ROUGE = a.couleur, a.accent
K = a.comp - 1

# --- chaine : pics filtres -> NMS (portee 2d+1) -> fenetres -> z-score -> PCA
g = np.load(f"{DONNEES}/vocab_series_{MEDIA}.npz")
X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
position = {int(dt): i for i, dt in enumerate(grille_dates)}
colonne = {m: j for j, m in enumerate(g["mots"])}

p = pd.read_csv(f"{DONNEES}/pics_{MEDIA}{a.pics}.csv")
p = p[p["surprise"] >= SEUIL].assign(pos=lambda x: x["date"].map(position))
gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                 2 * DEMI + 1)[0]]
          for _, gr in p.groupby("mot", sort=False)]
p = p.loc[np.concatenate(gardes)]
pos, col = p["pos"].to_numpy(), p["mot"].map(colonne).to_numpy(int)
complet = (pos - DEMI >= 0) & (pos + DEMI < len(grille_dates))
p, pos, col = p[complet], pos[complet], col[complet]
lignes = pos[:, None] + np.arange(-DEMI, DEMI + 1)
brut = X[lignes, col[:, None]]
F = (1e5 * brut / grille_N[lignes]).astype(np.float64)

if a.nettoie:
    F, garde_n, _, _ = nettoyer(F, grille_N[lignes], a.nettoie, DEMI)
    p, brut = p.iloc[garde_n], brut[garde_n]
Z, garde_z = normaliser(F, "z")
p, brut = p.iloc[garde_z], brut[garde_z]
volume = brut.max(axis=1)
mots, dates, surprise = (p["mot"].to_numpy(), p["date"].to_numpy(),
                         p["surprise"].to_numpy())
composantes, variance, proj = pca(Z)
js = np.arange(-DEMI, DEMI + 1)
D = 2 * DEMI + 1

if PAS_JOURS == 1:
    GRILLE_LIBELLE = f"journalier, fenêtres ±{DEMI} jours"
    UNITE_AXE = "jours autour du pic"
else:
    GRILLE_LIBELLE = (f"blocs de {PAS_JOURS} jours, fenêtres ±{DEMI} blocs "
                      f"(±{DEMI * PAS_JOURS} jours de parution)")
    UNITE_AXE = f"blocs de {PAS_JOURS} jours autour du pic"
TITRE = f"{a.media_nom}, {GRILLE_LIBELLE}, seuil de surprise {SEUIL:g}"

v = composantes[K]
centre = (v[np.abs(js) <= DEMI // 4] ** 2).sum() / (v ** 2).sum()
print(f"{MEDIA} d{DEMI} s{SEUIL:g} : {len(Z)} fenetres | comp {a.comp} = "
      f"{variance[K] * 100:.1f} % | {int((np.diff(np.sign(v)) != 0).sum())} croisements, "
      f"{centre * 100:.0f} % d'energie au centre")

# --- planche : le profil de la composante, puis ses 12 sauts les plus alignes
fig = plt.figure(figsize=(9.2, 11.4))
gs = fig.add_gridspec(5, 3, height_ratios=[1.15, 1, 1, 1, 1], hspace=0.55, wspace=0.22)

axp = fig.add_subplot(gs[0, 1])
axp.axhline(0, lw=.6, color=GRILLE)
axp.axvline(0, lw=.6, color=GRILLE)
axp.plot(js, v, lw=1.9, color=BLEU)
axp.set_title(f"profil de la composante {a.comp} — {variance[K] * 100:.1f} %",
              fontsize=9, color=ENCRE2)
axp.set_xticks([-DEMI, 0, DEMI])
axp.set_xlabel(UNITE_AXE, fontsize=8)
axp.grid(True, axis="y", lw=.5, color=GRILLE)
axp.set_axisbelow(True)

seuil_vol = max(np.percentile(volume, a.vol_q) if a.vol_q > 0 else 0, a.vol_min)
eligibles = np.where(volume >= seuil_vol)[0]
if len(eligibles) < 12:
    print(f"  (archetypes) filtre de volume ignore : seuil {seuil_vol:.0f} ne laisse "
          f"que {len(eligibles)} fenetres")
    seuil_vol, eligibles = 0, np.arange(len(Z))
elif seuil_vol > 0:
    print(f"  (archetypes) filtre de volume : >= {seuil_vol:.0f} occurrences au pic "
          f"(q{a.vol_q:g} = {np.percentile(volume, a.vol_q):.0f}, plancher {a.vol_min}) : "
          f"{len(eligibles)} fenetres eligibles sur {len(Z)}")

meilleurs = eligibles[np.argsort(proj[eligibles, K])[-12:][::-1]]
axes = []
for c, i in enumerate(meilleurs):
    ax = fig.add_subplot(gs[1 + c // 3, c % 3])
    axes.append(ax)
    ax.axhline(0, lw=.6, color=GRILLE)
    ax.axvline(0, lw=.6, color=GRILLE)
    ax.plot(js, Z[i], lw=1.4, color=BLEU)
    ax.scatter([0], [Z[i, DEMI]], s=16, color=ROUGE, zorder=3)
    quand = pd.to_datetime(str(dates[i])).strftime("%d/%m/%Y")
    ax.set_title(f"{c + 1}. {mots[i]} — {quand}\n{int(volume[i])} occ. au pic",
                 fontsize=8.5, color=ENCRE2)
    ax.set_xticks([-DEMI, 0, DEMI])
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    if c % 3 == 0:
        ax.set_ylabel("écart-types", fontsize=8.5)
    if c >= 9:
        ax.set_xlabel(UNITE_AXE, fontsize=8)
print(f"  (archetypes) comp {a.comp} : "
      + ", ".join(f"{mots[i]} {int(dates[i])} ({proj[i, K]:+.1f}, {int(volume[i])} occ.)"
                  for i in meilleurs))

filtre_libelle = (f", parmi les fenêtres d'au moins {seuil_vol:.0f} occurrences au pic"
                  if seuil_vol > 0 else "")
fig.suptitle(f"Composante {a.comp} : les 12 sauts réels les plus alignés (z-score)"
             f"{filtre_libelle}\n{TITRE}",
             fontsize=10.5, color=ENCRE2, y=0.965)
fig.savefig(f"{FIGURES}/{PREFIXE}_comp{a.comp}_archetypes.png",
            bbox_inches="tight", dpi=200)
plt.close(fig)
print(f"-> {os.path.relpath(FIGURES)}/{PREFIXE}_comp{a.comp}_archetypes.png")
