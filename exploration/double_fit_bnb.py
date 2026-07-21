# Double fit Bern-NB (valide par Simon) : tour 1 = fit normal ; on retire les
# outliers evidents (p < 1e-6) ; tour 2 = refit de la NB des jours actifs sur
# le reste. Effet sur (mu_b, r_b), le chi2/ddl du bulk et le nb de pics.
# Usage : python -m exploration.double_fit_bnb   (CSV de paper/donnees_maths)
import warnings
import numpy as np
import pandas as pd
from scipy.stats import nbinom
from statsmodels.discrete.discrete_model import NegativeBinomial

SEUIL, EVIDENT = 1e-4, 1e-6
MOTS = ["chomage", "covid", "guerre", "immigration", "mitterrand", "chirac",
        "attentat", "retraite", "greve", "sida", "gouvernement", "president",
        "inflation", "economie", "climat", "europe", "ukraine", "terrorisme",
        "internet", "cancer"]

print(f"{'mot':12s} {'mu_b (x1e5)':>14s} {'r_b':>12s} {'retires':>7s} "
      f"{'pics':>10s} {'chi2/ddl bulk':>13s} {'nouveaux evid.':>14s}")
for mot in MOTS:
    d = pd.read_csv(f"paper/donnees_maths/{mot}_lemonde.csv")
    X, N = d["X_t"].to_numpy(float), d["N_t"].to_numpy(float)
    T = len(X)
    p0 = (X == 0).mean()
    act = X >= 1

    # tour 1 : Bern-NB normale
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X[act] - 1, np.ones((int(act.sum()), 1)),
                               exposure=N[act]).fit(disp=0, maxiter=300)
    mu1, r1 = np.exp(res.params[0]), 1.0 / res.params[1]
    p1 = np.ones(T)
    p1[act] = (1 - p0) * nbinom.sf(X[act] - 2, r1, r1 / (r1 + mu1 * N[act]))
    evid = p1 < EVIDENT

    # tour 2 : refit sans les outliers evidents (p0 inchangee)
    garde = act & ~evid
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res2 = NegativeBinomial(X[garde] - 1, np.ones((int(garde.sum()), 1)),
                                exposure=N[garde]).fit(disp=0, maxiter=300)
    mu2, r2 = np.exp(res2.params[0]), 1.0 / res2.params[1]
    p2 = np.ones(T)
    p2[act] = (1 - p0) * nbinom.sf(X[act] - 2, r2, r2 / (r2 + mu2 * N[act]))

    # calibration du melange refitte sur le bulk (jours conserves)
    m = mu2 * N
    v = m + m ** 2 / r2
    e = (1 - p0) * (1 + m)
    V = (1 - p0) * (v + (1 + m) ** 2) - e ** 2
    z = (X - e) / np.sqrt(V)
    ratio = float((z[~evid] ** 2).sum()) / (int((~evid).sum()) - 3)

    pics1, pics2 = int((p1 < SEUIL).sum()), int((p2 < SEUIL).sum())
    nouveaux = int(((p2 < EVIDENT) & ~evid).sum())
    print(f"{mot:12s} {mu1*1e5:6.2f} -> {mu2*1e5:5.2f} {r1:5.2f} -> {r2:4.2f} "
          f"{int(evid.sum()):7d} {pics1:4d} -> {pics2:3d} {ratio:13.2f} {nouveaux:14d}")
