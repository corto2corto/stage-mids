# Figures de la configuration optimale de la campagne PCA (Le Monde, grille
# hebdomadaire, fenetres +/-10 blocs, seuil de surprise 6, sans log) : les
# memes vues que la presentation du modele zero (spectre, profils des
# composantes, plan PC1-PC2, archetypes, reconstruction), sans la variante
# [0,1] — seul le z-score par fenetre est retenu.
# Rejoue la chaine en memoire depuis vocab_series_lemonde7j.npz et
# pics_lemonde7j.csv (grille agregee : pas de nettoyage corpus-vide, cf.
# presentation du modele zero), puis ecrit les png dans campagne_pca/figures/.
# Usage : .venv/bin/python -m campagne_pca.figures_optimale
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rupture.nms import nms
from rupture.pca import normaliser, pca

BLEU, ROUGE, GRILLE, ENCRE2, GRIS = "#2a78d6", "#e34948", "#e1e0d9", "#52514e", "#c9ced6"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)
MEDIA, DEMI, SEUIL = "lemonde7j", 10, 6.0
PAS_JOURS = 7                                  # taille d'un bloc, pour les libelles

# --- chaine : pics filtres -> NMS (portee 2d+1) -> fenetres -> z-score -> PCA
g = np.load(f"{DONNEES}/vocab_series_{MEDIA}.npz")
X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
position = {int(dt): i for i, dt in enumerate(grille_dates)}
colonne = {m: j for j, m in enumerate(g["mots"])}

p = pd.read_csv(f"{DONNEES}/pics_{MEDIA}.csv")
p = p[p["surprise"] >= SEUIL].assign(pos=lambda x: x["date"].map(position))
gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                 2 * DEMI + 1)[0]]
          for _, gr in p.groupby("mot", sort=False)]
p = p.loc[np.concatenate(gardes)]
pos, col = p["pos"].to_numpy(), p["mot"].map(colonne).to_numpy(int)
complet = (pos - DEMI >= 0) & (pos + DEMI < len(grille_dates))
p, pos, col = p[complet], pos[complet], col[complet]
lignes = pos[:, None] + np.arange(-DEMI, DEMI + 1)
F = (1e5 * X[lignes, col[:, None]] / grille_N[lignes]).astype(np.float64)

Z, garde_z = normaliser(F, "z")
p = p.iloc[garde_z]
mots, dates, surprise = (p["mot"].to_numpy(), p["date"].to_numpy(),
                         p["surprise"].to_numpy())
composantes, variance, proj = pca(Z)
Zc = Z - Z.mean(axis=0)                        # ce que voit la PCA (colonnes centrees)
js = np.arange(-DEMI, DEMI + 1)
D = 2 * DEMI + 1
cum = np.cumsum(variance)
K50 = int(np.searchsorted(cum, 0.5) + 1)
print(f"{MEDIA} d{DEMI} s{SEUIL:g} : {len(Z)} fenetres x {D} blocs | "
      f"K50={K50}, cum6={cum[5] * 100:.1f} %, cum10={cum[9] * 100:.1f} %")
print("variance des 6 premieres (%) :", np.round(variance[:6] * 100, 1))

# indicateurs de forme, pour nommer les composantes (cf. inspection_composantes)
for k in range(6):
    v = composantes[k]
    centre = (v[np.abs(js) <= DEMI // 4] ** 2).sum() / (v ** 2).sum()
    print(f"  comp {k + 1} : {int((np.diff(np.sign(v)) != 0).sum())} croisements, "
          f"{centre * 100:3.0f} % d'energie au centre, "
          f"signe(avant)={np.sign(v[:DEMI].mean()):+.0f} "
          f"signe(apres)={np.sign(v[DEMI + 1:].mean()):+.0f}")

LIBELLES = ["pic confiné au bloc du saut", "montée progressive, chute brutale",
            "changement de niveau avant/après", "pic élargi, creux encadrants",
            "oscillation lente", "oscillation rapide"]
TITRE = (f"Le Monde, blocs de {PAS_JOURS} jours, fenêtres ±{DEMI} blocs "
         f"(±{DEMI * PAS_JOURS} jours de parution), seuil de surprise {SEUIL:g}")

# --- 1. spectre : variance expliquee par composante (z-score seul) -----------
fig, ax = plt.subplots(figsize=(6.8, 3.8))
rangs = np.arange(1, D)
v = variance[:D - 1] * 100
isotrope = 100 / (D - 1)
ax.plot(rangs, v, lw=1.8, color=BLEU, label="z-score par fenêtre")
ax.scatter(rangs[:1], v[:1], s=18, color=BLEU)
ax.annotate(f"{v[0]:.1f} %".replace(".", ","), (1, v[0]), xytext=(7, 2),
            textcoords="offset points", fontsize=8.5, color=ENCRE2)
ax.axhline(isotrope, lw=1.0, ls="--", color=ROUGE,
           label=f"nuage sans structure ({isotrope:.1f} %)".replace(".", ","))
ax.set_yscale("log")
ax.set_xlabel("rang de la composante")
ax.set_ylabel("variance expliquée (%)")
ax.set_xlim(0.5, D - 0.5)
ax.set_xticks([1] + list(range(5, D, 5)))
ax.legend(frameon=False, fontsize=8.5)
ax.grid(True, axis="y", lw=.5, color=GRILLE)
ax.set_axisbelow(True)
ax.set_title(f"Variance expliquée par composante — {K50} composantes pour 50 %, "
             f"{cum[5] * 100:.0f} % à 6\n{TITRE}", fontsize=9.5, color=ENCRE2)
fig.tight_layout()
fig.savefig(f"{FIGURES}/optimale_spectre.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 2. profils temporels des six premieres composantes ---------------------
fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.2), sharex=True)
for k, ax in enumerate(axes.flat):
    ax.axhline(0, lw=.6, color=GRILLE)
    ax.axvline(0, lw=.6, color=GRILLE)
    ax.plot(js, composantes[k], lw=1.7, color=BLEU)
    ax.set_title(f"composante {k + 1} — {variance[k] * 100:.1f} %\n{LIBELLES[k]}",
                 fontsize=8.5, color=ENCRE2)
    ax.set_xticks([-DEMI, 0, DEMI])
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
for ax in axes[1]:
    ax.set_xlabel(f"blocs de {PAS_JOURS} jours autour du pic")
fig.suptitle(f"Les six premières composantes comme profils temporels\n{TITRE}",
             fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(f"{FIGURES}/optimale_composantes.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 3. plan PC1-PC2 : densite du nuage, evenements situes ------------------
CANDIDATS = [("francisco", "conf. de San Francisco (ONU), 1945"),
             ("algérie", "accords d'Évian, 1962"),
             ("mitterrand", "réélection, 1988"),
             ("chirac", "élection, 1995"),
             ("attentats", "13-Novembre, 2015"),
             ("jaunes", "gilets jaunes, 2018"),
             ("covid", "Covid, 2020"),
             ("syrienne", "guerre civile syrienne")]
DECALAGES = {"francisco": (9, 4, "left"), "algérie": (-9, -14, "right"),
             "mitterrand": (9, 6, "left"), "chirac": (11, -15, "left"),
             "attentats": (9, 11, "left"), "jaunes": (2, -18, "left")}
fig, ax = plt.subplots(figsize=(7.6, 5.6))
hb = ax.hexbin(proj[:, 0], proj[:, 1], gridsize=60, bins="log",
               cmap="Blues", linewidths=0.2)
fig.colorbar(hb, ax=ax, label="fenêtres par case (échelle log)", shrink=0.85)
places = []
for mot, libelle in CANDIDATS:
    sel = mots == mot
    if not sel.any():
        print(f"  (plan) « {mot} » absent de cette configuration")
        continue
    i = np.where(sel)[0][np.argmax(surprise[sel])]
    quand = pd.to_datetime(str(dates[i])).strftime("%m/%Y")
    ax.scatter(proj[i, 0], proj[i, 1], s=26, color=ROUGE, zorder=3)
    places.append((proj[i, 0], proj[i, 1], f"{mot} — {libelle}", mot))
    print(f"  (plan) {mot} {quand} : PC1={proj[i, 0]:+.1f} PC2={proj[i, 1]:+.1f}")
for x, y, texte, mot in places:
    dx, dy, ha = DECALAGES.get(mot, (9, 4, "left"))
    ax.annotate(texte, (x, y), xytext=(dx, dy), ha=ha,
                textcoords="offset points", fontsize=8, color=ENCRE2,
                arrowprops={"arrowstyle": "-", "color": "#c3c2b7", "lw": 0.6})
ax.set_xlabel(f"composante 1 ({variance[0] * 100:.1f} % — {LIBELLES[0]})")
ax.set_ylabel(f"composante 2 ({variance[1] * 100:.1f} % — {LIBELLES[1]})")
effectif = f"{len(Z):,}".replace(",", " ")
ax.set_title(f"Les {effectif} fenêtres dans le plan des deux premières composantes\n"
             f"{TITRE}", fontsize=9.5, color=ENCRE2)
fig.tight_layout()
fig.savefig(f"{FIGURES}/optimale_plan12.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 4. archetypes : les 3 fenetres reelles les plus alignees par composante -
fig, axes = plt.subplots(4, 3, figsize=(9.2, 9.6), sharex=True)
for k in range(4):
    meilleurs = np.argsort(proj[:, k])[-3:][::-1]
    for c, i in enumerate(meilleurs):
        ax = axes[k, c]
        ax.axhline(0, lw=.6, color=GRILLE)
        ax.axvline(0, lw=.6, color=GRILLE)
        ax.plot(js, Z[i], lw=1.4, color=BLEU)
        ax.scatter([0], [Z[i, DEMI]], s=16, color=ROUGE, zorder=3)
        quand = pd.to_datetime(str(dates[i])).strftime("%d/%m/%Y")
        ax.set_title(f"{mots[i]} — {quand}", fontsize=8.5, color=ENCRE2)
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
        if c == 0:
            ax.set_ylabel(f"comp. {k + 1}\n({LIBELLES[k]})", fontsize=8.5)
    print(f"  (archetypes) comp {k + 1} : "
          + ", ".join(f"{mots[i]} {int(dates[i])}" for i in meilleurs))
for ax in axes[-1]:
    ax.set_xticks([-DEMI, 0, DEMI])
    ax.set_xlabel(f"blocs de {PAS_JOURS} jours autour du pic")
fig.suptitle("Fenêtres archétypes : les 3 sauts réels les plus alignés sur chaque "
             f"composante (z-score)\n{TITRE}", fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(f"{FIGURES}/optimale_archetypes.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- 5. reconstruction progressive d'une fenetre celebre --------------------
for mot_cible in ("jaunes", "attentats", "covid", "chirac"):
    sel = mots == mot_cible
    if sel.any():
        break
i = np.where(sel)[0][np.argmax(surprise[sel])]
w, Zmoy = Z[i], Z.mean(axis=0)
paliers = sorted({1, 3, K50, 6})           # K50 inclus, en ordre croissant
fig, axes = plt.subplots(1, len(paliers), figsize=(11.2, 3.0), sharey=True)
for ax, K in zip(axes, paliers):
    recon = Zmoy + proj[i, :K] @ composantes[:K]
    restitue = 1 - ((w - recon) ** 2).sum() / ((w - w.mean()) ** 2).sum()
    ax.axhline(0, lw=.6, color=GRILLE)
    ax.axvline(0, lw=.6, color=GRILLE)
    ax.plot(js, w, lw=2.0, color=GRIS)
    ax.plot(js, recon, lw=1.5, color=BLEU)
    ax.set_title(f"{K} composante{'s' if K > 1 else ''} — {restitue * 100:.0f} % restitués",
                 fontsize=9, color=ENCRE2)
    ax.set_xticks([-DEMI, 0, DEMI])
    ax.set_xlabel(f"blocs de {PAS_JOURS} jours")
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
quand = pd.to_datetime(str(dates[i])).strftime("%d/%m/%Y")
fig.suptitle(f"Reconstruction de la fenêtre « {mots[i]} » du {quand} (en gris) par les "
             f"premières composantes (bleu)\n{TITRE}", fontsize=9.5, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.90))
fig.savefig(f"{FIGURES}/optimale_reconstruction.png", bbox_inches="tight", dpi=200)
plt.close(fig)

print(f"-> {os.path.relpath(FIGURES)} : optimale_spectre.png, optimale_composantes.png, "
      "optimale_plan12.png, optimale_archetypes.png, optimale_reconstruction.png")
