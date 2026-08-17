# Figures d'exploration de la PCA du modele zero (etape 6) : plan PC1-PC2
# avec evenements celebres, fenetres archetypes de chaque composante,
# diagnostic corpus-quasi-vide sur la composante 4, reconstruction
# progressive d'une fenetre celebre. Lit fenetres_lemonde.npz,
# pca_lemonde_z.npz et vocab_series_lemonde.npz (grille N_t), ecrit 4 png
# dans rupture/sorties/.
# NB : l'hypothese « la paire 5-6 = rythme hebdomadaire » a ete testee et
# infirmee (vecteurs moyens par jour de semaine de norme 0,01-0,14 contre
# une dispersion de 0,8 ; idem apres 2000) : oscillations lentes generiques,
# pas de figure.
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLEU, ROUGE, GRILLE, ENCRE2, GRIS = "#2a78d6", "#e34948", "#e1e0d9", "#52514e", "#c9ced6"
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})

DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
SORTIES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rupture", "sorties")
os.makedirs(SORTIES, exist_ok=True)

d = np.load(f"{DOSSIER}/fenetres_lemonde.npz")
F, mots, dates, surprise = d["fenetres"].astype(float), d["mot"], d["date"], d["surprise"]
p = np.load(f"{DOSSIER}/pca_lemonde_z.npz")
proj, variance = p["projections"].astype(float), p["variance"]
Z = (F - F.mean(1, keepdims=True)) / F.std(1, keepdims=True)   # ce que voit la PCA
js = np.arange(-15, 16)

# --- A. densite du nuage dans le plan (PC1, PC2), evenements celebres situes ---
EVENEMENTS = [  # (mot, libelle court de l'evenement)
    ("francisco", "conf. de San Francisco (ONU), 1945"),
    ("algérie", "accords d'Évian, 1962"),
    ("mitterrand", "réélection Mitterrand, 1988"),
    ("chirac", "élection Chirac, 1995"),
    ("attentats", "13-Novembre, 2015"),
    ("jaunes", "gilets jaunes, 2018"),
]
EVENEMENTS = [(m, l.replace("réélection Mitterrand", "réélection")
               .replace("élection Chirac", "élection")) for m, l in EVENEMENTS]
DECALAGES = {  # position des etiquettes (points), reglee contre les collisions
    "francisco": (10, 26), "algérie": (7, 4), "mitterrand": (30, -8),
    "chirac": (16, -34), "attentats": (7, 4), "jaunes": (7, 4),
}
fig, ax = plt.subplots(figsize=(7.6, 5.6))
hb = ax.hexbin(proj[:, 0], proj[:, 1], gridsize=70, bins="log",
               cmap="Blues", linewidths=0.2)
fig.colorbar(hb, ax=ax, label="fenêtres par case (échelle log)", shrink=0.85)
for mot, libelle in EVENEMENTS:
    sel = mots == mot
    i = np.where(sel)[0][np.argmax(surprise[sel])]
    ax.scatter(proj[i, 0], proj[i, 1], s=26, color=ROUGE, zorder=3)
    ax.annotate(f"{mot} — {libelle}", (proj[i, 0], proj[i, 1]),
                xytext=DECALAGES[mot], textcoords="offset points",
                fontsize=8, color=ENCRE2,
                arrowprops={"arrowstyle": "-", "color": "#c3c2b7", "lw": 0.6})
ax.set_xlim(ax.get_xlim()[0], ax.get_xlim()[1] + 2.2)
ax.set_xlabel(f"composante 1 ({variance[0] * 100:.1f} % — pic isolé d'un jour)")
ax.set_ylabel(f"composante 2 ({variance[1] * 100:.1f} % — plus actif après le pic)")
ax.set_title("Les 123 310 fenêtres de sauts dans le plan des deux premières composantes",
             fontsize=10, color=ENCRE2)
fig.tight_layout()
fig.savefig(f"{SORTIES}/pca_lemonde_plan12.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- B. archetypes : les 3 fenetres reelles les plus alignees sur chaque composante ---
LIBELLES = ["pic isolé d'un jour", "plus actif après le pic",
            "bascule avant/après", "creux la veille, rebond"]
fig, axes = plt.subplots(4, 3, figsize=(9.2, 9.6), sharex=True)
for k in range(4):
    meilleurs = np.argsort(proj[:, k])[-3:][::-1]
    for c, i in enumerate(meilleurs):
        ax = axes[k, c]
        ax.axhline(0, lw=.6, color=GRILLE)
        ax.axvline(0, lw=.6, color=GRILLE)
        ax.plot(js, Z[i], lw=1.4, color=BLEU)
        ax.scatter([0], [Z[i, 15]], s=16, color=ROUGE, zorder=3)
        quand = pd.to_datetime(str(dates[i])).strftime("%d/%m/%Y")
        ax.set_title(f"{mots[i]} — {quand}", fontsize=8.5, color=ENCRE2)
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
        if c == 0:
            ax.set_ylabel(f"comp. {k + 1}\n({LIBELLES[k]})", fontsize=8.5)
for ax in axes[-1]:
    ax.set_xticks([-15, 0, 15])
    ax.set_xlabel("jours de parution autour du pic")
fig.suptitle("Fenêtres archétypes : les 3 sauts réels les plus alignés sur chaque composante"
             " (fenêtres en z-score)", fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(f"{SORTIES}/pca_lemonde_archetypes.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- C. la composante 4 attrape les jours a corpus quasi vide ---
# f_t = X_t / N_t explose quand N_t est minuscule (177 mots un jour de 1994
# contre 57 000 en mediane) : ces fenetres contaminees se projettent fort
# sur la composante 4.
g = np.load(f"{DOSSIER}/vocab_series_lemonde.npz")
grille_dates, grille_N = g["dates"], g["N"]
position = {int(dt): i for i, dt in enumerate(grille_dates)}
pos = np.array([position[int(dt)] for dt in dates])
N_min = grille_N[pos[:, None] + np.arange(-15, 16)].min(axis=1)
BORDS = [0, 100, 1000, 5000, 20000, 10**9]
NOMS_TRANCHES = ["< 100", "100\nà 1 000", "1 000\nà 5 000", "5 000\nà 20 000", "> 20 000"]
taux, effectifs = [], []
for a, b in zip(BORDS[:-1], BORDS[1:]):
    sel = (N_min >= a) & (N_min < b)
    taux.append((np.abs(proj[sel, 3]) > 2.5).mean() * 100)
    effectifs.append(int(sel.sum()))
fig, ax = plt.subplots(figsize=(6.4, 3.8))
barres = ax.bar(range(5), taux, width=0.62, color=BLEU)
for x, (t, n) in enumerate(zip(taux, effectifs)):
    ax.annotate(f"{t:.2f} %".replace(".", ","), (x, t), xytext=(0, 4),
                textcoords="offset points", ha="center", fontsize=8.5, color=ENCRE2)
    ax.annotate(f"{n:,} fen.".replace(",", " "), (x, 0), xytext=(0, -30),
                textcoords="offset points", ha="center", fontsize=7.5, color=ENCRE2)
ax.set_xticks(range(5), NOMS_TRANCHES, fontsize=8)
ax.set_xlabel("plus petit $N_t$ de la fenêtre (mots publiés le jour le plus creux)",
              labelpad=22)
ax.set_ylabel("part de projections extrêmes\n(|proj. comp. 4| > 2,5, en %)")
ax.set_title("Les projections extrêmes de la composante 4 viennent des fenêtres\n"
             "contenant un jour à corpus quasi vide ($f_t = X_t/N_t$ explose)",
             fontsize=10, color=ENCRE2)
ax.grid(True, axis="y", lw=.5, color=GRILLE)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(f"{SORTIES}/pca_lemonde_corpusvide.png", bbox_inches="tight", dpi=200)
plt.close(fig)
print("taux de |proj comp4| > 2,5 par tranche de N_min :",
      [f"{t:.2f}" for t in taux], "| effectifs :", effectifs)

# --- D. reconstruction progressive d'une fenetre celebre (gilets jaunes) ---
sel = mots == "jaunes"
i = np.where(sel)[0][np.argmax(surprise[sel])]
w = Z[i]
Zmoy = Z.mean(axis=0)
comp = p["composantes"]
fig, axes = plt.subplots(1, 4, figsize=(11.2, 3.0), sharey=True)
for ax, K in zip(axes, (1, 3, 6, 15)):
    recon = Zmoy + proj[i, :K] @ comp[:K]
    restitue = 1 - ((w - recon) ** 2).sum() / ((w - w.mean()) ** 2).sum()
    ax.axhline(0, lw=.6, color=GRILLE)
    ax.axvline(0, lw=.6, color=GRILLE)
    ax.plot(js, w, lw=2.0, color=GRIS)
    ax.plot(js, recon, lw=1.5, color=BLEU)
    ax.set_title(f"{K} composante{'s' if K > 1 else ''} — {restitue * 100:.0f} % restitués",
                 fontsize=9, color=ENCRE2)
    ax.set_xticks([-15, 0, 15])
    ax.set_xlabel("jours de parution")
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
quand = pd.to_datetime(str(dates[i])).strftime("%d/%m/%Y")
fig.suptitle(f"Reconstruction de la fenêtre « jaunes » du {quand} (gilets jaunes, en gris) "
             "par les premières composantes (bleu)", fontsize=10, color=ENCRE2)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(f"{SORTIES}/pca_lemonde_reconstruction.png", bbox_inches="tight", dpi=200)
plt.close(fig)

# --- E. le NMS en image : « syrienne » et le groupe geant du chainage ---
# (necessite la matrice X complete : produit sur gallica seulement)
if "X" in g.files:
    jcol = int(np.where(g["mots"] == "syrienne")[0][0])
    serie = 1e5 * g["X"][:, jcol].astype(float) / grille_N
    i1, i2 = np.searchsorted(grille_dates, [20110701, 20140901])
    dts = pd.to_datetime(pd.Series(grille_dates[i1:i2]).astype(str))
    avant = pd.read_csv(f"{DOSSIER}/pics_lemonde.csv")
    avant = avant[(avant["mot"] == "syrienne")
                  & avant["date"].between(20110701, 20140901)]
    apres = pd.read_csv(f"{DOSSIER}/pics_lemonde_nms.csv")
    apres = apres[(apres["mot"] == "syrienne")
                  & apres["date"].between(20110701, 20140901)]
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.plot(dts, serie[i1:i2], lw=.5, color=GRIS)
    ax.scatter(pd.to_datetime(avant["date"].astype(str)), avant["f_t"], s=9,
               color=BLEU, zorder=3, label=f"{len(avant)} pics détectés (p < 1e-4)")
    ax.scatter(pd.to_datetime(apres["date"].astype(str)), apres["f_t"], s=42,
               color=ROUGE, zorder=4, marker="o", facecolors="none", linewidths=1.6,
               label=f"{len(apres)} représentants gardés par le NMS")
    ax.set_ylabel("$f_t$ (pour 100 000 mots)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.margins(x=0)
    ax.set_title("« syrienne », 2011-2014 : le chaînage fusionnait ces pics en un seul "
                 "groupe (un seul datapoint) ; le NMS glouton garde un représentant "
                 "par sous-événement", fontsize=9.5, color=ENCRE2)
    fig.tight_layout()
    fig.savefig(f"{SORTIES}/nms_syrienne.png", bbox_inches="tight", dpi=200)
    plt.close(fig)

print("->", os.path.relpath(SORTIES), ": pca_lemonde_plan12.png, "
      "pca_lemonde_archetypes.png, pca_lemonde_corpusvide.png, "
      "pca_lemonde_reconstruction.png"
      + (", nms_syrienne.png" if "X" in g.files else " (nms_syrienne : gallica)"))
