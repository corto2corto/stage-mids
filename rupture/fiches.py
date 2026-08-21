"""Fiches statistiques d'un mot : ajustements Poisson / NB, figures, tableaux.

Bibliotheque commune a rapport.qmd (6 mots, 2020-2024), fiches_mots.qmd (le
recueil des 40 mots) et fiche.py (skill /fiche-mot). Reprend la logique validee
de estimation.py (MLE Poisson forme fermee, NB via statsmodels + exposure),
comparaison.py (densite-melange analytique sur les vrais N_t), pvaleurs.py
(p-valeur du jour sous la NB ajustee) et le test du chi2 sur les residus de
Pearson (meme calcul que la route /fiche de l'API).

Les series viennent de series_mots.csv : une colonne par mot, totaux N_t
factorises (N_1gram, N_2gram). Un mot absent de la table est extrait de la
base a la volee ; apres ajout dans MOTS ou RECUEIL, rebatir la table avec
python paper/donnees_maths/series.py pour figer la donnee dans le depot.

Les images sont ecrites dans BUILD, relatif au dossier ou tourne le rendu.
Un script lance d'ailleurs (fiche.py depuis la racine) fixe BUILD via build_dans().
"""
import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import poisson, nbinom, norm, skew, kurtosis, chi2 as loi_chi2
from statsmodels.discrete.discrete_model import NegativeBinomial

from rupture.extraire import serie, slug

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIES = f"{RACINE}/paper/donnees_maths/series_mots.csv"
BUILD = "build_rapport"
SEUIL = 1e-4

# les 6 mots de rapport.qmd
MOTS = ("président", "gouvernement", "guerre", "climat", "économie", "inflation")

# les 40 mots du recueil, par longueur de periode : (mot, debut, fin).
# ordre, periodes et regroupement sont editoriaux — pas deduits des dates.
RECUEIL = {
    "Périodes longues (25 à 80 ans)": [
        ("guerre",                    19450101, 20241231),
        ("gaulle",                    19460101, 19751231),
        ("communiste",                19450101, 19911231),
        ("algérie",                   19500101, 19691231),
        ("europe",                    19500101, 20241231),
        ("francs",                    19450101, 20051231),
        ("euro",                      19950101, 20241231),
        ("chômage",                   19700101, 20241231),
        ("internet",                  19900101, 20241231),
        ("nucléaire",                 19600101, 20241231),
        ("climat",                    19800101, 20241231),
        ("terrorisme",                19700101, 20241231),
        ("immigration",               19700101, 20241231),
        ("télévision",                19500101, 20091231),
        ("mondialisation",            19900101, 20151231),
        ("croissance",                19900101, 20241231),
        ("milliards",                 19800101, 20241231),
    ],
    "Périodes moyennes (7 à 22 ans)": [
        ("mitterrand",                19810101, 19961231),
        ("chirac",                    19860101, 20071231),
        ("sarkozy",                   20020101, 20171231),
        ("hollande",                  20110101, 20171231),
        ("macron",                    20140101, 20251231),
        ("crise",                     20060101, 20151231),
        ("islam",                     20010101, 20201231),
        ("attentats",                 20120101, 20201231),
        ("irak",                      20010101, 20101231),
        ("inflation",                 19730101, 19861231),
    ],
    "Périodes courtes (2 à 8 ans)": [
        ("covid",                     20200101, 20241231),
        ("confinement",               20200101, 20221231),
        ("vaccin",                    20200101, 20231231),
        ("russie",                    20210101, 20241231),
        ("ukraine",                   20210101, 20241231),
        ("poutine",                   20220101, 20241231),
        ("gaza",                      20220101, 20251231),
        ("retraites",                 20220101, 20241231),
        ("jeux",                      20230101, 20251231),
        ("dissolution",               20230101, 20251231),
        ("zemmour",                   20210101, 20231231),
        ("étudiants",                 19660101, 19701231),
        ("intelligence artificielle", 20180101, 20251231),
    ],
}

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
# donnees
# ---------------------------------------------------------------------------

_table = None


def _lire():
    """Table series_mots.csv, lue une seule fois : date, N_1gram, N_2gram, un mot/colonne."""
    global _table
    if _table is None:
        _table = pd.read_csv(SERIES)
    return _table


def charger(mot, d1=None, d2=None):
    """Serie (date, X_t, N_t) d'un mot sur la periode, jours a zero compris.

    Lue dans series_mots.csv ; un mot absent de la table est extrait de la base
    (extraire.serie, avec son cache) — pratique pour une fiche ponctuelle.
    """
    s, t = slug(mot), _lire()
    if s in t.columns:
        total = "N_2gram" if "_" in s else "N_1gram"  # expression -> grille bigram
        d = t[["date", s, total]].dropna().rename(columns={s: "X_t", total: "N_t"})
    else:
        d = serie(mot)
    d = d[(d["date"] >= (d1 or 0)) & (d["date"] <= (d2 or 99999999))]
    return d[["date", "X_t", "N_t"]].astype({"X_t": int, "N_t": int}).reset_index(drop=True)


def periode(d1, d2):
    """Libelle : « 2020 » ou « 1945–2024 » pour des annees pleines, les dates sinon."""
    if (d1 % 10000, d2 % 10000) == (101, 1231):
        return str(d1)[:4] if d1 // 10000 == d2 // 10000 else f"{str(d1)[:4]}–{str(d2)[:4]}"
    return f"{d1}–{d2}"


def fr(v):
    """Nombre a la francaise : espace pour les milliers, virgule decimale."""
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


def fr_p(p):
    return "≈ 0" if p < 1e-15 else f"{p:.1e}".replace(".", ",")


def fr_p_bref(p):
    """p-valeur en colonne etroite : « 0,29 », « 2e-4 », « ≈ 0 »."""
    if p < 1e-15:
        return "≈ 0"
    return f"{p:.2f}".replace(".", ",") if p >= 0.01 else f"{p:.0e}".replace("e-0", "e-")


# ---------------------------------------------------------------------------
# estimation
# ---------------------------------------------------------------------------

def ajuster(mot, d1=None, d2=None):
    """Charge un mot sur la periode, ajuste Poisson et NB, p-valeur de chaque jour."""
    d = charger(mot, d1, d2)
    if len(d) < 60:
        raise ValueError(f"« {mot} » : {len(d)} jours seulement, fit trop fragile")
    d1, d2 = d1 or int(d["date"].iloc[0]), d2 or int(d["date"].iloc[-1])
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
    return {"nom": slug(mot), "lib": mot, "per": periode(d1, d2), "d": d, "X": X,
            "N": N, "lam": lam, "mu": mu, "r": r, "alpha": alpha}


def melanges(m):
    """Densites-melange analytiques : moyenne des pmf du jour sur les vrais N_t."""
    X, N = m["X"], m["N"]
    k = np.arange(int(X.max() * 1.3) + 6)
    pois = poisson.pmf(k[:, None], (m["lam"] * N)[None, :]).mean(1)
    p_nb = m["r"] / (m["r"] + m["mu"] * N)
    nb = nbinom.pmf(k[:, None], m["r"], p_nb[None, :]).mean(1)
    return k, pois, nb


def adequation(m):
    """Test du chi2 sur les residus de Pearson z_t = (X_t - m_t)/sqrt(v_t).

    Chaque jour est compare a sa propre loi (N_t varie) ; ddl = jours - parametres.
    """
    X, N, lam, mu, r = m["X"], m["N"], m["lam"], m["mu"], m["r"]
    adeq = []
    for nom_loi, esp, var, k_est in (("Poisson", lam * N, lam * N, 1),
                                     ("binomiale négative", mu * N,
                                      mu * N + (mu * N) ** 2 / r, 2)):
        z = (X - esp) / np.sqrt(var)
        stat, ddl = float((z ** 2).sum()), len(X) - k_est
        adeq.append(dict(loi=nom_loi, z=z, chi2=stat, ddl=ddl, ratio=stat / ddl,
                         p=float(loi_chi2.sf(stat, ddl))))
    return adeq


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

def build_dans(dossier):
    """Fixe le dossier des images (a appeler quand le rendu ne tourne pas ici)."""
    global BUILD
    BUILD = dossier


def _chemin(fichier):
    """(chemin d'ecriture, chemin relatif tel que typst doit le lire)."""
    os.makedirs(BUILD, exist_ok=True)
    return f"{BUILD}/{fichier}", f"{os.path.basename(BUILD)}/{fichier}"


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
    ans = (d["dt"].iloc[-1] - d["dt"].iloc[0]).days / 365.25
    ax.xaxis.set_major_locator(mdates.YearLocator(max(1, round(ans / 12))))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.margins(x=0)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9)
    ecrire, lire = _chemin(f"serie_{m['nom']}.png")
    fig.tight_layout()
    fig.savefig(ecrire, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return lire


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
    ecrire, lire = _chemin(f"ajust_{m['nom']}.png")
    fig.tight_layout(w_pad=2.5)
    fig.savefig(ecrire, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return lire


def fig_zhist(m, adeq):
    """Histogrammes des residus z_t (tronques a [-5, 5]) vs densite N(0,1)."""
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.2))
    gz = np.linspace(-5, 5, 200)
    for ax, a, coul in zip(axes, adeq, (ORANGE, BLEU)):
        ax.hist(np.clip(a["z"], -5, 5), bins=40, range=(-5, 5), density=True,
                color=coul, alpha=.8)
        ax.plot(gz, norm.pdf(gz), color=ENCRE2, lw=1.1)
        ax.text(0.98, 0.95, "N(0,1)", color=ENCRE2, fontsize=8.5,
                ha="right", va="top", transform=ax.transAxes)
        ax.set_title(f"{a['loi']} — variance des $z_t$ : {fr(a['z'].var())}",
                     fontsize=9.5, color=ENCRE2)
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    ecrire, lire = _chemin(f"zhist_{m['nom']}.png")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(ecrire, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return lire


# ---------------------------------------------------------------------------
# tableaux (markup typst natif : pas d'image, coupable entre deux pages)
# ---------------------------------------------------------------------------

def table_typst(entetes, lignes, aligns, groupes=None, colonnes=None):
    """Markup d'un tableau typst sobre : trois filets horizontaux, sans fond.

    entetes : libelles de colonnes, en markup typst (les maths sont permises) ;
    lignes  : listes de valeurs deja formatees — markup typst, non echappe
              (« *mot* » pour du gras) : n'y passer que du texte maitrise ;
    aligns  : « left » / « right » / « center », un par colonne ;
    groupes : optionnel, liste de (libelle, nb_colonnes) formant une ligne de
              titres groupes au-dessus des entetes (libelle vide = pas de titre) ;
    colonnes: optionnel, specification typst des largeurs (« (1fr, auto, ...) »).
    """
    entete = []
    if groupes:
        cellules, filets, i = [], [], 0
        for lib, n in groupes:
            cellules.append(f"table.cell(colspan: {n}, align: center)[{lib}]")
            if lib:
                filets.append(f"table.hline(start: {i}, end: {i + n}, stroke: 0.4pt)")
            i += n
        entete.append("    " + ", ".join(cellules) + ",")
        entete += [f"    {f}," for f in filets]
    entete.append("    " + ", ".join(f"[{e}]" for e in entetes) + ",")

    corps = [f"  {', '.join(f'[{v}]' for v in l)}," for l in lignes]
    return "\n".join([
        "table(",
        f"  columns: {colonnes or len(entetes)},",
        f"  align: ({', '.join(aligns)}),",
        "  stroke: none,",
        "  inset: (x: 5pt, y: 3.5pt),",
        "  table.header(",
        "    table.hline(stroke: 0.8pt),",
        *entete,
        "    table.hline(stroke: 0.4pt),",
        "  ),",
        *corps,
        "  table.hline(stroke: 0.8pt),",
        ")",
    ])


def bloc_typst(corps):
    """Bloc brut ```{=typst}``` a imprimer depuis un chunk « output: asis »."""
    return "\n\n```{=typst}\n" + corps + "\n```\n\n"


def bloc_tableau(markup, legende):
    """Bloc typst : tableau dans un #figure legende, numerote « Tableau N »."""
    return bloc_typst("#figure(\n  " + markup.replace("\n", "\n  ")
                      + f',\n  caption: [{legende}],\n  kind: "table",'
                      + "\n  supplement: [Tableau],\n)")


def tab_stats(mods):
    """Statistiques observees de X_t par mot, triees par frequence decroissante."""
    lignes = []
    for m in sorted(mods, key=lambda m: -m["mu"]):
        moy, std, disp, sk, ku = moments_obs(m["X"])
        lignes.append([m["lib"], fr(m["lam"] * 1e5), fr(moy), fr(std),
                       f"{disp:.1f}".replace(".", ","), fr(sk), fr(ku)])
    return table_typst(
        ["Mot", "Fréquence (pour $10^5$)", "Moyenne", "Écart-type", "Var/Moy",
         "Skewness", "Kurtosis"],
        lignes, ["left"] + ["right"] * 6,
        groupes=[("", 2), ("Occurrences quotidiennes $X_t$", 5)])


def tab_params(mods):
    """Parametres estimes (lambda ; mu, r) par mot, tries par frequence."""
    lignes = [[m["lib"], fr(m["lam"] * 1e5), fr(m["mu"] * 1e5), fr(m["r"])]
              for m in sorted(mods, key=lambda m: -m["mu"])]
    return table_typst(
        ["Mot", "$hat(lambda)$ (pour $10^5$)", "$hat(mu)$ (pour $10^5$)", "$hat(r)$"],
        lignes, ["left", "right", "right", "right"],
        groupes=[("", 1), ("Poisson", 1), ("Binomiale négative", 2)])


def tab_moments(m, k, pois, nb):
    """Moments observes vs lois ajustees pour un mot."""
    sources = [("*observé*", moments_obs(m["X"])), ("Poisson", moments_pmf(pois, k)),
               ("binomiale négative", moments_pmf(nb, k))]
    lignes = [[nom] + [fr(v) for v in vals] for nom, vals in sources]
    lignes[0] = [lignes[0][0]] + [f"*{v}*" for v in lignes[0][1:]]
    return table_typst(
        ["Source", "Moyenne", "Écart-type", "Var/Moy", "Skewness", "Kurtosis"],
        lignes, ["left"] + ["right"] * 5)


def tab_chi2(m, adeq):
    """Chi2, ddl, ratio et p-valeur des deux lois pour un mot."""
    lignes = [[a["loi"], f"{a['chi2']:,.0f}".replace(",", " "), str(a["ddl"]),
               fr(a["ratio"]), fr_p(a["p"])] for a in adeq]
    return table_typst(["Loi", "$chi^2$", "ddl", "$chi^2$/ddl", "p-valeur"],
                       lignes, ["left", "right", "right", "right", "right"])


def tab_recueil(fiches):
    """Synthese d'un groupe du recueil : un mot par ligne, parametres et adequation.

    fiches : liste de couples (m, adeq) dans l'ordre d'affichage voulu. Tableau
    large : a poser hors #figure pour qu'il puisse se couper entre deux pages.
    """
    lignes = []
    for m, adeq in fiches:
        d = m["d"]
        pics = d[d["p_t"] < SEUIL]
        pire = pics.loc[pics["p_t"].idxmin(), "dt"].strftime("%d/%m/%Y") if len(pics) else "—"
        lignes.append([m["lib"], m["per"], fr(m["lam"] * 1e5), fr(m["mu"] * 1e5),
                       fr(m["r"]), str(len(pics)), pire, fr(adeq[0]["ratio"]),
                       fr(adeq[1]["ratio"]), fr_p_bref(adeq[1]["p"])])
    return table_typst(
        ["Mot", "Période", "$hat(lambda)$ ($10^5$)", "$hat(mu)$ ($10^5$)", "$hat(r)$",
         "Pics", "Jour le plus anormal", "$chi^2$/ddl (P)", "$chi^2$/ddl (NB)", "p (NB)"],
        lignes,
        ["left", "center"] + ["right"] * 4 + ["center"] + ["right"] * 3,
        colonnes="(1.7fr, 1.2fr, 1fr, 1fr, .7fr, .7fr, 1.5fr, 1fr, 1fr, .9fr)")


def tab_pics(mods):
    """Tous les jours anormaux (p < seuil), tries par surprise decroissante."""
    lignes = []
    for m in mods:
        d = m["d"]
        for _, x in d[d["p_t"] < SEUIL].iterrows():
            lignes.append((-np.log10(x["p_t"]),
                           [f"*{m['lib']}*", x["dt"].strftime("%d/%m/%Y"),
                            str(int(x["X_t"])), f"{x['f_t']:.1f}".replace(".", ",")]))
    lignes.sort(key=lambda t: -t[0])
    return table_typst(
        ["Mot", "Date", "$X_t$", "$f_t$ (pour $10^5$)", "Surprise $-log_10(p_t)$"],
        [l + [f"{s:.1f}".replace(".", ",")] for s, l in lignes],
        ["left", "center", "right", "right", "right"])
