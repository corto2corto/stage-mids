"""Détection de « spikes » : seuil = quantile de la loi ajustée sur le mot.

Remplace l'ancien detecter_spike.py, qui prenait le quantile empirique des
fréquences observées — un seuil sans modèle, contaminé par les spikes
eux-mêmes. Ici on suit la mécanique validée de rupture/pics.py :

1. ajuster la loi sur la série du mot, avec le volume publié N_t en exposition
   bnb (défaut) : X = 0 avec proba p0, sinon X = 1 + NB(mu_b * N_t, r_b) — les
                  jours à zéro, très nombreux, sont portés par la Bernoulli au
                  lieu de casser l'ajustement de la NB
   nb            : X ~ NB(mu * N_t, r)
2. double fit (fits=2, défaut) : retirer les fenêtres évidentes (p < 1e-6),
   réajuster sur le reste, recalculer les p-valeurs sous la loi purifiée
3. seuil = quantile q de CETTE loi, fenêtre par fenêtre (la moyenne suit le
   volume publié)
       nb  : ppf(q, r, r / (r + mu * N_t))
       bnb : 0 si q <= p0, sinon 1 + ppf((q - p0) / (1 - p0), r_b, ...)
         — la masse en zéro consomme p0 du quantile avant d'entamer la NB

Le quantile et la p-valeur sont les deux écritures du même test : X_t au-delà
du quantile 1 - alpha équivaut à p_t = P(X >= X_t) < alpha. Le défaut q =
0,9999 est donc le seuil de détection acté du projet (1e-4).

Sortie : le texte pour chaque taille de fenêtre, plus un PNG pour les fenêtres
de 1 et 7 jours dans exploration/figures/ — série temporelle et courbe de seuil
à gauche, histogramme des fréquences avec la densité ajustée à droite.

Lancement (Mac ou serveur) — 1 à 3 mots (guillemets si plusieurs) :
    python -m exploration.detecter_spike_V2 lemonde inflation
    python -m exploration.detecter_spike_V2 lemonde "république française" 0.9999 1,2,3,7 nb 1
"""

import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # rendu vers fichier, pas d'écran sur le serveur
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import nbinom

from rupture import pics, serie

BLEU, ROUGE = "#2a78d6", "#d03b3b"
ENCRE, GRIS, GRILLE, FOND = "#52514e", "#898781", "#e1e0d9", "#fcfcfb"

corpus = sys.argv[1]
mot = sys.argv[2]
quantile = float(sys.argv[3]) if len(sys.argv) > 3 else 0.9999
fenetres = [int(k) for k in (sys.argv[4] if len(sys.argv) > 4 else "1,2,3,7").split(",")]
loi = sys.argv[5] if len(sys.argv) > 5 else "bnb"
fits = int(sys.argv[6]) if len(sys.argv) > 6 else 2
if loi not in ("nb", "bnb"):
    sys.exit("loi : nb ou bnb")

try:
    d = serie.charger(mot, corpus)  # tokenisation, graphies OCR et zéros gérés là
except ValueError as e:
    sys.exit(str(e))

df = d.set_index("dt")[["X_t", "N_t"]]
# calendrier continu : les jours sans données comptent 0 (fenêtres vides retirées plus bas)
df = df.reindex(pd.date_range(df.index.min(), df.index.max()), fill_value=0)
print(f"{corpus} — « {mot} » : {int(df['X_t'].sum())} occurrences, "
      f"du {df.index.min():%Y-%m-%d} au {df.index.max():%Y-%m-%d}")

dossier = Path("exploration/figures")
dossier.mkdir(parents=True, exist_ok=True)
slug = re.sub(r"\W", "_", mot.lower())

for k in fenetres:
    roule = df.rolling(k).sum().dropna()  # fenêtre = les k jours qui finissent à la date indexée
    roule = roule[roule["N_t"] > 0]       # fenêtre sans un mot publié : rien à tester
    X, N = roule["X_t"].to_numpy(), roule["N_t"].to_numpy()

    params, p, garde = pics.ajuster(X, N, loi, fits)
    if loi == "nb":
        mu, r = params["mu"], params["r"]
        seuil = nbinom.ppf(quantile, r, r / (r + mu * N))
        aff = f"mu={mu * 1e5:.2f} / 100 000, r={r:.2f}"
    else:
        p0, mu_b, r_b = params["p0"], params["mu_b"], params["r_b"]
        reste = (quantile - p0) / (1 - p0)  # ce qu'il reste du quantile après la masse en 0
        seuil = (1 + nbinom.ppf(reste, r_b, r_b / (r_b + mu_b * N)) if reste > 0
                 else np.zeros(len(N)))
        aff = (f"p0={p0 * 100:.1f}%, mu_b={mu_b * 1e5:.2f} / 100 000, r_b={r_b:.2f}")

    res = pd.DataFrame({"X": X, "N": N, "seuil": seuil, "f": X / N * 1e5,
                        "seuil_f": seuil / N * 1e5, "p": p}, index=roule.index)
    spikes = res[res["X"] > res["seuil"]].sort_values("p")
    adeq = pics.adequation(X, N, loi, params, garde)
    retires = len(X) - int(garde.sum())

    print(f"\n--- fenêtre {k} jour(s) : {len(X)} fenêtres | {loi} ajustée {aff} | "
          f"chi2/ddl={adeq['ratio']:.2f}"
          + (f" | {retires} fenêtres retirées ({fits} fits)" if fits > 1 else "")
          + f" | {len(spikes)} spikes ---")
    print(f"    seuil médian = {res['seuil_f'].median():.2f} / 100 000 "
          f"(quantile {quantile:.4%}), {res['seuil'].median():.0f} occ.")
    for date, ligne in spikes.head(15).iterrows():
        debut = date - pd.Timedelta(days=k - 1)
        periode = f"{date:%Y-%m-%d}" if k == 1 else f"{debut:%Y-%m-%d} → {date:%Y-%m-%d}"
        print(f"  {periode}   {ligne['f']:7.2f} / 100 000   "
              f"({int(ligne['X'])} occ. pour un seuil de {ligne['seuil']:.0f})   "
              f"p = {ligne['p']:.1e}")

    if k not in (1, 7):  # figure pour le jour et la semaine seulement
        continue

    # densité de la loi ajustée, ramenée en fréquence via le volume médian publié
    grille, pmf = pics.densite(X, N, loi, params)
    n_med = np.median(N)
    bords = np.linspace(0, max(res["f"].max(), res["seuil_f"].max()) * 1.02, 61)
    centres = (bords[:-1] + bords[1:]) / 2
    attendu = np.histogram(grille, bins=bords * n_med / 1e5, weights=pmf)[0] * len(X)

    fig, (ax_t, ax_h) = plt.subplots(1, 2, figsize=(12, 4.2), width_ratios=[3.5, 1],
                                     sharey=True, layout="constrained")
    fig.set_facecolor(FOND)
    fig.suptitle(f"« {mot} » — {corpus}, fenêtre de {k} jour(s), seuil {loi}",
                 x=0.02, ha="left", color="#0b0b0b", fontweight="bold")
    ax_t.fill_between(res.index, res["f"], color=BLEU, alpha=0.08, linewidth=0)
    ax_t.plot(res.index, res["f"], color=BLEU, linewidth=1.2,
              solid_capstyle="round", solid_joinstyle="round")
    ax_t.plot(res.index, res["seuil_f"], color=GRIS, linestyle="--", linewidth=1,
              label=f"seuil {loi} (quantile {quantile:.4%})")
    if len(spikes):
        ax_t.scatter(spikes.index, spikes["f"], color=ROUGE, s=26, zorder=3,
                     edgecolors=FOND, linewidths=1.2,
                     label=f"{len(spikes)} fenêtres > seuil")
        pic = spikes.index[0]  # étiquette sur le spike le plus surprenant seulement
        ax_t.annotate(f"{pic:%d %b %Y}", (pic, spikes["f"].iloc[0]),
                      xytext=(6, 3), textcoords="offset points",
                      color=ENCRE, fontsize=8)
    ax_t.legend(frameon=False, labelcolor=ENCRE, fontsize=8)
    ax_t.set_ylabel("fréquence / 100 000 mots", color=ENCRE, fontsize=9)
    ax_t.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(ax_t.xaxis.get_major_locator()))
    ax_t.margins(x=0.01)
    ax_h.hist(res["f"], bins=bords, orientation="horizontal", color=BLEU,
              edgecolor=FOND, linewidth=0.5)
    ax_h.plot(np.where(attendu > 0, attendu, np.nan), centres,
              color=ROUGE, linewidth=1.2, label=f"{loi} ajustée")
    ax_h.axhline(res["seuil_f"].median(), color=GRIS, linestyle="--", linewidth=1)
    ax_h.set_xscale("log")
    ax_h.set_xlabel("nombre de fenêtres (log)", color=ENCRE, fontsize=9)
    ax_h.legend(frameon=False, labelcolor=ENCRE, fontsize=8)
    for ax in (ax_t, ax_h):
        ax.set_facecolor(FOND)
        ax.grid(axis="y", color=GRILLE, linewidth=0.5)
        ax.tick_params(colors=GRIS, labelsize=8)
        for cote in ax.spines.values():
            cote.set_color(GRILLE)
        ax.spines[["top", "right"]].set_visible(False)
    chemin = dossier / f"spikeV2_{corpus}_{slug}_{k}j_{loi}{fits}.png"
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    print(f"  figure : {chemin}")
