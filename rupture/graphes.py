"""Plot optionnel : planche des fenetres d'un mot, meme langage visuel que /fiche-mot."""
import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# palette de rapport_lib
BLEU, ROUGE, GRILLE, ENCRE2, AXE = "#2a78d6", "#e34948", "#e1e0d9", "#52514e", "#c3c2b7"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.edgecolor": AXE, "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
})


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
