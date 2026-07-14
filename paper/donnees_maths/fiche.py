"""Fiche d'un mot : meme rendu que les pages mot-par-mot de rapport.pdf.

Usage : python paper/donnees_maths/fiche.py <slug> [debut] [fin]
        (dates YYYYMMDD ; defaut 20200101 20241231)
Le CSV paper/donnees_maths/<slug>_lemonde.csv doit exister (skill fiche-mot).
Sortie : paper/donnees_maths/fiches/fiche_<slug>_<debut>_<fin>.pdf — une page A4
portrait Quarto/typst, figures et tableaux produits par rapport_lib comme rapport.qmd,
plus le test d'adequation du chi2 sur les residus de Pearson (meme calcul que l'API).
"""
import os, shutil, subprocess, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from great_tables import GT
from scipy.stats import chi2 as loi_chi2, nbinom, norm
from statsmodels.discrete.discrete_model import NegativeBinomial
from rapport_lib import (MOTS, SEUIL, BUILD, BLEU, ORANGE, ENCRE2, GRILLE,
                         melanges, fig_serie, fig_ajustement, tab_moments,
                         _style, _sauver)

ICI = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{ICI}/fiches", exist_ok=True)

slug = sys.argv[1]
d1 = int(sys.argv[2]) if len(sys.argv) > 2 else 20200101
d2 = int(sys.argv[3]) if len(sys.argv) > 3 else 20241231
lib = MOTS.get(slug, slug.replace("_", " "))

# --- donnees + ajustements sur la periode (meme logique que rapport_lib.ajuster) ---
d = pd.read_csv(f"{ICI}/{slug}_lemonde.csv")
d = d[(d["date"] >= d1) & (d["date"] <= d2)].reset_index(drop=True)
if len(d) < 60:
    sys.exit(f"periode trop courte ({len(d)} jours) : fit trop fragile sous ~60 jours")
d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
d["f_t"] = 1e5 * d["X_t"] / d["N_t"]
X, N = d["X_t"].to_numpy(), d["N_t"].to_numpy()

lam = X.sum() / N.sum()                          # MLE Poisson (forme fermee)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
mu, r = np.exp(res.params[0]), 1.0 / res.params[1]

d["p_t"] = nbinom.sf(X - 1, r, r / (r + mu * N))     # p-valeur du jour sous la NB
pics = d[d["p_t"] < SEUIL]

# --- test du chi2 sur les residus de Pearson (meme calcul que l'API) ---
# chaque jour est compare a sa propre loi (N_t varie) ; ddl = jours - parametres
adeq = []
for nom_loi, esp, var, k_est in (("Poisson", lam * N, lam * N, 1),
                                 ("binomiale négative", mu * N, mu * N + (mu * N) ** 2 / r, 2)):
    z = (X - esp) / np.sqrt(var)
    stat, ddl = float((z ** 2).sum()), len(X) - k_est
    adeq.append(dict(loi=nom_loi, z=z, chi2=stat, ddl=ddl, ratio=stat / ddl,
                     p=float(loi_chi2.sf(stat, ddl))))

fr = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",")
fr_p = lambda p: "≈ 0" if p < 1e-15 else f"{p:.1e}".replace(".", ",")

# --- figures et tableau, via les memes fonctions que rapport.qmd ---
m = {"nom": slug, "lib": lib, "d": d, "X": X, "N": N, "lam": lam, "mu": mu, "r": r}
k, pois, nb = melanges(m)
c_serie = fig_serie(m)
c_ajust = fig_ajustement(m, k, pois, nb)
c_moments = tab_moments(m, k, pois, nb)

# figure chi2 : histogrammes des z_t (tronques a [-5, 5]) vs densite N(0,1)
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
fig.tight_layout(w_pad=2.0)
fig.savefig(f"{BUILD}/zhist_{slug}.png", bbox_inches="tight", dpi=200)
plt.close(fig)
c_zhist = f"build_rapport/zhist_{slug}.png"

# tableau chi2 (great_tables, meme style que les tableaux du rapport)
df_chi2 = pd.DataFrame([{"loi": a["loi"], "chi2": a["chi2"], "ddl": a["ddl"],
                         "ratio": a["ratio"], "p": fr_p(a["p"]),
                         "verdict": "rejetée" if a["p"] < 0.05 else "non rejetée"}
                        for a in adeq])
gt = (
    GT(df_chi2, rowname_col="loi")
    .cols_label(chi2="χ²", ddl="ddl", ratio="χ²/ddl", p="p-valeur", verdict="verdict")
    .fmt_number(columns=["chi2"], decimals=0, locale="fr")
    .fmt_number(columns=["ratio"], decimals=2, locale="fr")
    .cols_align(align="right", columns=["chi2", "ddl", "ratio", "p"])
    .tab_stubhead(label="Loi")
)
c_chi2 = _sauver(_style(gt), f"chi2_{slug}", vwidth=1250)

# --- page Quarto/typst, memes options et memes legendes que rapport.qmd ---
if (d1 % 10000, d2 % 10000) == (101, 1231):
    per = str(d1)[:4] if d1 // 10000 == d2 // 10000 else f"{str(d1)[:4]}–{str(d2)[:4]}"
else:
    per = f"{d1}–{d2}"

verdict_nb = ("est aussi rejetée" if adeq[1]["p"] < 0.05 else "n'est pas rejetée")
p_nb = "p ≈ 0" if adeq[1]["p"] < 1e-15 else f"p = {fr_p(adeq[1]['p'])}"
qmd = f"""---
title: "*{lib}* dans *Le Monde*, {per}"
subtitle: "Série, ajustements Poisson / binomiale négative, jours anormaux, test du χ²"
lang: fr
format:
  typst:
    papersize: a4
    margin:
      x: 2cm
      y: 1.6cm
    fontsize: 11pt
    toc: false
---

Ajustement sur {len(d)} jours : $\\hat\\lambda$ = {fr(lam * 1e5)} et
$\\hat\\mu$ = {fr(mu * 1e5)} pour 100 000 mots ; $\\hat r$ = {fr(r)} ;
{len(pics)} {'jours anormaux' if len(pics) > 1 else 'jour anormal'}
($p_t < 10^{{-4}}$ sous la loi NB du jour). Le test du χ² sur les résidus de
Pearson rejette la loi de Poisson (χ²/ddl = {fr(adeq[0]["ratio"])}) ; la
binomiale négative {verdict_nb} (χ²/ddl = {fr(adeq[1]["ratio"])}, {p_nb}).

```{{=typst}}
#figure(
  image("{c_serie}", width: 100%),
  caption: [Fréquence quotidienne $f_t$ — {lib}],
)
```

```{{=typst}}
#figure(
  image("{c_ajust}", width: 100%),
  caption: [Histogramme de $X_t$ et lois ajustées ; p-valeurs sous la NB — {lib}],
)
```

```{{=typst}}
#figure(
  grid(columns: (42%, 58%), gutter: 12pt,
    align(horizon, image("{c_chi2}", width: 100%)),
    align(horizon, image("{c_zhist}", width: 100%))),
  caption: [Adéquation — test du χ² sur les résidus de Pearson
    $z_t = (X_t - m_t)\\/sqrt(v_t)$, histogrammes vs loi normale — {lib}],
)
```

```{{=typst}}
#figure(
  image("{c_moments}", width: 72%),
  caption: [Moments observés et moments des lois ajustées — {lib}],
  kind: "table",
  supplement: [Tableau],
)
```
"""

base = f"fiche_{slug}_{d1}_{d2}"
with open(f"{ICI}/{base}.qmd", "w") as f:
    f.write(qmd)
subprocess.run(["quarto", "render", f"{base}.qmd", "--quiet"], cwd=ICI, check=True)
os.remove(f"{ICI}/{base}.qmd")
sortie = f"{ICI}/fiches/{base}.pdf"
shutil.move(f"{ICI}/{base}.pdf", sortie)

print(f"{lib} {per} : {len(d)} jours | lambda={lam*1e5:.2f} mu={mu*1e5:.2f} r={r:.2f} | {len(pics)} pics")
print(f"chi2/ddl Poisson={adeq[0]['ratio']:.2f} p={adeq[0]['p']:.1e} | NB={adeq[1]['ratio']:.2f} p={adeq[1]['p']:.1e}")
if len(pics):
    print(pics[["date", "X_t", "p_t"]].to_string(index=False))
print("->", os.path.relpath(sortie))
