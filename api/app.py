# API ngram : interroge les bases *_ngram.db à la manière de Gallicagram.
# Route /query compatible avec le front React de Benoît (réponse CSV).
# Lancement (serveur) : python -m api.app  puis  http://localhost:8501/query?mot=inflation&corpus=lesechos

import os
import re
import sqlite3
from flask import Flask, Response, request, send_file
from flask_cors import CORS
import pandas as pd

CORPUS = {
    "lesechos": "/data/elias/stage-mids/data/corpus/lesechos_ngram.db",
    "lefigaro": "/data/elias/stage-mids/data/corpus/lefigaro_ngram.db",
    # "lemonde": en reconstruction, à réactiver quand le build est fini
}
TABLE = {1: "unigram", 2: "bigram", 3: "trigram"}

app = Flask(__name__)
CORS(app)  # autorise un front hébergé ailleurs (Vercel) à appeler l'API


def tokeniser(gram):
    # même normalisation qu'à la construction des bases (scripts/ngram_*.py)
    gram = re.sub(r"(?<=[A-Z])\.", "", gram).lower().replace("’", "'")
    return re.findall(r"[a-zà-ÿ0-9']+", gram)


def serie(conn, tokens, date_min, date_max):
    # id des mots d'abord (jamais de jointure sur token : scan complet sinon)
    ids = []
    for t in tokens:
        ligne = conn.execute("SELECT id FROM token WHERE word = ?", (t,)).fetchone()
        if ligne is None:  # mot inconnu de la base -> série à zéro
            return pd.DataFrame({"date": [], "n": []})
        ids.append(ligne[0])
    conditions = " AND ".join(f"w{i} = ?" for i in range(1, len(tokens) + 1))
    return pd.read_sql_query(
        f"SELECT date, n FROM {TABLE[len(tokens)]} WHERE {conditions} AND date BETWEEN ? AND ?",
        conn, params=ids + [date_min, date_max])


@app.route("/")
def accueil():
    return send_file(os.path.join(os.path.dirname(__file__), "index.html"))


@app.route("/query")
def query():
    corpus = request.args.get("corpus", "lesechos")
    if corpus not in CORPUS:
        return f"corpus inconnu : {corpus} (choix : {', '.join(CORPUS)})", 400
    date_min = int(request.args.get("from", 1900)) * 10000 + 101    # 1er janvier
    date_max = int(request.args.get("to", 2100)) * 10000 + 1231     # 31 décembre
    resolution = request.args.get("resolution", "mois")

    conn = sqlite3.connect(f"file:{CORPUS[corpus]}?mode=ro", uri=True)
    series = []
    for gram in request.args.get("mot", "").split(","):
        tokens = tokeniser(gram)
        if not 1 <= len(tokens) <= 3:
            return f"« {gram.strip()} » : 1 à 3 mots attendus", 400
        totaux = pd.read_sql_query(
            f"SELECT date, total FROM total_{TABLE[len(tokens)]} WHERE date BETWEEN ? AND ?",
            conn, params=[date_min, date_max])
        df = totaux.merge(serie(conn, tokens, date_min, date_max), on="date", how="left")
        df["n"] = df["n"].fillna(0).astype(int)
        df["gram"] = gram.strip()
        series.append(df)
    conn.close()
    if not series:
        return "paramètre mot manquant", 400

    df = pd.concat(series)
    df["annee"] = df["date"] // 10000
    df["mois"] = df["date"] // 100 % 100
    df["jour"] = df["date"] % 100
    if resolution == "annee":
        df = df.groupby(["gram", "annee"], as_index=False)[["n", "total"]].sum()
    elif resolution == "mois":
        df = df.groupby(["gram", "annee", "mois"], as_index=False)[["n", "total"]].sum()
    else:  # jour
        df = df.drop(columns="date")
    return Response(df.to_csv(index=False), mimetype="text/plain")


if __name__ == "__main__":
    # 127.0.0.1 : joignable seulement depuis la machine (ou un tunnel ssh), rien d'exposé
    app.run(host="127.0.0.1", port=8501)
