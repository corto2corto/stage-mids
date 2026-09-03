# Vocabulaire ETENDU du corpus unifie : le top-10 000 du Monde (jours actifs sur
# 1944-2025, vocab_lemonde_top10000.csv) complete par le top-K du Monde par
# OCCURRENCES sur 2000-2025 (vocab_lemonde_2000.csv). Le classement par jours
# actifs sur toute l'archive ecarte structurellement le vocabulaire recent
# (ukraine, macron, covid, confinement...) ; le second classement le ramene.
# Les 10 000 premiers mots restent identiques, meme ordre : les colonnes de
# vocab_series_etendu.npz prolongent celles de vocab_series_unifie.npz.
# Memes exclusions que masse.py (mots outils, chiffres, une lettre), pas
# d'absorption OCR (periode recente). Pour les mots ajoutes, jours_actifs et
# total sont ceux de 2000-2025.
# Sorties dans <VOCAB_DIR>/ :
# - vocab_etendu.csv         : mot, cle, jours_actifs, total (top-10 000 puis ajouts)
# - vocab_parlant_etendu.txt : vocab600 du depot + les mots ajoutes de categorie
#   nom / nom propre / adjectif (ou absents de vocab_categories.csv) — filtre
#   des fenetres archetypes des rapports
# Usage (sur gallica) : python -m rupture.vocab_etendu [K]
import os
import sys
import unicodedata

import pandas as pd

from scripts.tokenisation import MOTS_OUTILS

K = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
DOSSIER = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
DEPOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GARDEES = ("nom", "nom_propre", "adj")

base = pd.read_csv(f"{DOSSIER}/vocab_lemonde_top10000.csv",
                   dtype={"mot": str, "cle": str}, keep_default_na=False)
v = pd.read_csv(f"{DOSSIER}/vocab_lemonde_2000.csv", dtype={"mot": str},
                keep_default_na=False)
v = v[~v["mot"].isin(set(MOTS_OUTILS))]
v = v[~v["mot"].str.match(r"[0-9]")]
v = v[v["mot"].str.len() > 1]
v = v[~v["mot"].str.contains("'")]
recent = v.sort_values("total", ascending=False).head(K)
ajouts = recent[~recent["mot"].isin(set(base["mot"]))].copy()
ajouts["cle"] = [unicodedata.normalize("NFD", m).encode("ascii", "ignore").decode()
                 for m in ajouts["mot"]]
etendu = pd.concat([base, ajouts[["mot", "cle", "jours_actifs", "total"]]],
                   ignore_index=True)
etendu.to_csv(f"{DOSSIER}/vocab_etendu.csv", index=False)

cat = pd.read_csv(f"{DEPOT}/campagne_pca/data/vocab_categories.csv",
                  dtype={"mot": str}, keep_default_na=False
                  ).set_index("mot")["categorie"]
c = ajouts["mot"].map(cat)
parlant_ajouts = ajouts.loc[c.isin(GARDEES) | c.isna(), "mot"].tolist()
vocab600 = [m for m in open(f"{DEPOT}/campagne_pca/data/pics_unifie/vocab600.txt",
                            encoding="utf-8").read().split("\n") if m]
with open(f"{DOSSIER}/vocab_parlant_etendu.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(vocab600 + parlant_ajouts) + "\n")

tests = ["ukraine", "macron", "covid", "confinement", "poutine", "trump"]
print(f"top-{K} par occurrences 2000-2025 : seuil {int(recent['total'].iloc[-1])} occ. ; "
      f"{len(ajouts)} mots ajoutes au top-10 000 -> {len(etendu)} mots "
      f"(vocab_etendu.csv)", flush=True)
print(f"parlant : {len(vocab600)} (vocab600) + {len(parlant_ajouts)} ajoutes "
      f"-> {len(vocab600) + len(parlant_ajouts)} (vocab_parlant_etendu.txt)", flush=True)
print("controle :", ", ".join(f"{m} {'OUI' if m in set(ajouts['mot']) else 'non'}"
                              for m in tests), flush=True)
