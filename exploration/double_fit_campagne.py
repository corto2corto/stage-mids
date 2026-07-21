# Campagne de tests du double fit Bern-NB sur les 20 mots :
#  1. sensibilite au seuil « evident » (1e-5, 1e-6, 1e-7), un tour de refit ;
#  2. version iteree a 1e-6 jusqu'a convergence (max 6 tours) ;
#  3. dates des pics gagnes par le double fit (1e-6, un tour) ;
#  4. calibration du bulk (chi2/ddl du melange refitte sur les jours conserves).
# Usage : python -m exploration.double_fit_campagne
import warnings
import numpy as np
import pandas as pd
from scipy.stats import nbinom
from statsmodels.discrete.discrete_model import NegativeBinomial

SEUIL = 1e-4
SEUILS_EVIDENT = (1e-5, 1e-6, 1e-7)
MOTS = ["chomage", "covid", "guerre", "immigration", "mitterrand", "chirac",
        "attentat", "retraite", "greve", "sida", "gouvernement", "president",
        "inflation", "economie", "climat", "europe", "ukraine", "terrorisme",
        "internet", "cancer"]

warnings.simplefilter("ignore")
gains = {}                       # mot -> dates des pics gagnes (1e-6, un tour)
totaux = {s: 0 for s in SEUILS_EVIDENT}
total_simple, total_itere = 0, 0

print(f"{'mot':12s} {'simple':>6s} | {'@1e-5':>5s} {'@1e-6':>5s} {'@1e-7':>5s} | "
      f"{'itere':>5s} {'tours':>5s} | {'bulk':>5s}")
for mot in MOTS:
    d = pd.read_csv(f"paper/donnees_maths/{mot}_lemonde.csv")
    X, N = d["X_t"].to_numpy(float), d["N_t"].to_numpy(float)
    T = len(X)
    p0 = (X == 0).mean()
    act = X >= 1

    # fit simple (tour 1)
    res = NegativeBinomial(X[act] - 1, np.ones((int(act.sum()), 1)),
                           exposure=N[act]).fit(disp=0, maxiter=300)
    mu1, r1 = np.exp(res.params[0]), 1.0 / res.params[1]
    p1 = np.ones(T)
    p1[act] = (1 - p0) * nbinom.sf(X[act] - 2, r1, r1 / (r1 + mu1 * N[act]))
    pics1 = int((p1 < SEUIL).sum())
    total_simple += pics1

    # 1. un tour de refit, pour chaque seuil « evident »
    pics_seuil = {}
    for s in SEUILS_EVIDENT:
        garde = act & (p1 >= s)
        res2 = NegativeBinomial(X[garde] - 1, np.ones((int(garde.sum()), 1)),
                                exposure=N[garde]).fit(disp=0, maxiter=300)
        mu2, r2 = np.exp(res2.params[0]), 1.0 / res2.params[1]
        p2 = np.ones(T)
        p2[act] = (1 - p0) * nbinom.sf(X[act] - 2, r2, r2 / (r2 + mu2 * N[act]))
        pics_seuil[s] = int((p2 < SEUIL).sum())
        totaux[s] += pics_seuil[s]
        if s == 1e-6:
            gains[mot] = d["date"][(p2 < SEUIL) & (p1 >= SEUIL)].tolist()
            p_1e6, retires_1e6 = p2, garde

    # 2. iteration a 1e-6 jusqu'a convergence
    retires = np.zeros(T, bool)
    p_it, tours = p1, 1
    for tour in range(2, 7):
        nouveaux = act & (p_it < 1e-6) & ~retires
        if not nouveaux.any():
            break
        retires |= nouveaux
        garde = act & ~retires
        res_i = NegativeBinomial(X[garde] - 1, np.ones((int(garde.sum()), 1)),
                                 exposure=N[garde]).fit(disp=0, maxiter=300)
        mu_i, r_i = np.exp(res_i.params[0]), 1.0 / res_i.params[1]
        p_it = np.ones(T)
        p_it[act] = (1 - p0) * nbinom.sf(X[act] - 2, r_i, r_i / (r_i + mu_i * N[act]))
        tours = tour
    pics_it = int((p_it < SEUIL).sum())
    total_itere += pics_it

    # 4. calibration du bulk (loi du tour final itere, jours non retires)
    m = mu_i * N if tours > 1 else mu1 * N
    r_f = r_i if tours > 1 else r1
    v = m + m ** 2 / r_f
    e = (1 - p0) * (1 + m)
    V = (1 - p0) * (v + (1 + m) ** 2) - e ** 2
    z = (X - e) / np.sqrt(V)
    bulk = float((z[~retires] ** 2).sum()) / (int((~retires).sum()) - 3)

    print(f"{mot:12s} {pics1:6d} | {pics_seuil[1e-5]:5d} {pics_seuil[1e-6]:5d} "
          f"{pics_seuil[1e-7]:5d} | {pics_it:5d} {tours:5d} | {bulk:5.2f}")

print(f"\nTOTAUX : simple {total_simple} | un tour @1e-5 {totaux[1e-5]} "
      f"@1e-6 {totaux[1e-6]} @1e-7 {totaux[1e-7]} | itere @1e-6 {total_itere}")

print("\nPics gagnes par le double fit (@1e-6, un tour) :")
for mot, dates in gains.items():
    if dates:
        print(f"  {mot:12s} {' '.join(str(x) for x in dates)}")
