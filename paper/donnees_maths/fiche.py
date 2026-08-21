"""Fiche d'un mot : meme rendu que les pages mot-par-mot de rapport.pdf.

Usage : python paper/donnees_maths/fiche.py <mot> [debut] [fin]
        (mot accentue ou slug ; dates YYYYMMDD ; defaut 20200101 20241231)
Tout le calcul est dans rupture/fiches.py, partage avec rapport.qmd et
fiches_mots.qmd : serie, ajustements Poisson / NB, jours anormaux, test du chi2
sur les residus de Pearson, tableau des moments.
Sortie : paper/donnees_maths/fiches/fiche_<slug>_<debut>_<fin>.pdf, une page A4
portrait Quarto/typst.
"""
import os, shutil, subprocess, sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(ICI)))    # racine du depot
from rupture import fiches

mot = sys.argv[1]
d1 = int(sys.argv[2]) if len(sys.argv) > 2 else 20200101
d2 = int(sys.argv[3]) if len(sys.argv) > 3 else 20241231

# le rendu quarto tourne dans ICI : les images doivent y etre ecrites
fiches.build_dans(f"{ICI}/build_rapport")
os.makedirs(f"{ICI}/fiches", exist_ok=True)

m = fiches.ajuster(mot, d1, d2)
adeq = fiches.adequation(m)
k, pois, nb = fiches.melanges(m)
d, lib, per = m["d"], m["lib"], m["per"]
pics = d[d["p_t"] < fiches.SEUIL]

c_serie = fiches.fig_serie(m)
c_ajust = fiches.fig_ajustement(m, k, pois, nb)
c_zhist = fiches.fig_zhist(m, adeq)
c_chi2 = fiches.tab_chi2(m, adeq)
c_moments = fiches.tab_moments(m, k, pois, nb)

fr, fr_p = fiches.fr, fiches.fr_p
verdict_nb = "est aussi rejetée" if adeq[1]["p"] < 0.05 else "n'est pas rejetée"
p_nb = "p ≈ 0" if adeq[1]["p"] < 1e-15 else f"p = {fr_p(adeq[1]['p'])}"

# --- page Quarto/typst, memes options et memes legendes que rapport.qmd ---
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

```{{=typst}}
#show table: set par(justify: false)
```

Ajustement sur {len(d)} jours : $\\hat\\lambda$ = {fr(m["lam"] * 1e5)} et
$\\hat\\mu$ = {fr(m["mu"] * 1e5)} pour 100 000 mots ; $\\hat r$ = {fr(m["r"])} ;
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
  grid(columns: (46%, 54%), gutter: 10pt,
    align(horizon)[#set text(size: 8.5pt)
#{c_chi2}],
    align(horizon, image("{c_zhist}", width: 100%))),
  caption: [Adéquation — test du χ² sur les résidus de Pearson
    $z_t = (X_t - m_t)\\/sqrt(v_t)$, histogrammes vs loi normale — {lib}],
  kind: image,
)
```

```{{=typst}}
#figure(
  {c_moments},
  caption: [Moments observés et moments des lois ajustées — {lib}],
  kind: "table",
  supplement: [Tableau],
)
```
"""

base = f"fiche_{m['nom']}_{d1}_{d2}"
with open(f"{ICI}/{base}.qmd", "w") as f:
    f.write(qmd)
subprocess.run(["quarto", "render", f"{base}.qmd", "--quiet"], cwd=ICI, check=True)
os.remove(f"{ICI}/{base}.qmd")
sortie = f"{ICI}/fiches/{base}.pdf"
shutil.move(f"{ICI}/{base}.pdf", sortie)

print(f"{lib} {per} : {len(d)} jours | lambda={m['lam']*1e5:.2f} mu={m['mu']*1e5:.2f} "
      f"r={m['r']:.2f} | {len(pics)} pics")
print(f"chi2/ddl Poisson={adeq[0]['ratio']:.2f} p={adeq[0]['p']:.1e} | "
      f"NB={adeq[1]['ratio']:.2f} p={adeq[1]['p']:.1e}")
if len(pics):
    print(pics[["date", "X_t", "p_t"]].to_string(index=False))
print("->", os.path.relpath(sortie))
