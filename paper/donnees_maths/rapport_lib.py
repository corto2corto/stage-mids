"""Bibliotheque pour rapport.qmd — rapport consolide (estimation + batterie de graphes).

Reprend la logique validee de estimation.py (MLE Poisson forme fermee, NB via
statsmodels + exposure), comparaison.py (densite-melange analytique sur les vrais
N_t) et pvaleurs.py (p-valeur du jour sous la NB ajustee), avec un style commun.
"""
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import poisson, nbinom, skew, kurtosis
from statsmodels.discrete.discrete_model import NegativeBinomial
from great_tables import GT, style, loc

ICI = os.path.dirname(os.path.abspath(__file__))
BUILD = f"{ICI}/build_rapport"
os.makedirs(BUILD, exist_ok=True)

MOTS = {
    "president":    "président",
    "gouvernement": "gouvernement",
    "guerre":       "guerre",
    "climat":       "climat",
    "economie":     "économie",
    "inflation":    "inflation",
}
SEUIL = 1e-4

# palette validee (CVD + contraste, fond blanc) : bleu = NB / lissage,
# orange = Poisson, rouge = jours anormaux ; gris recessif pour les donnees
BLEU, ORANGE, ROUGE = "#2a78d6", "#eb6834", "#e34948"
GRIS, GRILLE, ENCRE2, AXE = "#c9ced6", "#e1e0d9", "#52514e", "#c3c2b7"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.edgecolor": AXE, "axes.linewidth": 0.8, "axes.labelcolor": ENCRE2,
    "xtick.color": ENCRE2, "ytick.color": ENCRE2,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False,
})


# ---------------------------------------------------------------------------
# estimation
# ---------------------------------------------------------------------------

def ajuster(nom):
    """Charge un mot, ajuste Poisson et NB, calcule la p-valeur de chaque jour."""
    d = pd.read_csv(f"{ICI}/{nom}_lemonde.csv")
    d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
    d["f_t"] = 1e5 * d["X_t"] / d["N_t"]
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()

    lam = X.sum() / N.sum()                          # MLE Poisson (forme fermee)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, alpha = np.exp(res.params[0]), res.params[1]
    r = 1.0 / alpha

    # p_t = P(X >= X_t) sous la loi du jour NB(mu*N_t, r) : sf(X_t - 1)
    d["p_t"] = nbinom.sf(X - 1, r, r / (r + mu * N))
    return {"nom": nom, "lib": MOTS[nom], "d": d, "X": X, "N": N,
            "lam": lam, "mu": mu, "r": r, "alpha": alpha}


def melanges(m):
    """Densites-melange analytiques : moyenne des pmf du jour sur les vrais N_t."""
    X, N = m["X"], m["N"]
    k = np.arange(int(X.max() * 1.3) + 6)
    pois = poisson.pmf(k[:, None], (m["lam"] * N)[None, :]).mean(1)
    p_nb = m["r"] / (m["r"] + m["mu"] * N)
    nb = nbinom.pmf(k[:, None], m["r"], p_nb[None, :]).mean(1)
    return k, pois, nb


def moments_obs(X):
    m, v = X.mean(), X.var()                         # population (ddof=0)
    return m, np.sqrt(v), v / m, skew(X), kurtosis(X)


def moments_pmf(p, k):
    m = (k * p).sum()
    v = ((k - m) ** 2 * p).sum()
    return m, np.sqrt(v), v / m, ((k - m) ** 3 * p).sum() / v**1.5, ((k - m) ** 4 * p).sum() / v**2 - 3


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------

def fig_serie(m):
    """Serie temporelle de f_t + moyenne mobile + jours anormaux."""
    d = m["d"]
    fig, ax = plt.subplots(figsize=(10, 3.0))
    ax.plot(d["dt"], d["f_t"], lw=.5, color=GRIS, label="quotidien")
    mm = d["f_t"].rolling(7, center=True, min_periods=1).mean()
    ax.plot(d["dt"], mm, lw=1.4, color=BLEU, label="moyenne mobile 7 j")
    pics = d[d["p_t"] < SEUIL]
    ax.scatter(pics["dt"], pics["f_t"], s=22, color=ROUGE, zorder=3,
               label="jour anormal ($p_t < 10^{-4}$)")
    ax.set_ylabel("$f_t$ (pour 100 000 mots)")
    ax.set_ylim(0, d["f_t"].max() * 1.12)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.margins(x=0)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9)
    chemin = f"{BUILD}/serie_{m['nom']}.png"
    fig.tight_layout()
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return f"build_rapport/serie_{m['nom']}.png"


def fig_ajustement(m, k, pois, nb):
    """2 panneaux : histogramme + densites ajustees ; histogramme des p-valeurs."""
    X, p = m["X"], m["d"]["p_t"]
    n_pics = int((p < SEUIL).sum())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.2), width_ratios=[1.45, 1])

    a1.hist(X, bins=np.arange(0, k[-1] + 2) - 0.5, density=True, color=GRIS,
            label="données")
    a1.plot(k, pois, color=ORANGE, lw=1.6, label=f"Poisson ($\\hat\\lambda$)")
    a1.plot(k, nb, color=BLEU, lw=1.8, label=f"binomiale négative ($\\hat\\mu,\\hat r$)")
    a1.set_xlim(-0.5, np.percentile(X, 99.5) + max(3, int(0.05 * X.max())))
    a1.set_xlabel("$X_t$ (occurrences/jour)")
    a1.set_ylabel("densité")
    a1.legend(fontsize=9)

    a2.hist(p, bins=20, range=(0, 1), density=True, color=GRIS)
    a2.axhline(1, color=ENCRE2, lw=1, ls="--")
    a2.text(0.985, 1.0, "uniforme", color=ENCRE2, fontsize=8.5,
            ha="right", va="bottom", transform=a2.get_yaxis_transform())
    a2.set_xlabel("$p_t = \\mathbb{P}(X \\geq X_t)$")
    a2.set_title(f"{n_pics} jour{'s' if n_pics > 1 else ''} sous $10^{{-4}}$",
                 fontsize=9.5, color=ENCRE2)

    for ax in (a1, a2):
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    chemin = f"{BUILD}/ajust_{m['nom']}.png"
    fig.tight_layout(w_pad=2.5)
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return f"build_rapport/ajust_{m['nom']}.png"


# ---------------------------------------------------------------------------
# tableaux (great_tables)
# ---------------------------------------------------------------------------

def _style(gt):
    return (
        gt.opt_table_font(font="Helvetica")
        .opt_horizontal_padding(scale=1.4)
        .tab_options(
            table_border_top_style="hidden",
            table_border_bottom_style="hidden",
            column_labels_border_top_color="#0b0b0b",
            column_labels_border_top_width="2px",
            column_labels_border_bottom_color="#0b0b0b",
            column_labels_border_bottom_width="1px",
            table_body_border_bottom_color="#0b0b0b",
            table_body_border_bottom_width="2px",
            row_striping_background_color="#f4f6f9",
            column_labels_background_color="white",
            table_font_size="15px",
            data_row_padding="7px",
        )
        .opt_row_striping()
    )


def _sauver(gt, nom, vwidth=1700):
    chemin = f"{BUILD}/tab_{nom}.png"
    gt.gtsave(chemin, zoom=3.0, vwidth=vwidth, vheight=500)
    return f"build_rapport/tab_{nom}.png"


def tab_stats(mods):
    """Statistiques observees de X_t par mot, triees par frequence decroissante."""
    rows = []
    for m in sorted(mods, key=lambda m: -m["mu"]):
        moy, std, disp, sk, ku = moments_obs(m["X"])
        rows.append({"mot": m["lib"], "freq": m["lam"] * 1e5, "moy": moy,
                     "std": std, "disp": disp, "skew": sk, "kurt": ku})
    gt = (
        GT(pd.DataFrame(rows), rowname_col="mot")
        .tab_spanner(label="Occurrences quotidiennes Xₜ", columns=["moy", "std", "disp", "skew", "kurt"])
        .cols_label(freq="Fréquence (pour 10⁵)", moy="Moyenne", std="Écart-type",
                    disp="Var/Moy", skew="Skewness", kurt="Kurtosis")
        .fmt_number(columns=["freq", "moy", "std", "skew", "kurt"], decimals=2, locale="fr")
        .fmt_number(columns=["disp"], decimals=1, locale="fr")
        .cols_align(align="right", columns=["freq", "moy", "std", "disp", "skew", "kurt"])
        .tab_stubhead(label="Mot")
    )
    return _sauver(_style(gt), "stats")


def tab_params(mods):
    """Parametres estimes (lambda ; mu, r) des 6 mots, tries par frequence."""
    rows = []
    for m in sorted(mods, key=lambda m: -m["mu"]):
        rows.append({"mot": m["lib"], "lam": m["lam"] * 1e5, "mu": m["mu"] * 1e5,
                     "r": m["r"]})
    gt = (
        GT(pd.DataFrame(rows), rowname_col="mot")
        .tab_spanner(label="Poisson", columns=["lam"])
        .tab_spanner(label="Binomiale négative", columns=["mu", "r"])
        .cols_label(lam="λ̂ (pour 10⁵)", mu="μ̂ (pour 10⁵)", r="r̂")
        .fmt_number(columns=["lam", "mu", "r"], decimals=2, locale="fr")
        .cols_align(align="right", columns=["lam", "mu", "r"])
        .tab_stubhead(label="Mot")
    )
    return _sauver(_style(gt), "params", vwidth=1300)


def tab_moments(m, k, pois, nb):
    """Moments observes vs lois ajustees pour un mot."""
    rows = [("observé", *moments_obs(m["X"])),
            ("Poisson", *moments_pmf(pois, k)),
            ("binomiale négative", *moments_pmf(nb, k))]
    df = pd.DataFrame(rows, columns=["source", "moy", "std", "disp", "skew", "kurt"])
    gt = (
        GT(df, rowname_col="source")
        .cols_label(moy="Moyenne", std="Écart-type", disp="Var/Moy",
                    skew="Skewness", kurt="Kurtosis")
        .fmt_number(columns=["moy", "std", "disp", "skew", "kurt"], decimals=2, locale="fr")
        .cols_align(align="right", columns=["moy", "std", "disp", "skew", "kurt"])
        .tab_stubhead(label="Source")
        .tab_style(style=style.text(weight="bold"), locations=loc.body(rows=[0]))
        .tab_style(style=style.text(weight="bold"), locations=loc.stub(rows=[0]))
    )
    return _sauver(_style(gt), f"moments_{m['nom']}", vwidth=1100)


def tab_pics(mods):
    """Tous les jours anormaux (p < seuil), tries par surprise decroissante."""
    rows = []
    for m in mods:
        d = m["d"]
        for _, x in d[d["p_t"] < SEUIL].iterrows():
            rows.append({"mot": m["lib"], "date": x["dt"].strftime("%d/%m/%Y"),
                         "X_t": int(x["X_t"]), "f_t": x["f_t"],
                         "surprise": -np.log10(x["p_t"])})
    df = pd.DataFrame(rows).sort_values("surprise", ascending=False)
    gt = (
        GT(df)
        .cols_label(mot="Mot", date="Date", X_t="Xₜ", f_t="fₜ (pour 10⁵)",
                    surprise="Surprise −log₁₀(pₜ)")
        .fmt_number(columns=["f_t"], decimals=1, locale="fr")
        .fmt_number(columns=["surprise"], decimals=1, locale="fr")
        .cols_align(align="right", columns=["X_t", "f_t", "surprise"])
        .cols_align(align="center", columns=["date"])
        .tab_style(style=style.text(weight="bold"), locations=loc.body(columns=["mot"]))
    )
    return _sauver(_style(gt), "pics", vwidth=1100)
