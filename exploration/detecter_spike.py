"""Détection de « spikes » : fenêtres de k jours où un mot est anormalement
fréquent par rapport à son historique.

Méthode : la distribution des fréquences passées du mot (tous les jours de la
base) sert de densité de probabilité empirique ; tout ce qui dépasse son
quantile haut (ex. 99 %) est considéré comme un phénomène extrême. Le même
calcul est refait pour chaque taille de fenêtre (1, 2, 3... jours), chacune
avec sa propre distribution et donc son propre seuil.

Lancement (serveur) :
    python -m exploration.detecter_spike lemonde inflation
    python -m exploration.detecter_spike lemonde inflation 0.995 1,2,3,7
"""

import re
import sys
import sqlite3
import pandas as pd

corpus = sys.argv[1]
mot = sys.argv[2]
quantile = float(sys.argv[3]) if len(sys.argv) > 3 else 0.99
fenetres = [int(k) for k in (sys.argv[4] if len(sys.argv) > 4 else "1,2,3,7").split(",")]

# même normalisation qu'à la construction des bases (cf. api/app.py)
mot = re.sub(r"(?<=[A-Z])\.", "", mot).lower().replace("’", "'")

conn = sqlite3.connect(f"file:/data/elias/stage-mids/data/corpus/{corpus}_ngram.db?mode=ro",
                       uri=True)
ligne = conn.execute("SELECT id FROM token WHERE word = ?", (mot,)).fetchone()
if ligne is None:
    sys.exit(f"« {mot} » absent de la base {corpus}")
totaux = pd.read_sql_query("SELECT date, total FROM total_unigram", conn)
serie = pd.read_sql_query("SELECT date, n FROM unigram WHERE w1 = ?", conn, params=[ligne[0]])
conn.close()

df = totaux.merge(serie, on="date", how="left").fillna({"n": 0})
df.index = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
# calendrier continu : les jours sans données comptent 0 (fenêtres vides retirées plus bas)
df = df[["n", "total"]].reindex(pd.date_range(df.index.min(), df.index.max()), fill_value=0)
print(f"{corpus} — « {mot} » : {int(df['n'].sum())} occurrences, "
      f"du {df.index.min():%Y-%m-%d} au {df.index.max():%Y-%m-%d}")

for k in fenetres:
    roule = df.rolling(k).sum()  # fenêtre = les k jours qui finissent à la date indexée
    f = (roule["n"] / roule["total"] * 1e5).dropna()  # fréquence pour 100 000 mots
    seuil = f.quantile(quantile)
    spikes = f[f > seuil].sort_values(ascending=False)
    print(f"\n--- fenêtre {k} jour(s) : seuil = {seuil:.2f} / 100 000 "
          f"(quantile {quantile:.1%}) — {len(spikes)} fenêtres au-dessus ---")
    for date, valeur in spikes.head(15).items():
        debut = date - pd.Timedelta(days=k - 1)
        periode = f"{date:%Y-%m-%d}" if k == 1 else f"{debut:%Y-%m-%d} → {date:%Y-%m-%d}"
        print(f"  {periode}   {valeur:7.2f} / 100 000   ({int(roule.loc[date, 'n'])} occ.)")
