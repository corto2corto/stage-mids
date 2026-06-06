"""Inspection des CSV rapatriés depuis le serveur.

Place les CSV dans data/resultats/ puis lance :
    python -m exploration.inspecter_resultats le_monde
    python -m exploration.inspecter_resultats le_figaro
"""

import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
RESULTATS = RACINE / "data" / "resultats"

EXTRAIT = 40   # nombre de mots à afficher en début et fin d'article


def charger(media):
    chemin = RESULTATS / f"{media}.csv"
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}\nLance d'abord : scp ubuntu@<serveur>:/data/elias/stage-mids/data/{media}.csv {RESULTATS}/")
    return pd.read_csv(chemin)


def afficher_extrait(row, statut):
    texte = str(row.get("contenu", "") or "")
    mots = texte.split()
    debut = " ".join(mots[:EXTRAIT])
    fin = " ".join(mots[-EXTRAIT:]) if len(mots) > EXTRAIT else ""
    print(f"\n[{statut}] id={row.get('id', '?')}  {row.get('url', '')}")
    print(f"  début : {debut}")
    if fin:
        print(f"  fin   : {fin}")
    print(f"  ({len(mots)} mots)")


def inspecter(media, n=5):
    df = charger(media)
    print(f"\n{'='*60}")
    print(f"  {media}  —  {len(df)} articles")
    print(f"{'='*60}")

    ok = df[df["contenu"].notna() & (df["contenu"].str.len() > 200)]
    ko = df[df["contenu"].isna() | (df["contenu"].str.len() <= 200)]

    print(f"\n  OK : {len(ok)} articles  |  KO (vide/bloqué) : {len(ko)} articles")

    print(f"\n--- {n} articles OK ---")
    for _, row in ok.head(n).iterrows():
        afficher_extrait(row, "OK")

    print(f"\n--- {n} articles KO ---")
    for _, row in ko.head(n).iterrows():
        afficher_extrait(row, "KO")


if __name__ == "__main__":
    media = sys.argv[1] if len(sys.argv) > 1 else "le_monde"
    inspecter(media)
