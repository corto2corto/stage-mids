"""Etape 3 - Comparaison loi ajustee vs donnees (Poisson & NB), Le Monde 2020-2024.

Pas de simulation. Comme N_t varie, la loi de X_t change chaque jour : on compare donc
les donnees a la LOI-MELANGE analytique
        p_mix(k) = moyenne_t  pmf(k ; parametres, N_t),
qui tient compte de l'exposure variable. Determinite, 100% vraies donnees.

Sorties :
  - tableau des moments : observe vs Poisson-melange vs NB-melange (comparaison_moments.csv)
  - une figure par mot : histogramme de X_t + densites ajustees Poisson et NB (build_comparaison/)
"""
import os, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import poisson, nbinom, skew, kurtosis
from statsmodels.discrete.discrete_model import NegativeBinomial

ICI = "paper/donnees_maths"
OUT = f"{ICI}/build_comparaison"
os.makedirs(OUT, exist_ok=True)
MOTS = ["gouvernement", "president", "inflation", "economie", "guerre", "climat"]
LIB = {"president": "président", "economie": "économie"}
GRIS, BLEU, ROUGE = "#c9ced6", "#1f4e79", "#c1440e"


def fit(nom):
    d = pd.read_csv(f"{ICI}/{nom}_lemonde.csv")
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()
    lam = X.sum() / N.sum()                                  # Poisson MLE (forme fermee)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, alpha = np.exp(res.params[0]), res.params[1]
    return X, N, lam, mu, 1.0 / alpha                        # r = 1/alpha


def moments_pmf(p, k):
    """Moments (population) d'une loi discrete donnee par sa pmf p sur la grille k."""
    m = (k * p).sum()
    v = ((k - m) ** 2 * p).sum()
    return m, np.sqrt(v), v / m, ((k - m) ** 3 * p).sum() / v ** 1.5, ((k - m) ** 4 * p).sum() / v ** 2 - 3


def moments_obs(X):
    m, v = X.mean(), X.var()                                 # population (ddof=0)
    return m, np.sqrt(v), v / m, skew(X), kurtosis(X)        # scipy : population, Fisher


rows = []
for nom in MOTS:
    X, N, lam, mu, r = fit(nom)
    Kmax = int(X.max() * 1.3) + 5
    k = np.arange(Kmax + 1)
    pois = poisson.pmf(k[:, None], (lam * N)[None, :]).mean(1)
    p_nb = r / (r + mu * N)
    nb = nbinom.pmf(k[:, None], r, p_nb[None, :]).mean(1)

    lib = LIB.get(nom, nom)
    for src, mm in [("observé", moments_obs(X)), ("Poisson", moments_pmf(pois, k)), ("NB", moments_pmf(nb, k))]:
        rows.append((lib, src, *mm))

    # figure : histogramme des donnees + densites ajustees
    hi = int(np.percentile(X, 99.5)) + max(3, int(0.05 * X.max()))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.hist(X, bins=np.arange(0, Kmax + 2) - 0.5, density=True, color=GRIS, label="données")
    ax.plot(k, pois, color=ROUGE, lw=1.4, label=f"Poisson  (λ={lam*1e5:.0f}·10⁻⁵)")
    ax.plot(k, nb, color=BLEU, lw=1.8, label=f"NB  (r={r:.1f})")
    ax.set_xlim(-0.5, hi)
    ax.set_title(lib)
    ax.set_xlabel("$X_t$ (occurrences/jour)")
    ax.set_ylabel("densité")
    ax.legend(fontsize=8, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/cmp_{nom}.png", dpi=130)
    plt.close(fig)

tab = pd.DataFrame(rows, columns=["mot", "source", "moyenne", "ecart_type", "var/moy", "skewness", "kurtosis"])
with pd.option_context("display.float_format", lambda v: f"{v:9.2f}"):
    print(tab.to_string(index=False))
tab.to_csv(f"{ICI}/comparaison_moments.csv", index=False)
print("\n-> comparaison_moments.csv + build_comparaison/cmp_*.png")
