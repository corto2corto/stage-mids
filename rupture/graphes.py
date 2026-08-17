"""Briques graphiques : fiche express d'un mot, planche des fenetres.

Meme langage visuel que /fiche-mot (palette de rapport_lib) ; les fonctions
prennent des donnees deja calculees (serie enrichie, densite) — le calcul
reste dans pics.py.
"""
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# palette de rapport_lib (+ vert Bern-NB des fiches)
BLEU, ROUGE, GRILLE, ENCRE2, AXE = "#2a78d6", "#e34948", "#e1e0d9", "#52514e", "#c3c2b7"
GRIS, ORANGE, VERT = "#c9ced6", "#eb6834", "#2f9e6e"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.edgecolor": AXE, "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})


def fiche(d, k, pmf, loi, titre, chemin):
    """Fiche express : serie f_t + pics, histogramme vs loi ajustee, p-valeurs."""
    X = d["X_t"].to_numpy(float)
    coul = {"poisson": ORANGE, "nb": BLEU, "bnb": VERT}[loi]
    fig = plt.figure(figsize=(10, 5.8))
    ax = fig.add_subplot(2, 1, 1)
    ax.plot(d["dt"], d["f_t"], lw=.4, color=GRIS)
    mm = d["f_t"].rolling(7, center=True, min_periods=1).mean()
    ax.plot(d["dt"], mm, lw=1.1, color=BLEU)
    pics = d[d["p_t"] < 1e-4]
    ax.scatter(pics["dt"], pics["f_t"], s=12, color=ROUGE, zorder=3)
    ax.set_ylabel("$f_t$ (pour 100 000 mots)")
    ax.set_ylim(0, d["f_t"].max() * 1.12)
    ax.margins(x=0)
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.set_title(titre, fontsize=10, color=ENCRE2)

    a1 = fig.add_subplot(2, 2, 3)
    a1.hist(X, bins=np.arange(0, k[-1] + 2) - 0.5, density=True, color=GRIS)
    a1.plot(k, pmf, color=coul, lw=1.6)
    a1.set_xlim(-0.5, np.percentile(X, 99.5) + max(3, int(0.05 * X.max())))
    a1.set_xlabel("$X_t$ (occurrences/jour)")
    a1.set_ylabel("densité")

    a2 = fig.add_subplot(2, 2, 4)
    p = d.loc[d["X_t"] >= 1, "p_t"] if loi == "bnb" else d["p_t"]
    a2.hist(p, bins=20, range=(0, 1), density=True, color=GRIS)
    a2.axhline(1, color=ENCRE2, lw=1, ls="--")
    a2.set_xlabel("$p_t$" + (" (jours actifs)" if loi == "bnb" else ""))

    for a in (ax, a1, a2):
        a.grid(True, axis="y", lw=.5, color=GRILLE)
        a.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)


def planche(fen, slug, chemin, ncol=5):
    """Petits multiples : une cellule par fenetre (f_t sur ±15 j, pic en rouge)."""
    cols = [c for c in fen.columns if c.startswith("j")]
    js = [int(c[1:]) for c in cols]
    n = len(fen)
    ncol = min(ncol, n)
    nlig = math.ceil(n / ncol)
    fig, axes = plt.subplots(nlig, ncol, figsize=(2.3 * ncol, 1.9 * nlig), squeeze=False)
    for ax, (_, p) in zip(axes.flat, fen.iterrows()):
        ax.plot(js, p[cols].to_numpy(float), lw=1.1, color=BLEU)
        ax.scatter([0], [p["f_t"]], s=18, color=ROUGE, zorder=3)
        date = pd.to_datetime(str(p["date"])).strftime("%d/%m/%Y")
        ax.set_title(f"{date} — surprise {p['surprise']:.1f}", fontsize=8, color=ENCRE2)
        ax.set_xticks([js[0], 0, js[-1]])
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    for ax in axes.flat[n:]:
        ax.axis("off")
    fig.suptitle(f"{slug} — fenetres de f_t (pour 100 000 mots) autour des {n} pics",
                 fontsize=10, color=ENCRE2)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
