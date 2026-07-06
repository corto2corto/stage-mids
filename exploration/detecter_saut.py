"""Détection de « sauts » : variations anormales de la fréquence d'un mot d'une
fenêtre à la suivante, vers le haut comme vers le bas.

Méthode : au lieu de la fréquence X(t) (cf. detecter_spike), on regarde le
différentiel D(t) = X(t) - X(t-k), soit l'écart entre la fenêtre de k jours qui
finit en t et la fenêtre précédente (disjointe). Pour k = 1, c'est exactement
X(t) - X(t-1). D peut être négatif : la distribution empirique de D donne donc
deux seuils — le quantile haut (ex. 99,9 %) pour les hausses brutales, le
quantile bas symétrique (0,1 %) pour les chutes brutales. Une chute anormale
peut s'interpréter comme une invisibilisation du sujet.

Sortie : le texte ci-dessous, plus un PNG par taille de fenêtre dans
exploration/figures/ — série temporelle du différentiel à gauche, histogramme
de sa distribution à droite, les deux seuils en pointillé.

Lancement (serveur) — 1 à 3 mots (guillemets si plusieurs) :
    python -m exploration.detecter_saut lemonde inflation
    python -m exploration.detecter_saut lemonde "république française" 0.995 1,2,3,7
"""

import re
import sys
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # rendu vers fichier, pas d'écran sur le serveur
import matplotlib.pyplot as plt
import pandas as pd

BLEU, ROUGE, VIOLET = "#2a78d6", "#d03b3b", "#7a4fd0"
ENCRE, GRIS, GRILLE, FOND = "#52514e", "#898781", "#e1e0d9", "#fcfcfb"

corpus = sys.argv[1]
mot = sys.argv[2]
quantile = float(sys.argv[3]) if len(sys.argv) > 3 else 0.99
fenetres = [int(k) for k in (sys.argv[4] if len(sys.argv) > 4 else "1,2,3,7").split(",")]

# même normalisation qu'à la construction des bases (cf. api/app.py)
mot = re.sub(r"(?<=[A-Z])\.", "", mot).lower().replace("’", "'")
mots = mot.split()
if len(mots) > 3:
    sys.exit("3 mots maximum (unigram, bigram ou trigram)")
table = {1: "unigram", 2: "bigram", 3: "trigram"}[len(mots)]

conn = sqlite3.connect(f"file:/data/elias/stage-mids/data/corpus/{corpus}_ngram.db?mode=ro",
                       uri=True)
ids = []
for m in mots:
    ligne = conn.execute("SELECT id FROM token WHERE word = ?", (m,)).fetchone()
    if ligne is None:
        sys.exit(f"« {m} » absent de la base {corpus}")
    ids.append(ligne[0])
condition = " AND ".join(f"w{i} = ?" for i in range(1, len(mots) + 1))
totaux = pd.read_sql_query(f"SELECT date, total FROM total_{table}", conn)
serie = pd.read_sql_query(f"SELECT date, n FROM {table} WHERE {condition}", conn, params=ids)
conn.close()

df = totaux.merge(serie, on="date", how="left").fillna({"n": 0})
df.index = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
# calendrier continu : les jours sans données comptent 0 (fenêtres vides retirées plus bas)
df = df[["n", "total"]].reindex(pd.date_range(df.index.min(), df.index.max()), fill_value=0)
print(f"{corpus} — « {mot} » : {int(df['n'].sum())} occurrences, "
      f"du {df.index.min():%Y-%m-%d} au {df.index.max():%Y-%m-%d}")

dossier = Path("exploration/figures")
dossier.mkdir(parents=True, exist_ok=True)
slug = re.sub(r"\W", "_", mot)

for k in fenetres:
    roule = df.rolling(k).sum()  # fenêtre = les k jours qui finissent à la date indexée
    f = (roule["n"] / roule["total"] * 1e5).dropna()  # fréquence pour 100 000 mots
    d = f.diff(k).dropna()  # fenêtre courante moins la fenêtre précédente (disjointe)
    seuil_haut, seuil_bas = d.quantile(quantile), d.quantile(1 - quantile)
    hausses = d[d > seuil_haut].sort_values(ascending=False)
    baisses = d[d < seuil_bas].sort_values()
    print(f"\n--- fenêtre {k} jour(s) : seuils = {seuil_bas:+.2f} / {seuil_haut:+.2f} "
          f"pour 100 000 (quantiles {1 - quantile:.1%} et {quantile:.1%}) ---")
    print(f"  {len(hausses)} sauts vers le haut :")
    for date, valeur in hausses.head(15).items():
        print(f"    {date:%Y-%m-%d}   {valeur:+7.2f} / 100 000")
    print(f"  {len(baisses)} sauts vers le bas :")
    for date, valeur in baisses.head(15).items():
        print(f"    {date:%Y-%m-%d}   {valeur:+7.2f} / 100 000")

    # figure : série temporelle du différentiel + histogramme, les deux seuils
    fig, (ax_t, ax_h) = plt.subplots(1, 2, figsize=(12, 4), width_ratios=[3, 1],
                                     sharey=True, layout="constrained")
    fig.set_facecolor(FOND)
    fig.suptitle(f"« {mot} » — {corpus}, différentiel sur fenêtres de {k} jour(s)",
                 color="#0b0b0b")
    ax_t.plot(d.index, d, color=BLEU, linewidth=1.5)
    if len(hausses):
        ax_t.scatter(hausses.index, hausses, color=ROUGE, s=18, zorder=3,
                     label=f"{len(hausses)} sauts > {seuil_haut:+.2f}")
    if len(baisses):
        ax_t.scatter(baisses.index, baisses, color=VIOLET, s=18, zorder=3,
                     label=f"{len(baisses)} sauts < {seuil_bas:+.2f}")
    ax_t.axhline(seuil_haut, color=GRIS, linestyle="--", linewidth=1)
    ax_t.axhline(seuil_bas, color=GRIS, linestyle="--", linewidth=1)
    ax_t.axhline(0, color=GRILLE, linewidth=1)
    ax_t.legend(frameon=False, labelcolor=ENCRE)
    ax_t.set_ylabel("Δ fréquence / 100 000 mots", color=ENCRE)
    ax_h.hist(d, bins=60, orientation="horizontal", color=BLEU,
              edgecolor=FOND, linewidth=0.5)
    ax_h.axhline(seuil_haut, color=GRIS, linestyle="--", linewidth=1)
    ax_h.axhline(seuil_bas, color=GRIS, linestyle="--", linewidth=1)
    ax_h.set_xscale("log")
    ax_h.set_xlabel("nombre de fenêtres (log)", color=ENCRE)
    for ax in (ax_t, ax_h):
        ax.set_facecolor(FOND)
        ax.grid(axis="y", color=GRILLE, linewidth=0.5)
        ax.tick_params(colors=GRIS, labelsize=8)
        for cote in ax.spines.values():
            cote.set_color(GRILLE)
        ax.spines[["top", "right"]].set_visible(False)
    chemin = dossier / f"saut_{corpus}_{slug}_{k}j.png"
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    print(f"  figure : {chemin}")
