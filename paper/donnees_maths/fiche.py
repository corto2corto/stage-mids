"""Fiche d'un mot : meme rendu que les pages mot-par-mot de rapport.pdf.

Usage : python paper/donnees_maths/fiche.py <slug> [debut] [fin]
        (dates YYYYMMDD ; defaut 20200101 20241231)
Le CSV paper/donnees_maths/<slug>_lemonde.csv doit exister (skill fiche-mot).
Sortie : paper/donnees_maths/fiches/fiche_<slug>_<debut>_<fin>.pdf — une page A4
portrait Quarto/typst, figures et tableau produits par rapport_lib comme rapport.qmd.
"""
import os, shutil, subprocess, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy.stats import nbinom
from statsmodels.discrete.discrete_model import NegativeBinomial
from rapport_lib import MOTS, SEUIL, melanges, fig_serie, fig_ajustement, tab_moments

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

# --- figures et tableau, via les memes fonctions que rapport.qmd ---
m = {"nom": slug, "lib": lib, "d": d, "X": X, "N": N, "lam": lam, "mu": mu, "r": r}
k, pois, nb = melanges(m)
c_serie = fig_serie(m)
c_ajust = fig_ajustement(m, k, pois, nb)
c_moments = tab_moments(m, k, pois, nb)

# --- page Quarto/typst, memes options et memes legendes que rapport.qmd ---
if (d1 % 10000, d2 % 10000) == (101, 1231):
    per = str(d1)[:4] if d1 // 10000 == d2 // 10000 else f"{str(d1)[:4]}–{str(d2)[:4]}"
else:
    per = f"{d1}–{d2}"
fr = lambda v: f"{v:,.2f}".replace(",", " ").replace(".", ",")

qmd = f"""---
title: "*{lib}* dans *Le Monde*, {per}"
subtitle: "Série, ajustements Poisson / binomiale négative, jours anormaux détectés"
date: today
lang: fr
format:
  typst:
    papersize: a4
    margin:
      x: 2.2cm
      y: 2.2cm
    fontsize: 11pt
    toc: false
---

Ajustement sur {len(d)} jours : $\\hat\\lambda$ = {fr(lam * 1e5)} et
$\\hat\\mu$ = {fr(mu * 1e5)} pour 100 000 mots ; $\\hat r$ = {fr(r)} ;
{len(pics)} {'jours anormaux' if len(pics) > 1 else 'jour anormal'}
($p_t < 10^{{-4}}$ sous la loi NB du jour).

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
if len(pics):
    print(pics[["date", "X_t", "p_t"]].to_string(index=False))
print("->", os.path.relpath(sortie))
