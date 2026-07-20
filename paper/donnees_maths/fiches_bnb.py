"""Fiches Bern-NB : 20 mots dans Le Monde sur toute la serie (1944-2025).

Compare TROIS lois ajustees jour par jour (exposure = N_t) :
  - Poisson (forme fermee),
  - binomiale negative (statsmodels),
  - Bernoulli x NB decalee (melange : X=0 avec proba p0, sinon 1 + NB).

Produit UN PDF multi-pages fiches_bnb.pdf (une page de synthese + une page par
mot), un CSV recapitulatif machine, et une ligne stdout par mot. Meme mecanique
que fiche.py : sys.path + rapport_lib, .qmd -> quarto render -> PDF typst.

Usage : python paper/donnees_maths/fiches_bnb.py
"""
import os, subprocess, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from great_tables import GT, style, loc
from scipy.stats import chi2 as loi_chi2, poisson, nbinom, norm
from statsmodels.discrete.discrete_model import NegativeBinomial
from rapport_lib import (BUILD, SEUIL, BLEU, ORANGE, ROUGE, GRIS, GRILLE, ENCRE2,
                         moments_obs, moments_pmf, _style, _sauver)

ICI = os.path.dirname(os.path.abspath(__file__))
VERT = "#2f9e6e"                                  # couleur de la loi Bern-NB

# 20 mots (slug -> libelle accentue pour l'affichage)
MOTS = {
    "chomage": "chômage", "covid": "covid", "guerre": "guerre",
    "immigration": "immigration", "mitterrand": "Mitterrand", "chirac": "Chirac",
    "attentat": "attentat", "retraite": "retraite", "greve": "grève",
    "sida": "sida", "gouvernement": "gouvernement", "president": "président",
    "inflation": "inflation", "economie": "économie", "climat": "climat",
    "europe": "Europe", "ukraine": "Ukraine", "terrorisme": "terrorisme",
    "internet": "internet", "cancer": "cancer",
}

fr = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",")
fr_p = lambda p: "≈ 0" if p < 1e-15 else f"{p:.1e}".replace(".", ",")


# --- densites-melange : moyenne des pmf du jour sur les vrais N_t, par blocs ---
# grille plafonnee a 30000 points ; blocs de 2000 jours pour borner la memoire.

def grille_k(X):
    k1 = int(X.max() * 1.3) + 6
    k0 = max(0, k1 - 30000)
    return np.arange(k0, k1)


def melange_pois(k, N, lam):
    acc = np.zeros(len(k))
    for i in range(0, len(N), 2000):
        acc += poisson.pmf(k[:, None], (lam * N[i:i + 2000])[None, :]).sum(1)
    return acc / len(N)


def melange_nb(k, N, mu, r):
    acc = np.zeros(len(k))
    for i in range(0, len(N), 2000):
        p = r / (r + mu * N[i:i + 2000])
        acc += nbinom.pmf(k[:, None], r, p[None, :]).sum(1)
    return acc / len(N)


def melange_bnb(k, N, p0, mu_b, r_b):
    out = np.zeros(len(k))
    ks = k[k >= 1] - 1                            # partie NB decalee (k >= 1)
    acc = np.zeros(len(ks))
    for i in range(0, len(N), 2000):
        p = r_b / (r_b + mu_b * N[i:i + 2000])
        acc += nbinom.pmf(ks[:, None], r_b, p[None, :]).sum(1)
    out[k >= 1] = (1 - p0) * acc / len(N)
    if k[0] == 0:
        out[0] += p0                             # masse ponctuelle en 0
    return out


# --- figures (fonctions locales : rapport_lib n'est pas modifie) ---

def fig_serie(slug, lib, d):
    """Serie f_t + moyenne mobile 7 j ; jours anormaux sous Bern-NB en rouge."""
    fig, ax = plt.subplots(figsize=(10, 2.9))
    ax.plot(d["dt"], d["f_t"], lw=.4, color=GRIS, label="quotidien")
    mm = d["f_t"].rolling(7, center=True, min_periods=1).mean()
    ax.plot(d["dt"], mm, lw=1.2, color=BLEU, label="moyenne mobile 7 j")
    pics = d[d["p_bnb"] < SEUIL]
    ax.scatter(pics["dt"], pics["f_t"], s=10, color=ROUGE, zorder=3,
               label="jour anormal ($p_t < 10^{-4}$, Bern-NB)")
    ax.set_ylabel("$f_t$ (pour 100 000 mots)")
    ax.set_ylim(0, d["f_t"].max() * 1.12)
    ax.xaxis.set_major_locator(mdates.YearLocator(10))     # tick tous les 10 ans
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, axis="y", lw=.5, color=GRILLE)
    ax.set_axisbelow(True)
    ax.margins(x=0)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9)
    chemin = f"{BUILD}/bnb_serie_{slug}.png"
    fig.tight_layout()
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return f"build_rapport/bnb_serie_{slug}.png"


def fig_hist(slug, X, k, pois, nb, bnb, p_actifs, n_pics):
    """Histogramme de X_t + 3 densites ; p-valeurs Bern-NB des jours actifs."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.1), width_ratios=[1.45, 1])
    a1.hist(X, bins=np.arange(0, k[-1] + 2) - 0.5, density=True, color=GRIS,
            label="données")
    a1.plot(k, pois, color=ORANGE, lw=1.5, label="Poisson")
    a1.plot(k, nb, color=BLEU, lw=1.7, label="binomiale négative")
    a1.plot(k, bnb, color=VERT, lw=1.7, label="Bernoulli × NB")
    a1.set_xlim(-0.5, np.percentile(X, 99.5) + max(3, int(0.05 * X.max())))
    a1.set_xlabel("$X_t$ (occurrences/jour)")
    a1.set_ylabel("densité")
    a1.legend(fontsize=9)
    a2.hist(p_actifs, bins=20, range=(0, 1), density=True, color=GRIS)
    a2.axhline(1, color=ENCRE2, lw=1, ls="--")
    a2.text(0.985, 1.0, "uniforme", color=ENCRE2, fontsize=8.5,
            ha="right", va="bottom", transform=a2.get_yaxis_transform())
    a2.set_xlabel("$p_t$ Bern-NB (jours actifs)")
    a2.set_title(f"{n_pics} jour{'s' if n_pics > 1 else ''} sous $10^{{-4}}$",
                 fontsize=9.5, color=ENCRE2)
    for ax in (a1, a2):
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    chemin = f"{BUILD}/bnb_ajust_{slug}.png"
    fig.tight_layout(w_pad=2.5)
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return f"build_rapport/bnb_ajust_{slug}.png"


def fig_zhist(slug, zs):
    """3 panneaux : histogrammes des residus z_t (clip +-5) vs N(0,1)."""
    fig, axes = plt.subplots(1, 3, figsize=(10, 2.3))
    gz = np.linspace(-5, 5, 200)
    for ax, (nom, z, coul) in zip(axes, zs):
        ax.hist(np.clip(z, -5, 5), bins=40, range=(-5, 5), density=True,
                color=coul, alpha=.8)
        ax.plot(gz, norm.pdf(gz), color=ENCRE2, lw=1.1)
        ax.text(0.98, 0.95, "N(0,1)", color=ENCRE2, fontsize=8,
                ha="right", va="top", transform=ax.transAxes)
        ax.set_title(f"{nom} — var($z_t$) : {fr(z.var())}", fontsize=8.5,
                     color=ENCRE2)
        ax.grid(True, axis="y", lw=.5, color=GRILLE)
        ax.set_axisbelow(True)
    fig.tight_layout(w_pad=1.4)
    chemin = f"{BUILD}/bnb_zhist_{slug}.png"
    fig.savefig(chemin, bbox_inches="tight", dpi=200)
    plt.close(fig)
    return f"build_rapport/bnb_zhist_{slug}.png"


# --- tableaux great_tables ---

def tab_chi2(slug, adeq):
    df = pd.DataFrame([{"loi": a["loi"], "chi2": a["chi2"], "ddl": a["ddl"],
                        "ratio": a["ratio"], "p": fr_p(a["p"]),
                        "verdict": "rejetée" if a["p"] < 0.05 else "non rejetée"}
                       for a in adeq])
    gt = (
        GT(df, rowname_col="loi")
        .cols_label(chi2="χ²", ddl="ddl", ratio="χ²/ddl", p="p-valeur",
                    verdict="verdict")
        .fmt_number(columns=["chi2"], decimals=0, locale="fr")
        .fmt_number(columns=["ratio"], decimals=2, locale="fr")
        .cols_align(align="right", columns=["chi2", "ddl", "ratio", "p"])
        .tab_stubhead(label="Loi")
    )
    return _sauver(_style(gt), f"bnb_chi2_{slug}", vwidth=1250)


def tab_moments(slug, X, k, pois, nb, bnb):
    rows = [("observé", *moments_obs(X)),
            ("Poisson", *moments_pmf(pois, k)),
            ("binomiale négative", *moments_pmf(nb, k)),
            ("Bernoulli × NB", *moments_pmf(bnb, k))]
    df = pd.DataFrame(rows, columns=["source", "moy", "std", "disp", "skew", "kurt"])
    gt = (
        GT(df, rowname_col="source")
        .cols_label(moy="Moyenne", std="Écart-type", disp="Var/Moy",
                    skew="Skewness", kurt="Kurtosis")
        .fmt_number(columns=["moy", "std", "disp", "skew", "kurt"], decimals=2,
                    locale="fr")
        .cols_align(align="right", columns=["moy", "std", "disp", "skew", "kurt"])
        .tab_stubhead(label="Source")
        .tab_style(style=style.text(weight="bold"), locations=loc.body(rows=[0]))
        .tab_style(style=style.text(weight="bold"), locations=loc.stub(rows=[0]))
    )
    return _sauver(_style(gt), f"bnb_moments_{slug}", vwidth=1150)


def tab_synthese(rows):
    df = pd.DataFrame(rows).sort_values("p0", ascending=False).drop(columns=["slug"])
    df["p0"] = df["p0"] * 100
    gt = (
        GT(df, rowname_col="lib")
        .tab_spanner(label="r", columns=["r", "r_b"])
        .tab_spanner(label="χ²/ddl", columns=["chi2_nb", "chi2_bnb"])
        .tab_spanner(label="Pics", columns=["pics_nb", "pics_bnb"])
        .cols_label(p0="% jours à 0", r="NB", r_b="Bern-NB",
                    chi2_nb="NB", chi2_bnb="Bern-NB",
                    pics_nb="NB", pics_bnb="Bern-NB")
        .fmt_number(columns=["p0"], decimals=1, locale="fr")
        .fmt_number(columns=["r", "r_b"], decimals=2, locale="fr")
        .fmt_number(columns=["chi2_nb", "chi2_bnb"], decimals=1, locale="fr")
        .cols_align(align="right", columns=["p0", "r", "r_b", "chi2_nb",
                                            "chi2_bnb", "pics_nb", "pics_bnb"])
        .tab_stubhead(label="Mot")
    )
    return _sauver(_style(gt), "bnb_synthese", vwidth=1500)


# --- traitement d'un mot ---

def traiter(slug):
    lib = MOTS[slug]
    d = pd.read_csv(f"{ICI}/{slug}_lemonde.csv")
    d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
    d["f_t"] = 1e5 * d["X_t"] / d["N_t"]
    X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()
    T = len(X)

    # 1. Poisson (forme fermee)
    lam = X.sum() / N.sum()

    # 2. NB (statsmodels, exposure = N)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((T, 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, r = np.exp(res.params[0]), 1.0 / res.params[1]
    p_nb = nbinom.sf(X - 1, r, r / (r + mu * N))          # p-valeur du jour, NB

    # 3. Bern-NB : Bernoulli(p0) x NB decalee sur les jours actifs (Y = X - 1)
    p0 = float((X == 0).mean())
    act = X >= 1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rb = NegativeBinomial(X[act] - 1, np.ones((act.sum(), 1)),
                              exposure=N[act]).fit(disp=0, maxiter=300)
    mu_b, r_b = np.exp(rb.params[0]), 1.0 / rb.params[1]
    p_bnb = np.ones(T)                                    # jours a zero -> 1.0
    p_bnb[act] = (1 - p0) * nbinom.sf(X[act] - 2, r_b,
                                     r_b / (r_b + mu_b * N[act]))
    d["p_bnb"] = p_bnb
    pics_nb = int((p_nb < SEUIL).sum())
    pics_bnb = int((p_bnb < SEUIL).sum())

    # --- chi2 de Pearson sur tous les jours (E, V par jour ; ddl = T - k) ---
    # Poisson
    e_p, v_p = lam * N, lam * N
    z_p = (X - e_p) / np.sqrt(v_p)
    # NB
    e_n, v_n = mu * N, mu * N + (mu * N) ** 2 / r
    z_n = (X - e_n) / np.sqrt(v_n)
    # Bern-NB
    m_b = mu_b * N
    v_nb = m_b + m_b ** 2 / r_b
    e_b = (1 - p0) * (1 + m_b)
    v_b = (1 - p0) * (v_nb + (1 + m_b) ** 2) - e_b ** 2
    z_b = (X - e_b) / np.sqrt(v_b)

    adeq = []
    for nom, z, ddl in (("Poisson", z_p, T - 1),
                        ("binomiale négative", z_n, T - 2),
                        ("Bernoulli × NB", z_b, T - 3)):
        stat = float((z ** 2).sum())
        adeq.append(dict(loi=nom, z=z, chi2=stat, ddl=ddl, ratio=stat / ddl,
                         p=float(loi_chi2.sf(stat, ddl))))

    # --- densites-melange sur la grille commune ---
    k = grille_k(X)
    pois = melange_pois(k, N, lam)
    nb = melange_nb(k, N, mu, r)
    bnb = melange_bnb(k, N, p0, mu_b, r_b)

    # --- figures + tableaux ---
    c_serie = fig_serie(slug, lib, d)
    c_hist = fig_hist(slug, X, k, pois, nb, bnb, p_bnb[act], pics_bnb)
    c_zhist = fig_zhist(slug, [("Poisson", z_p, ORANGE), ("NB", z_n, BLEU),
                               ("Bern-NB", z_b, VERT)])
    c_chi2 = tab_chi2(slug, adeq)
    c_moments = tab_moments(slug, X, k, pois, nb, bnb)

    print(f"{lib:14s} T={T} p0={p0*100:4.1f}% | lam={lam*1e5:.2f} mu={mu*1e5:.2f} "
          f"r={r:.2f} | mu_b={mu_b*1e5:.2f} r_b={r_b:.2f} | "
          f"χ²/ddl P={adeq[0]['ratio']:.2f} NB={adeq[1]['ratio']:.2f} "
          f"BNB={adeq[2]['ratio']:.2f} | pics NB={pics_nb} BNB={pics_bnb}")

    entete = (
        f"### *{lib}* — 1944–2025\n\n"
        f"{T} jours, dont {p0*100:.1f} % à zéro. "
        f"Poisson $\\hat\\lambda$ = {fr(lam*1e5)} ; "
        f"NB $\\hat\\mu$ = {fr(mu*1e5)}, $\\hat r$ = {fr(r)} ; "
        f"Bern-NB $\\hat\\mu_b$ = {fr(mu_b*1e5)}, $\\hat r_b$ = {fr(r_b)} "
        f"(fréquences pour 100 000 mots). "
        f"Jours anormaux ($p_t < 10^{{-4}}$) : {pics_nb} sous la NB, "
        f"{pics_bnb} sous Bern-NB.\n"
    )
    page = entete + f"""
```{{=typst}}
#figure(image("{c_serie}", width: 100%),
  caption: [Fréquence quotidienne $f_t$, jours anormaux sous Bern-NB — {lib}])
```

```{{=typst}}
#figure(image("{c_hist}", width: 100%),
  caption: [Histogramme de $X_t$ et 3 densités-mélange (orange Poisson, bleu NB,
    vert Bern-NB) ; p-valeurs Bern-NB des jours actifs — {lib}])
```

```{{=typst}}
#figure(
  grid(columns: (38%, 62%), gutter: 10pt,
    align(horizon, image("{c_chi2}", width: 100%)),
    align(horizon, image("{c_zhist}", width: 100%))),
  caption: [Adéquation — test du χ² sur les résidus de Pearson et histogrammes
    des $z_t$ vs $N(0,1)$ pour les 3 lois — {lib}])
```

```{{=typst}}
#figure(image("{c_moments}", width: 66%),
  caption: [Moments observés et moments des 3 lois ajustées — {lib}],
  kind: "table", supplement: [Tableau])
```
"""
    syn = dict(slug=slug, lib=lib, p0=p0, r=r, r_b=r_b,
               chi2_nb=adeq[1]["ratio"], chi2_bnb=adeq[2]["ratio"],
               pics_nb=pics_nb, pics_bnb=pics_bnb)
    csv = dict(slug=slug, jours=T, p0=round(p0, 4), lam=lam, mu=mu, r=r,
               mu_b=mu_b, r_b=r_b, chi2_ddl_poisson=adeq[0]["ratio"],
               chi2_ddl_nb=adeq[1]["ratio"], chi2_ddl_bnb=adeq[2]["ratio"],
               pics_nb=pics_nb, pics_bnb=pics_bnb)
    return page, syn, csv


# --- boucle sur les 20 mots ---
pages, syns, csvs = [], [], []
for slug in MOTS:
    page, syn, csv = traiter(slug)
    pages.append(page)
    syns.append(syn)
    csvs.append(csv)

c_syn = tab_synthese(syns)

# --- assemblage du .qmd (synthese + 1 page par mot) ---
tete = f"""---
title: "Bernoulli × binomiale négative — 20 mots dans *Le Monde*, 1944–2025"
subtitle: "Trois lois ajustées jour par jour : Poisson, binomiale négative, mélange Bernoulli × NB"
lang: fr
format:
  typst:
    papersize: a4
    margin:
      x: 1.7cm
      y: 1.4cm
    fontsize: 10pt
    toc: false
---

Comparaison de trois lois ajustées sur la série quotidienne complète (26 917 jours,
exposition $N_t$). Le mélange **Bernoulli × NB** sépare la probabilité d'un jour
sans occurrence (Bernoulli, $p_0$) de la loi des jours actifs (NB décalée sur
$X_t - 1$). Le tableau ci-dessous résume les 20 mots (tri par part de jours à zéro
décroissante) ; une page détaillée par mot suit.

```{{=typst}}
#figure(image("{c_syn}", width: 80%),
  caption: [Synthèse des 20 mots — $p_0$, dispersion $r$, adéquation χ²/ddl et
    nombre de jours anormaux, sous NB et sous Bern-NB],
  kind: "table", supplement: [Tableau])
```
"""

corps = "\n".join("\n```{=typst}\n#pagebreak()\n```\n\n" + p for p in pages)
qmd = tete + corps

base = "fiches_bnb"
with open(f"{ICI}/{base}.qmd", "w") as f:
    f.write(qmd)
subprocess.run(["quarto", "render", f"{base}.qmd", "--quiet"], cwd=ICI, check=True)
os.remove(f"{ICI}/{base}.qmd")

# --- CSV recapitulatif machine ---
pd.DataFrame(csvs).to_csv(f"{BUILD}/fiches_bnb_resume.csv", index=False)

print("->", os.path.relpath(f"{ICI}/{base}.pdf"))
print("->", os.path.relpath(f"{BUILD}/fiches_bnb_resume.csv"))
