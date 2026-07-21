"""Brique 2 : ajuster une loi de comptage et detecter les pics d'un mot.

Trois lois, toutes normalisees par l'exposition N_t :
  poisson   X ~ P(lam * N_t)
  nb        X ~ NB(mu * N_t, r)
  bnb       melange Bernoulli x NB decalee : X = 0 avec proba p0,
            sinon X = 1 + NB(mu_b * N_t, r_b)   (defaut)
fits = nombre de fits : 1 (defaut) ; k > 1 : (k-1) tours « retirer les jours
evidents (p < 1e-6) puis refiter » (double fit valide par Simon ; p0 n'est
jamais retouchee, un jour a zero n'est pas un outlier).

Les fonctions de calcul travaillent sur des tableaux (X, N) : la CLI les
branche sur serie.charger, l'API /fiche sur sa propre lecture de la base.

Usage : python -m rupture.pics <mot> [poisson|nb|bnb] [fits] [debut] [fin]
        [--media lemonde|lefigaro|lesechos] [--plot]
Ex.    python -m rupture.pics chômage nb          # l'ancien resultat (NB, 1 fit)
       python -m rupture.pics retraite bnb 2      # Bern-NB + double fit
"""
import sys
import warnings
import numpy as np
from scipy.stats import chi2 as loi_chi2, nbinom, poisson as loi_pois
from statsmodels.discrete.discrete_model import NegativeBinomial

from rupture import serie

SEUIL, EVIDENT = 1e-4, 1e-6
LOIS = ("poisson", "nb", "bnb")
K_PARAMS = {"poisson": 1, "nb": 2, "bnb": 3}


def _fit_nb(y, n):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(y, np.ones((len(y), 1)), exposure=n).fit(disp=0, maxiter=300)
    return float(np.exp(res.params[0])), float(1.0 / res.params[1])


def pvaleurs(X, N, loi, params):
    """p_t = P(X >= X_t) sous la loi du jour."""
    if loi == "poisson":
        return loi_pois.sf(X - 1, params["lam"] * N)
    if loi == "nb":
        r = params["r"]
        return nbinom.sf(X - 1, r, r / (r + params["mu"] * N))
    p0, mu_b, r_b = params["p0"], params["mu_b"], params["r_b"]
    p = np.ones(len(X))
    act = X >= 1
    p[act] = (1 - p0) * nbinom.sf(X[act] - 2, r_b, r_b / (r_b + mu_b * N[act]))
    return p


def ajuster(X, N, loi="bnb", fits=1, evident=EVIDENT):
    """Ajuste la loi (fits-1 retraits des jours a p < evident) ; renvoie (params, p, garde).

    garde = jours ayant participe au dernier fit (sert au chi2 du bulk)."""
    X, N = np.asarray(X, float), np.asarray(N, float)
    garde = np.ones(len(X), bool)
    for tour in range(fits):
        if loi == "poisson":
            params = {"lam": float(X[garde].sum() / N[garde].sum())}
        elif loi == "nb":
            mu, r = _fit_nb(X[garde], N[garde])
            params = {"mu": mu, "r": r}
        else:
            act = (X >= 1) & garde
            mu_b, r_b = _fit_nb(X[act] - 1, N[act])
            params = {"p0": float((X == 0).mean()), "mu_b": mu_b, "r_b": r_b}
        p = pvaleurs(X, N, loi, params)
        if tour < fits - 1:
            garde &= p >= evident
    return params, p, garde


def esperance_variance(N, loi, params):
    """(E_t, V_t) de la loi du jour, pour les residus de Pearson."""
    if loi == "poisson":
        m = params["lam"] * N
        return m, m
    if loi == "nb":
        m = params["mu"] * N
        return m, m + m ** 2 / params["r"]
    p0, m_b = params["p0"], params["mu_b"] * N
    v_nb = m_b + m_b ** 2 / params["r_b"]
    e = (1 - p0) * (1 + m_b)
    return e, (1 - p0) * (v_nb + (1 + m_b) ** 2) - e ** 2


def adequation(X, N, loi, params, garde=None):
    """Chi2 de Pearson sur les jours du fit ; ddl = jours - parametres."""
    X, N = np.asarray(X, float), np.asarray(N, float)
    if garde is None:
        garde = np.ones(len(X), bool)
    e, v = esperance_variance(N, loi, params)
    z = (X - e) / np.sqrt(v)
    stat = float((z[garde] ** 2).sum())
    ddl = int(garde.sum()) - K_PARAMS[loi]
    return {"chi2": stat, "ddl": ddl, "ratio": stat / ddl,
            "p": float(loi_chi2.sf(stat, ddl)), "z": z}


def densite(X, N, loi, params):
    """Densite-melange (moyenne des pmf du jour sur les vrais N_t), par blocs.

    Grille plafonnee a 30 000 valeurs ; renvoie (k, pmf)."""
    X, N = np.asarray(X, float), np.asarray(N, float)
    k1 = int(X.max() * 1.3) + 6
    k = np.arange(max(0, k1 - 30000), k1)
    pmf = np.zeros(len(k))
    for i in range(0, len(N), 2000):
        n = N[i:i + 2000]
        if loi == "poisson":
            pmf += loi_pois.pmf(k[:, None], (params["lam"] * n)[None, :]).sum(1)
        elif loi == "nb":
            q = params["r"] / (params["r"] + params["mu"] * n)
            pmf += nbinom.pmf(k[:, None], params["r"], q[None, :]).sum(1)
        else:
            q = params["r_b"] / (params["r_b"] + params["mu_b"] * n)
            pmf += (1 - params["p0"]) * nbinom.pmf(k[:, None] - 1, params["r_b"], q[None, :]).sum(1)
    pmf /= len(N)
    if loi == "bnb" and k[0] == 0:
        pmf[0] = params["p0"]                 # masse ponctuelle en 0
    return k, pmf


def moments_pmf(k, pmf):
    """[moyenne, ecart-type, Var/Moy, skewness, kurtosis] d'une loi discrete."""
    m = float((k * pmf).sum())
    v = float(((k - m) ** 2 * pmf).sum())
    return [m, v ** 0.5, v / m if m else None,
            float(((k - m) ** 3 * pmf).sum()) / v ** 1.5 if v else None,
            float(((k - m) ** 4 * pmf).sum()) / v ** 2 - 3 if v else None]


def detecter(d, seuil=SEUIL):
    """Les pics : lignes de la serie dont p_t < seuil (index = position du jour)."""
    return d[d["p_t"] < seuil]


if __name__ == "__main__":
    mot, loi, fits, dates, media, plot = None, "bnb", 1, [], "lemonde", False
    args = iter(sys.argv[1:])
    for a in args:
        if a == "--plot":
            plot = True
        elif a == "--media":
            media = next(args)
        elif a.lower() in LOIS or a.lower() == "p":
            loi = "poisson" if a.lower() == "p" else a.lower()
        elif a.isdigit() and len(a) == 8:
            dates.append(int(a))
        elif a.isdigit():
            fits = int(a)
        elif mot is None:
            mot = a
        else:
            sys.exit(f"argument inconnu : {a}")
    if mot is None:
        sys.exit(__doc__)
    d1 = dates[0] if dates else 0
    d2 = dates[1] if len(dates) > 1 else 99999999

    try:
        d = serie.charger(mot, media, d1, d2)
    except ValueError as e:
        sys.exit(str(e))
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()
    params, p, garde = ajuster(X, N, loi, fits)
    d["p_t"] = p
    d["surprise"] = -np.log10(np.maximum(p, 1e-300))
    adeq = adequation(X, N, loi, params, garde)
    pics = detecter(d)

    if loi == "poisson":
        aff = f"lam={params['lam']*1e5:.2f} pour 10^5"
    elif loi == "nb":
        aff = f"mu={params['mu']*1e5:.2f} pour 10^5, r={params['r']:.2f}"
    else:
        aff = (f"p0={params['p0']*100:.1f}%, mu_b={params['mu_b']*1e5:.2f} "
               f"pour 10^5, r_b={params['r_b']:.2f}")
    retires = len(d) - int(garde.sum())
    print(f"{mot} ({media}) : {len(d)} jours | {loi} fits={fits} | {aff} | "
          f"chi2/ddl={adeq['ratio']:.2f}"
          + (f" | {retires} jours retires" if fits > 1 else "")
          + f" | {len(pics)} pics")
    aff_pics = pics if len(pics) <= 30 else pics.nlargest(30, "surprise").sort_values("date")
    if len(aff_pics) < len(pics):
        print(f"(les 30 plus surprenants sur {len(pics)})")
    if len(aff_pics):
        print(aff_pics[["date", "X_t", "f_t", "p_t", "surprise"]].to_string(
            index=False, formatters={"f_t": "{:.1f}".format, "p_t": "{:.1e}".format,
                                     "surprise": "{:.1f}".format}))
    if plot:
        import os
        from rupture import extraire, graphes
        k, pmf = densite(X, N, loi, params)
        sorties = f"{os.path.dirname(os.path.abspath(__file__))}/sorties"
        os.makedirs(sorties, exist_ok=True)
        chemin = f"{sorties}/pics_{media}_{extraire.slug(mot)}_{loi}{fits}.png"
        graphes.fiche(d, k, pmf, loi, f"{mot} ({media}) — {loi}, fits={fits}", chemin)
        print("->", os.path.relpath(chemin))
