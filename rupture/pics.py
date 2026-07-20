"""Brique 2 : ajuster la binomiale negative et detecter les pics d'un mot.

Meme modele que rapport_lib : X_t ~ NB(mu * N_t, r) via statsmodels (exposure),
p-valeur du jour p_t = P(X >= X_t) sous la loi du jour, pic si p_t < 10^-4
(surprise = -log10(p_t) > 4).

L'option --poisson remplace la NB par une loi de Poisson(lambda * N_t), aux
queues plus legeres : elle declare plus de jours anormaux.

Usage : python -m rupture.pics <slug> [debut] [fin] [--poisson]
"""
import sys
import warnings
import numpy as np
from scipy.stats import nbinom, poisson
from statsmodels.discrete.discrete_model import NegativeBinomial

from rupture import serie

SEUIL = 1e-4


def ajuster(d):
    """Ajoute p_t et surprise a la serie ; renvoie (d, mu, r)."""
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, r = np.exp(res.params[0]), 1.0 / res.params[1]
    p = nbinom.sf(X - 1, r, r / (r + mu * N))
    d["p_t"] = p
    d["surprise"] = -np.log10(np.maximum(p, 1e-300))
    return d, mu, r


def ajuster_poisson(d):
    """Variante Poisson : ajoute p_t et surprise ; renvoie (d, lam)."""
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()
    lam = X.sum() / N.sum()                       # MLE en forme fermee
    p = poisson.sf(X - 1, lam * N)
    d["p_t"] = p
    d["surprise"] = -np.log10(np.maximum(p, 1e-300))
    return d, lam


def detecter(d, seuil=SEUIL):
    """Les pics : lignes de la serie dont p_t < seuil (index = position du jour)."""
    return d[d["p_t"] < seuil]


if __name__ == "__main__":
    en_poisson = "--poisson" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--poisson"]
    slug = args[0]
    d1 = int(args[1]) if len(args) > 1 else 0
    d2 = int(args[2]) if len(args) > 2 else 99999999
    d = serie.charger(slug, d1, d2)
    if en_poisson:
        d, lam = ajuster_poisson(d)
        loi = f"Poisson lambda={lam*1e5:.2f} pour 10^5"
    else:
        d, mu, r = ajuster(d)
        loi = f"NB mu={mu*1e5:.2f} pour 10^5, r={r:.2f}"
    pics = detecter(d)
    print(f"{slug} : {len(d)} jours | {loi} | {len(pics)} pics")
    aff = pics if len(pics) <= 30 else pics.nlargest(30, "surprise").sort_values("date")
    if len(aff) < len(pics):
        print(f"(les 30 plus surprenants sur {len(pics)})")
    if len(aff):
        print(aff[["date", "X_t", "f_t", "p_t", "surprise"]].to_string(
            index=False, formatters={"f_t": "{:.1f}".format, "p_t": "{:.1e}".format,
                                     "surprise": "{:.1f}".format}))
