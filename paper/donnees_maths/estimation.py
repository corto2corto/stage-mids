"""Etape 2 - Estimation des parametres Poisson et NB (Le Monde, 2020-2024).

Poisson scale : X_t ~ Poisson(lambda * N_t).
    MLE en forme fermee  ->  lambda = sum(X) / sum(N)   (la "moyenne empirique" scalee).
NB2 scale     : X_t ~ NB(mu * N_t, r), Var = mu.N (1 + alpha.mu.N), alpha = 1/r.
    Pas de forme fermee  ->  statsmodels (intercept seul + exposure = N_t).
    mu = exp(const) = frequence moyenne ; alpha = dispersion ; r = 1/alpha.

Sortie : tableau console + params_estimes.csv. Frequences donnees pour 100 000 mots.
"""
import warnings
import numpy as np
import pandas as pd
from statsmodels.discrete.discrete_model import NegativeBinomial

ICI = "paper/donnees_maths"
MOTS = ["gouvernement", "president", "inflation", "economie", "guerre", "climat"]
LIB = {"president": "président", "economie": "économie"}


def charger(nom):
    d = pd.read_csv(f"{ICI}/{nom}_lemonde.csv")
    return d["X_t"].to_numpy(), d["N_t"].to_numpy()


rows = []
for nom in MOTS:
    X, N = charger(nom)
    lam = X.sum() / N.sum()                         # Poisson MLE (forme fermee)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, alpha = np.exp(res.params[0]), res.params[1]
    rows.append({
        "mot": LIB.get(nom, nom),
        "lambda (Poisson, /1e5)": lam * 1e5,
        "mu (NB, /1e5)": mu * 1e5,
        "r (NB)": 1.0 / alpha,
        "alpha (NB)": alpha,
    })

tab = pd.DataFrame(rows)
with pd.option_context("display.float_format", lambda v: f"{v:10.3f}"):
    print(tab.to_string(index=False))
tab.to_csv(f"{ICI}/params_estimes.csv", index=False)
print("\n-> paper/donnees_maths/params_estimes.csv")
