# API ngram : interroge les bases *_ngram.db à la manière de Gallicagram.
# Route /query compatible avec le front React de Benoît (réponse CSV).
# Lancement (serveur) : python -m api.app  puis  http://localhost:8501/query?mot=inflation&corpus=lesechos

import os
import re
import sqlite3
import unicodedata
from flask import Flask, Response, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd

from scripts.tokenisation import tokeniser

# NGRAM_DIR surchargeable pour tester en local sur une mini-base
DOSSIER = os.environ.get("NGRAM_DIR", "/data/elias/stage-mids/data/corpus")
CORPUS = {nom: f"{DOSSIER}/{nom}_ngram.db" for nom in ("lesechos", "lefigaro", "lemonde")}
TABLE = {1: "unigram", 2: "bigram", 3: "trigram"}

app = Flask(__name__)
CORS(app)  # autorise un front hébergé ailleurs (Vercel) à appeler l'API


def borne_date(texte, complement):
    # "2020" -> 2020*10000+complement ; "2020-03" -> AAAAMM+jour ; "2020-03-14" -> 20200314
    chiffres = re.sub(r"\D", "", texte)
    if len(chiffres) == 8:
        return int(chiffres)
    if len(chiffres) == 6:
        return int(chiffres) * 100 + (1 if complement == 101 else 31)
    return int(chiffres) * 10000 + complement


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
    date_min = borne_date(request.args.get("from") or "1900", 101)   # défaut : 1er janvier
    date_max = borne_date(request.args.get("to") or "2100", 1231)    # défaut : 31 décembre
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


@app.route("/top")
def top():
    # les ngrams les plus fréquents d'une période, lus dans <corpus>_top.db
    # (précalculée par scripts/top_ngram.py — trop lourd à calculer à la volée)
    corpus = request.args.get("corpus", "lesechos")
    if corpus not in CORPUS:
        return f"corpus inconnu : {corpus} (choix : {', '.join(CORPUS)})", 400
    chemin = CORPUS[corpus].replace("_ngram.db", "_top.db")
    if not os.path.exists(chemin):
        return f"top pas encore construit pour {corpus} (scripts/top_ngram.py)", 400
    taille = request.args.get("n", "1")
    resolution = request.args.get("resolution", "annee")
    if taille not in ("1", "2", "3") or resolution not in ("annee", "mois", "jour"):
        return "paramètres invalides : n (1 à 3), resolution (annee|mois|jour)", 400
    periode = re.sub(r"\D", "", request.args.get("periode", ""))
    if not periode:
        return "paramètre periode manquant (ex. 2022, 2022-03, 2022-03-14)", 400
    k = min(int(request.args.get("k", 10)), 500)
    filtre = "" if request.args.get("sans_stop", "1") == "0" else "AND stop = 0"

    conn = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    df = pd.read_sql_query(
        f"SELECT gram, n FROM top WHERE ngram_n = ? AND resolution = ? AND periode = ? {filtre} "
        "ORDER BY rang LIMIT ?",
        conn, params=[int(taille), resolution, int(periode), k])
    conn.close()
    return Response(df.to_csv(index=False), mimetype="text/plain")


def bornes_periode(periode, resolution):
    p = int(periode)
    if resolution == "annee":
        return p * 10000 + 101, p * 10000 + 1231
    if resolution == "mois":
        return p * 100 + 1, p * 100 + 31
    return p, p


@app.route("/evolution")
def evolution():
    # ce qui monte / descend entre deux périodes, à partir des tops précalculés
    # (approximation : un ngram hors du top 500 d'une période y compte pour zéro)
    corpus = request.args.get("corpus", "lesechos")
    if corpus not in CORPUS:
        return f"corpus inconnu : {corpus} (choix : {', '.join(CORPUS)})", 400
    chemin = CORPUS[corpus].replace("_ngram.db", "_top.db")
    if not os.path.exists(chemin):
        return f"top pas encore construit pour {corpus} (scripts/top_ngram.py)", 400
    taille = request.args.get("n", "1")
    resolution = request.args.get("resolution", "annee")
    if taille not in ("1", "2", "3") or resolution not in ("annee", "mois", "jour"):
        return "paramètres invalides : n (1 à 3), resolution (annee|mois|jour)", 400
    periodes = [re.sub(r"\D", "", request.args.get(p, "")) for p in ("avant", "apres")]
    if not all(periodes):
        return "paramètres avant et apres requis (ex. avant=2018&apres=2023)", 400
    k = min(int(request.args.get("k", 10)), 100)
    filtre = "" if request.args.get("sans_stop", "1") == "0" else "AND stop = 0"

    conn_top = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
    conn_ng = sqlite3.connect(f"file:{CORPUS[corpus]}?mode=ro", uri=True)
    freqs = [{}, {}]  # gram -> occurrences pour 100 000, pour chaque période
    for i, periode in enumerate(periodes):
        total = conn_ng.execute(
            f"SELECT SUM(total) FROM total_{TABLE[int(taille)]} WHERE date BETWEEN ? AND ?",
            bornes_periode(periode, resolution)).fetchone()[0]
        if not total:
            return f"pas de données pour la période {periode}", 400
        lignes = conn_top.execute(
            f"SELECT gram, n FROM top WHERE ngram_n = ? AND resolution = ? AND periode = ? "
            f"{filtre} ORDER BY rang LIMIT 500",
            [int(taille), resolution, int(periode)])
        freqs[i] = {gram: n / total * 1e5 for gram, n in lignes}
    conn_top.close()
    conn_ng.close()

    lignes = [(gram, freqs[0].get(gram, 0), freqs[1].get(gram, 0)) for gram
              in set(freqs[0]) | set(freqs[1])]
    lignes = [(g, f1, f2, f2 - f1) for g, f1, f2 in lignes]
    hausses = sorted((l for l in lignes if l[3] > 0), key=lambda l: -l[3])[:k]
    baisses = sorted((l for l in lignes if l[3] < 0), key=lambda l: l[3])[:k]
    df = pd.DataFrame([("hausse", *l) for l in hausses] + [("baisse", *l) for l in baisses],
                      columns=["sens", "gram", "avant", "apres", "delta"])
    return Response(df.to_csv(index=False), mimetype="text/plain")


def sans_accents(texte):
    return unicodedata.normalize("NFD", texte).encode("ascii", "ignore").decode()


def serie_sommee(conn, gram, date_min, date_max):
    # somme les graphies avec/sans accents (l'OCR a créé des doublons type "président"/"president")
    morceaux = []
    for forme in {gram, sans_accents(gram)}:
        tokens = tokeniser(forme)
        if 1 <= len(tokens) <= 3:
            df = serie(conn, tokens, date_min, date_max)
            if len(df):
                morceaux.append(df)
    if not morceaux:
        return pd.DataFrame({"date": [], "n": []})
    return pd.concat(morceaux).groupby("date", as_index=False)["n"].sum()


def moments_grille(pmf, k):
    # moyenne, écart-type, Var/Moy, skewness, kurtosis (excès) d'une loi discrète (pmf sur k)
    m = float((k * pmf).sum())
    v = float(((k - m) ** 2 * pmf).sum())
    return [m, v ** 0.5, v / m if m else None,
            float(((k - m) ** 3 * pmf).sum()) / v ** 1.5 if v else None,
            float(((k - m) ** 4 * pmf).sum()) / v ** 2 - 3 if v else None]


@app.route("/fiche")
def fiche():
    # fiche statistique d'un mot : ajustements Poisson(lambda*N_t), NB(mu*N_t, r) et
    # mélange Bernoulli × NB décalée (« bnb »), p-valeurs, pics, moments et densités-mélange.
    # /fiche?mot=guerre&corpus=lemonde&from=2020&to=2024[&seuil=1e-4]
    import numpy as np
    from scipy.stats import poisson, nbinom, skew, kurtosis, chi2 as loi_chi2
    try:
        from statsmodels.discrete.discrete_model import NegativeBinomial
    except ImportError:
        return "statsmodels manquant : pip install statsmodels dans le venv de l'API", 500
    import warnings

    corpus = request.args.get("corpus", "lemonde")
    if corpus not in CORPUS:
        return f"corpus inconnu : {corpus} (choix : {', '.join(CORPUS)})", 400
    gram = request.args.get("mot", "").strip()
    if not gram:
        return "paramètre mot manquant", 400
    if not 1 <= len(tokeniser(gram)) <= 3:
        return f"« {gram} » : 1 à 3 mots attendus", 400
    date_min = borne_date(request.args.get("from") or "2020", 101)
    date_max = borne_date(request.args.get("to") or "2024", 1231)
    seuil = float(request.args.get("seuil", 1e-4))

    conn = sqlite3.connect(f"file:{CORPUS[corpus]}?mode=ro", uri=True)
    n_tokens = len(tokeniser(gram))
    totaux = pd.read_sql_query(
        f"SELECT date, total FROM total_{TABLE[n_tokens]} WHERE date BETWEEN ? AND ?",
        conn, params=[date_min, date_max])
    df = totaux.merge(serie_sommee(conn, gram, date_min, date_max), on="date", how="left")
    conn.close()
    df["n"] = df["n"].fillna(0).astype(int)
    df = df[df["total"] > 0].sort_values("date")  # jours sans publication : hors modèle

    if len(df) < 60:
        return f"période trop courte ({len(df)} jours avec publication) : fit trop fragile", 400
    X = df["n"].to_numpy(float)
    N = df["total"].to_numpy(float)
    if X.sum() == 0:
        return f"« {gram} » : aucune occurrence dans {corpus} sur la période", 404

    lam = X.sum() / N.sum()                          # MLE Poisson (forme fermée)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = NegativeBinomial(X, np.ones((len(X), 1)), exposure=N).fit(disp=0, maxiter=300)
    mu, r = float(np.exp(res.params[0])), float(1.0 / res.params[1])

    # troisième ajustement : mélange Bernoulli × binomiale négative décalée (« bnb »)
    # X = 0 avec proba p0, sinon X = 1 + Z avec Z ~ NB(mu_b*N_t, r_b) (décision Simon, 20/07/2026)
    p0 = float((X == 0).mean())
    actifs = X >= 1                                  # jours à X >= 1 (le NB décalé porte sur ceux-là)
    Ya, Na = X[actifs] - 1, N[actifs]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res_b = NegativeBinomial(Ya, np.ones((len(Ya), 1)), exposure=Na).fit(disp=0, maxiter=300)
    mu_b, r_b = float(np.exp(res_b.params[0])), float(1.0 / res_b.params[1])

    # test d'adéquation du chi² sur les résidus de Pearson : chaque jour est comparé
    # à sa propre loi (N_t varie, impossible de binner un histogramme commun) ;
    # ddl = jours - paramètres estimés (1 pour Poisson : lambda ; 2 pour la NB : mu, r)
    adequation = {}
    for nom, m, v, k_estimes in (("poisson", lam * N, lam * N, 1),
                                 ("nb", mu * N, mu * N + (mu * N) ** 2 / r, 2)):
        stat = float(((X - m) ** 2 / v).sum())
        ddl = len(X) - k_estimes
        adequation[nom] = {"chi2": stat, "ddl": ddl, "p": float(loi_chi2.sf(stat, ddl))}
    # chi² du mélange sur tous les jours (3 paramètres : p0, mu_b, r_b)
    m_b = mu_b * N
    v_nb = m_b + m_b ** 2 / r_b                      # variance du NB décalé jour par jour
    E = (1 - p0) * (1 + m_b)                          # espérance et variance du mélange
    V = (1 - p0) * (v_nb + (1 + m_b) ** 2) - E ** 2
    stat = float(((X - E) ** 2 / V).sum())
    adequation["bnb"] = {"chi2": stat, "ddl": len(X) - 3,
                         "p": float(loi_chi2.sf(stat, len(X) - 3))}

    p = nbinom.sf(X - 1, r, r / (r + mu * N))        # p_t = P(X >= X_t) sous la loi du jour
    pics = df[p < seuil]
    # p-valeur du jour sous le mélange (1.0 les jours à zéro)
    p_bnb = np.where(actifs, (1 - p0) * nbinom.sf(X - 2, r_b, r_b / (r_b + mu_b * N)), 1.0)
    pics_bnb = df[p_bnb < seuil]

    # densités-mélange (moyenne des pmf sur les vrais N_t), par blocs pour borner la mémoire
    k0 = 0 if X.max() < 3000 else max(0, int(X.min() * 0.6))
    k1 = min(int(X.max() * 1.3) + 6, k0 + 30000)
    k = np.arange(k0, k1)
    pois_mix, nb_mix, bnb_mix = np.empty(len(k)), np.empty(len(k)), np.empty(len(k))
    for debut in range(0, len(k), 2000):
        bloc = k[debut:debut + 2000, None]
        pois_mix[debut:debut + 2000] = poisson.pmf(bloc, (lam * N)[None, :]).mean(1)
        nb_mix[debut:debut + 2000] = nbinom.pmf(bloc, r, (r / (r + mu * N))[None, :]).mean(1)
        # k == 0 -> p0 ; k >= 1 -> (1-p0)*NB(k-1) moyennée sur les N_t
        dens = (1 - p0) * nbinom.pmf(bloc - 1, r_b, (r_b / (r_b + mu_b * N))[None, :]).mean(1)
        bnb_mix[debut:debut + 2000] = np.where(k[debut:debut + 2000] == 0, p0, dens)

    pas = max(1, len(k) // 800)                      # ~800 points suffisent pour le tracé
    return jsonify({
        "mot": gram, "corpus": corpus, "de": int(date_min), "a": int(date_max),
        "jours": len(df), "seuil": seuil,
        "params": {"lambda": lam, "mu": mu, "r": r,
                   "p0": p0, "mu_bnb": mu_b, "r_bnb": r_b},
        "adequation": adequation,
        "serie": {"date": df["date"].tolist(), "x": df["n"].tolist(),
                  "total": df["total"].tolist(), "p": np.round(p, 8).tolist(),
                  "p_bnb": np.round(p_bnb, 8).tolist()},
        "pics": [{"date": int(d), "x": int(x), "p": float(pv)}
                 for d, x, pv in zip(pics["date"], pics["n"], p[p < seuil])],
        "pics_bnb": [{"date": int(d), "x": int(x), "p": float(pv)}
                     for d, x, pv in zip(pics_bnb["date"], pics_bnb["n"], p_bnb[p_bnb < seuil])],
        "hist": {"k": k[::pas].tolist(), "poisson": pois_mix[::pas].tolist(),
                 "nb": nb_mix[::pas].tolist(), "bnb": bnb_mix[::pas].tolist()},
        "moments": {
            "observe": [float(X.mean()), float(X.std()), float(X.var() / X.mean()),
                        float(skew(X)), float(kurtosis(X))],
            "poisson": moments_grille(pois_mix, k),
            "nb": moments_grille(nb_mix, k),
            "bnb": moments_grille(bnb_mix, k),
        },
    })


if __name__ == "__main__":
    # 127.0.0.1 : joignable seulement depuis la machine (ou un tunnel ssh), rien d'exposé
    app.run(host="127.0.0.1", port=8501)
