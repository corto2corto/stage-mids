"""Etape 1 - Indicateurs descriptifs des series d'occurrences (Le Monde, 2020-2024).

Pour chaque mot : moments empiriques de X_t (moyenne, ecart-type, dispersion,
skewness, kurtosis) par periode (global + par annee) + une figure de la serie.
Sortie : un PDF LaTeX propre (indicateurs.pdf).

Rien n'est ajuste ici (pas de loi, pas de p-valeur) : purement descriptif.
"""
import os, shutil, subprocess
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ICI = "paper/donnees_maths"
BUILD = f"{ICI}/build_indic"
os.makedirs(BUILD, exist_ok=True)

# nom de fichier -> libelle affiche (avec accents)
MOTS = {
    "president":    "président",
    "gouvernement": "gouvernement",
    "guerre":       "guerre",
    "climat":       "climat",
    "economie":     "économie",
    "inflation":    "inflation",
}

PERIODES = [("2020–2024", 20200101, 20241231)] + [
    (str(a), a*10000 + 101, a*10000 + 1231) for a in range(2020, 2025)
]

BLEU, GRIS = "#1f4e79", "#c9ced6"


def charger(nom):
    d = pd.read_csv(f"{ICI}/{nom}_lemonde.csv")
    d["dt"] = pd.to_datetime(d["date"], format="%Y%m%d")
    d["f"] = 1e5 * d["X_t"] / d["N_t"]        # occurrences pour 100 000 mots
    return d


def moments(sub):
    """Indicateurs descriptifs de X_t sur un sous-ensemble de jours."""
    x = sub["X_t"]
    moy, var = x.mean(), x.var(ddof=1)
    return {
        "jours": len(sub),
        "moy": moy,
        "std": x.std(ddof=1),
        "disp": var / moy if moy else np.nan,      # variance / moyenne (Poisson -> 1)
        "skew": x.skew(),
        "kurt": x.kurt(),                          # exces (loi normale -> 0)
        "freq": 1e5 * sub["X_t"].sum() / sub["N_t"].sum(),
    }


def figure_serie(d, libelle, chemin):
    fig, ax = plt.subplots(figsize=(9, 2.7))
    ax.plot(d["dt"], d["f"], lw=.5, color=GRIS, label="quotidien")
    mm = d["f"].rolling(7, center=True, min_periods=1).mean()
    ax.plot(d["dt"], mm, lw=1.2, color=BLEU, label="moyenne 7 jours")
    ax.set_ylabel("pour 100 000 mots", fontsize=8)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=8)
    ax.grid(True, axis="y", lw=.4, alpha=.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc="upper left", ncol=2)
    ax.margins(x=0)
    fig.tight_layout()
    fig.savefig(chemin, bbox_inches="tight")
    plt.close(fig)


def fmt(v, n=2):
    return "—" if pd.isna(v) else f"{v:,.{n}f}".replace(",", "\\,")


def tableau_latex(lignes):
    """lignes : liste de (label_periode, dict moments)."""
    out = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
           r"Période & Jours & Moyenne & Écart-type & Var/Moy & Skewness & Kurtosis & Fréq. (pour $10^5$) \\",
           r"\midrule"]
    for i, (lab, m) in enumerate(lignes):
        if i == 1:
            out.append(r"\midrule")
        gras = (lambda s: rf"\textbf{{{s}}}") if i == 0 else (lambda s: s)
        out.append(" & ".join([
            gras(lab), gras(f"{m['jours']}"), gras(fmt(m['moy'])), gras(fmt(m['std'])),
            gras(fmt(m['disp'], 1)), gras(fmt(m['skew'])), gras(fmt(m['kurt'])),
            gras(fmt(m['freq'])),
        ]) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out)


# ---- construction du document ----
donnees = {nom: charger(nom) for nom in MOTS}
# tri des mots par frequence globale decroissante
ordre = sorted(MOTS, key=lambda n: -donnees[n]["X_t"].sum() / donnees[n]["N_t"].sum())

corps = []

# 1) tableau de synthese (periode globale, tous les mots)
synth = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
         r"Mot & Jours & Moyenne & Écart-type & Var/Moy & Skewness & Kurtosis & Fréq. (pour $10^5$) \\",
         r"\midrule"]
for nom in ordre:
    m = moments(donnees[nom])
    synth.append(" & ".join([
        MOTS[nom], f"{m['jours']}", fmt(m['moy']), fmt(m['std']),
        fmt(m['disp'], 1), fmt(m['skew']), fmt(m['kurt']), fmt(m['freq']),
    ]) + r" \\")
synth += [r"\bottomrule", r"\end{tabular}"]
corps.append(r"\section*{Vue d'ensemble --- période 2020--2024}" +
             "\n\\begin{center}\\small\n" + "\n".join(synth) + "\n\\end{center}")

# 2) une section par mot
for nom in ordre:
    d = donnees[nom]
    fig_path = f"{BUILD}/fig_{nom}.pdf"
    figure_serie(d, MOTS[nom], fig_path)
    lignes = [(lab, moments(d[(d.date >= a) & (d.date <= b)])) for lab, a, b in PERIODES]
    corps.append(
        rf"\section*{{{MOTS[nom]}}}" + "\n"
        rf"\begin{{center}}\includegraphics[width=\linewidth]{{fig_{nom}.pdf}}\end{{center}}" + "\n"
        r"\begin{center}\small" + "\n" + tableau_latex(lignes) + "\n\\end{center}"
    )

INTRO = r"""Occurrences quotidiennes de six mots dans \emph{Le Monde} sur 2020--2024
(source : base d'unigrammes, grille complète de 1\,827 jours, jours d'absence comptés~0).
On note $X_t$ le nombre d'occurrences du mot le jour~$t$, $N_t$ le nombre total de mots
ce jour-là, et $f_t = X_t/N_t$ la fréquence. Cette première étape est purement
\textbf{descriptive} : on calcule les moments empiriques de $X_t$ (aucune loi n'est encore
ajustée). Les figures montrent la fréquence $f_t$ (ramenée à 100\,000 mots, lissée sur 7~jours)
pour la lisibilité ; les tableaux portent sur le comptage brut $X_t$, la quantité modélisée.
Le rapport \emph{Var/Moy} (indice de dispersion) vaudrait~1 pour une loi de Poisson."""

doc = r"""\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[french]{babel}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{mathptmx}
\usepackage[margin=2cm]{geometry}
\graphicspath{{.}}
\setlength{\parindent}{0pt}
\title{\vspace{-1.5cm}Indicateurs descriptifs des séries d'occurrences}
\author{Le Monde, 2020--2024 --- étape 1}
\date{}
\begin{document}
\maketitle
""" + INTRO + "\n\n" + "\n\n\\bigskip\n\n".join(corps) + "\n\\end{document}\n"

with open(f"{BUILD}/rapport.tex", "w") as f:
    f.write(doc)

# ---- compilation ----
env = dict(os.environ, PATH="/Library/TeX/texbin:" + os.environ.get("PATH", ""))
r = subprocess.run(
    ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "rapport.tex"],
    cwd=BUILD, env=env, capture_output=True, text=True,
)
if r.returncode != 0:
    print(r.stdout[-2500:])
    raise SystemExit("Echec compilation LaTeX (voir build_indic/rapport.log)")

shutil.copy(f"{BUILD}/rapport.pdf", f"{ICI}/indicateurs.pdf")
print("OK ->", f"{ICI}/indicateurs.pdf")
