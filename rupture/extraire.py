"""Brique 0 : LE mecanisme d'extraction des series ngram (mot -> date, X_t, N_t).

Mecanisme unique du pipeline : les briques rupture (via serie.charger) et la
route /fiche de l'API s'appuient dessus ; extraire.sh est obsolete. 1 a 3 mots
(uni/bi/trigrammes), graphies avec/sans accents sommees (doublons OCR — taper
la graphie accentuee, l'autre est deduite), zeros reinjectes via total_<table>.
Sur gallica : lecture sqlite directe (NGRAM_DIR surchargeable pour tester sur
une mini-base) ; sur le Mac : la meme requete via ssh (lecture seule).
Cache rupture/cache/<media>_<slug>.csv, a supprimer librement ; cache=False
force la lecture en base (API : bases mises a jour quotidiennement).
"""
import io
import os
import sqlite3
import subprocess
import unicodedata
import pandas as pd

from scripts.tokenisation import tokeniser

DOSSIER = os.environ.get("NGRAM_DIR", "/data/elias/stage-mids/data/corpus")
CACHE = f"{os.path.dirname(os.path.abspath(__file__))}/cache"
MEDIAS = ("lemonde", "lefigaro", "lesechos")
TABLE = {1: "unigram", 2: "bigram", 3: "trigram"}


def slug(mot):
    """Minuscules sans accents, espaces -> _ (nom de fichier, graphie OCR)."""
    mot = " ".join(mot.strip().lower().split())
    return unicodedata.normalize("NFD", mot).encode("ascii", "ignore").decode().replace(" ", "_")


def _sql(db, requete):
    # gallica (ou mini-base NGRAM_DIR) : lecture directe ; Mac : via ssh
    if os.path.exists(db):
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            return pd.read_sql_query(requete, conn)
    sortie = subprocess.run(["ssh", "gallica", f'sqlite3 -csv -header {db} "{requete}"'],
                            capture_output=True, text=True, check=True)
    if not sortie.stdout.strip():                    # aucun resultat : pas meme l'en-tete
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(sortie.stdout))


def _morceau(db, graphie):
    """SELECT (date, n) du gram pour une graphie, ou None si absente de la base."""
    tokens = tokeniser(graphie)
    if not 1 <= len(tokens) <= 3:
        raise ValueError(f"« {graphie} » : 1 a 3 mots attendus")
    ids = []
    for t in tokens:
        df = _sql(db, "SELECT id FROM token WHERE word = '{}'".format(t.replace("'", "''")))
        if not len(df):
            return None, len(tokens)
        ids.append(int(df["id"].iloc[0]))
    conditions = " AND ".join(f"w{i + 1} = {v}" for i, v in enumerate(ids))
    return f"SELECT date, n FROM {TABLE[len(tokens)]} WHERE {conditions}", len(tokens)


def serie(mot, media="lemonde", cache=True):
    """Serie complete du mot dans le media : DataFrame (date, X_t, N_t)."""
    if media not in MEDIAS:
        raise ValueError(f"media inconnu : {media} (choix : {', '.join(MEDIAS)})")
    mot = " ".join(mot.strip().lower().split())
    chemin = f"{CACHE}/{media}_{slug(mot)}.csv"
    if cache and os.path.exists(chemin):
        return pd.read_csv(chemin)

    db = f"{DOSSIER}/{media}_ngram.db"
    sans = unicodedata.normalize("NFD", mot).encode("ascii", "ignore").decode()
    morceaux, n_tokens = [], 1
    for graphie in {mot, sans}:
        m, n_tokens = _morceau(db, graphie)
        if m:
            morceaux.append(m)
    if not morceaux:
        raise ValueError(f"« {mot} » : inconnu de la base {media}")
    d = _sql(db, f"SELECT t.date AS date, COALESCE(u.x, 0) AS X_t, t.total AS N_t "
                 f"FROM total_{TABLE[n_tokens]} t "
                 f"LEFT JOIN (SELECT date, SUM(n) AS x FROM ({' UNION ALL '.join(morceaux)}) "
                 f"GROUP BY date) u ON u.date = t.date ORDER BY t.date")
    if cache:
        os.makedirs(CACHE, exist_ok=True)
        d.to_csv(chemin, index=False)
    return d
