"""
Suivi de l'avancement du scraping.

Ce script lit les données produites par le scraping :
- la base sqlite `urls.db`  -> pour savoir où on en est (combien d'URLs traitées) ;
- les CSV de sortie (un par média) -> pour les statistiques de contenu.

Il ne touche à aucun module du dossier scraping/. Seule exception à la lecture
seule : `snapshot` tient un journal de bord (`suivi_journal.csv`) — ses propres
données, pas celles du scraping — pour suivre le taux de réussite dans le temps.

Chaque indicateur est une fonction indépendante, appelable de deux façons :
- en ligne de commande :  python -m scripts.suivi <indicateur> [média]
- par import           :  from scripts.suivi import avancement; avancement()

À lancer depuis la racine du dépôt (forme `-m`, pour que le package scraping
soit importable).

Indicateurs disponibles :
  resume      vue d'ensemble (avancement + longueur des articles)   [défaut]
  avancement  où en est le scraping, par média            (source : urls.db)
  echecs      taux d'échec par média                       (source : urls.db)
  contenu     longueur des articles, en mots               (source : CSV)
  dates       répartition des articles par année           (source : CSV)
  sections    rubriques les plus fréquentes                (source : CSV)
  auteurs     signatures les plus fréquentes               (source : CSV)
  acces       part d'articles en accès libre / payant       (source : CSV)
  tendance    page HTML du taux de réussite, batch par batch (source : journal)
  snapshot    enregistre un instantané des compteurs        (écrit : journal)

Les indicateurs lus dans les CSV acceptent un nom de média en argument pour
se limiter à ce média (sinon : tous les médias confondus).

Exemples :
  python -m scripts.suivi
  python -m scripts.suivi avancement
  python -m scripts.suivi contenu le_monde

Les données vivent sur le serveur (DATA_DIR dans scraping/stockage.py). Pour
tester ce script sur une copie locale, pointer ailleurs avec la variable
d'environnement STAGE_DATA_DIR (ex : STAGE_DATA_DIR=./data python -m scripts.suivi).
"""

import csv
import os
import sqlite3
import sys
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev

# Source unique de vérité pour l'emplacement des données ; surchargeable en local.
from scraping.stockage import DATA_DIR as _DATA_DIR_DEFAUT

DATA_DIR = Path(os.environ.get("STAGE_DATA_DIR", _DATA_DIR_DEFAUT))
BASE = DATA_DIR / "urls.db"
DOSSIER_CSV = DATA_DIR / "csv"
JOURNAL = DATA_DIR / "suivi_journal.csv"

# Carte de contrôle : on signale un décrochage quand le taux d'un intervalle
# passe sous (moyenne − 3σ) de l'historique du média. MIN_BASELINE = nombre
# d'intervalles de référence requis avant de juger (sinon la moyenne ne veut rien
# dire et on alerterait pour du bruit).
SEUIL_SIGMA = 3
MIN_BASELINE = 5

# Les CSV contiennent des articles entiers : on relève la limite de taille d'un champ.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# Helpers : affichage et accès aux données

def _afficher(titre, entetes, lignes):
    """Affiche un tableau aligné. 1re colonne à gauche, le reste à droite."""
    print(f"\n{titre}")
    if not lignes:
        print("  (aucune donnée)")
        return
    lignes = [[str(c) for c in ligne] for ligne in lignes]
    largeurs = [max(len(e), *(len(l[i]) for l in lignes)) for i, e in enumerate(entetes)]

    def fmt(ligne):
        cells = [v.ljust(largeurs[i]) if i == 0 else v.rjust(largeurs[i])
                 for i, v in enumerate(ligne)]
        return "  " + "  ".join(cells)

    print(fmt(entetes))
    print("  " + "  ".join("-" * l for l in largeurs))
    for ligne in lignes:
        print(fmt(ligne))


def _connexion():
    """Ouvre la base, ou explique gentiment qu'elle est introuvable."""
    if not BASE.exists():
        sys.exit(f"Base introuvable : {BASE}\n"
                 f"Les données vivent sur le serveur, sous {DATA_DIR}.\n"
                 f"En local, pointer ailleurs avec STAGE_DATA_DIR=...")
    return sqlite3.connect(BASE)


def _medias_csv():
    """Liste des médias ayant un CSV de sortie (déduit des fichiers présents)."""
    if not DOSSIER_CSV.exists():
        return []
    return sorted(p.stem for p in DOSSIER_CSV.glob("*.csv"))


def _lire_csv(media):
    """Génère les lignes (dict) du CSV d'un média ; rien si le fichier n'existe pas."""
    chemin = DOSSIER_CSV / f"{media}.csv"
    if not chemin.exists():
        return
    with open(chemin, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


# Indicateurs lus dans la base sqlite

def avancement():
    """Où en est le scraping : URLs traitées par média (source : urls.db)."""
    with _connexion() as conn:
        rows = conn.execute(
            "SELECT media, etat, COUNT(*) FROM urls GROUP BY media, etat"
        ).fetchall()

    par_media = {}                       # media -> {0: restants, 1: échecs, 2: réussis}
    for media, etat, n in rows:
        par_media.setdefault(media, {0: 0, 1: 0, 2: 0})[etat] = n

    total = {0: 0, 1: 0, 2: 0}
    lignes = []
    for media in sorted(par_media):
        compte = par_media[media]
        for etat in total:
            total[etat] += compte[etat]
        lignes.append(_ligne_avancement(media, compte))
    if len(lignes) > 1:
        lignes.append(_ligne_avancement("TOTAL", total))

    _afficher(
        "Avancement du scraping (source : urls.db)",
        ["média", "total", "réussis", "échecs", "restants", "% traité", "% succès"],
        lignes,
    )
    return par_media


def _ligne_avancement(media, compte):
    total = compte[0] + compte[1] + compte[2]
    traites = compte[1] + compte[2]
    pct_traite = f"{100 * traites / total:.1f}%" if total else "—"
    pct_succes = f"{100 * compte[2] / traites:.1f}%" if traites else "—"
    return [media, total, compte[2], compte[1], compte[0], pct_traite, pct_succes]


def echecs():
    """Taux d'échec par média parmi les URLs déjà traitées (source : urls.db).

    Un échec = page non récupérée, vide, ou restée derrière le paywall.

    Lecture : un média qui ressort avec beaucoup d'échecs signale un problème à
    creuser (bypass qui échoue, sélecteur de corps inadapté, paywall sélectif…).
    Utile pour juger un run de test.
    """
    with _connexion() as conn:
        rows = conn.execute(
            "SELECT media, etat, COUNT(*) FROM urls WHERE etat IN (1, 2) "
            "GROUP BY media, etat"
        ).fetchall()

    par_media = {}                       # media -> {1: échecs, 2: réussis}
    for media, etat, n in rows:
        par_media.setdefault(media, {1: 0, 2: 0})[etat] = n

    lignes = []
    for media in sorted(par_media):
        compte = par_media[media]
        traites = compte[1] + compte[2]
        taux = f"{100 * compte[1] / traites:.1f}%" if traites else "—"
        lignes.append([media, traites, compte[1], taux])

    _afficher(
        "Taux d'échec (échec = paywall ou page vide, source : urls.db)",
        ["média", "traités", "échecs", "taux d'échec"],
        lignes,
    )
    return par_media


# Indicateurs lus dans les CSV de sortie

def contenu(media=None):
    """Longueur des articles écrits dans les CSV, en mots (source : CSV)."""
    medias = [media] if media else _medias_csv()
    lignes = []
    global_mots = []
    for m in medias:
        mots = [len(row["contenu"].split()) for row in _lire_csv(m)]
        if not mots:
            continue
        global_mots.extend(mots)
        lignes.append(_ligne_contenu(m, mots))
    if not media and len(lignes) > 1:
        lignes.append(_ligne_contenu("TOTAL", global_mots))

    _afficher(
        "Longueur des articles (source : CSV)",
        ["média", "articles", "moy. mots", "médiane", "min", "max"],
        lignes,
    )
    return lignes


def _ligne_contenu(media, mots):
    return [media, len(mots), round(mean(mots)), round(median(mots)), min(mots), max(mots)]


def dates(media=None):
    """Répartition des articles par année de publication (source : CSV)."""
    medias = [media] if media else _medias_csv()
    annees = Counter()
    sans_date = 0
    for m in medias:
        for row in _lire_csv(m):
            an = (row.get("date") or "")[:4]
            if an.isdigit():
                annees[an] += 1
            else:
                sans_date += 1

    lignes = [[an, annees[an]] for an in sorted(annees)]
    if sans_date:
        lignes.append(["(date absente)", sans_date])

    titre = "Articles par année" + (f" — {media}" if media else "") + " (source : CSV)"
    _afficher(titre, ["année", "articles"], lignes)
    return annees


def sections(media=None, n=15):
    """Rubriques (articleSection) les plus fréquentes (source : CSV)."""
    compte = _compter_champ(media, "section")
    lignes = [[sec, nb] for sec, nb in compte.most_common(n)]
    titre = f"Top {n} rubriques" + (f" — {media}" if media else "") + " (source : CSV)"
    _afficher(titre, ["rubrique", "articles"], lignes)
    return compte


def auteurs(media=None, n=15):
    """Signatures les plus fréquentes (source : CSV)."""
    compte = _compter_champ(media, "auteur")
    lignes = [[aut, nb] for aut, nb in compte.most_common(n)]
    titre = f"Top {n} signatures" + (f" — {media}" if media else "") + " (source : CSV)"
    _afficher(titre, ["auteur", "articles"], lignes)
    return compte


def _compter_champ(media, champ):
    """Compte les valeurs d'un champ multi-valué (séparées par ', ' à l'écriture)."""
    medias = [media] if media else _medias_csv()
    compte = Counter()
    for m in medias:
        for row in _lire_csv(m):
            for valeur in (row.get(champ) or "").split(", "):
                valeur = valeur.strip()
                if valeur:
                    compte[valeur] += 1
    return compte


def acces(media=None):
    """Part d'articles en accès libre vs payant (champ 'free', source : CSV)."""
    medias = [media] if media else _medias_csv()
    compte = Counter()
    for m in medias:
        for row in _lire_csv(m):
            compte[(row.get("free") or "").strip() or "(non précisé)"] += 1

    total = sum(compte.values())
    lignes = []
    for libelle, cle in [("libre", "oui"), ("payant", "non"), ("non précisé", "(non précisé)")]:
        nb = compte.get(cle, 0)
        if nb:
            lignes.append([libelle, nb, f"{100 * nb / total:.1f}%"])

    titre = "Accès aux articles" + (f" — {media}" if media else "") + " (source : CSV)"
    _afficher(titre, ["accès", "articles", "part"], lignes)
    return compte


def resume():
    """Vue d'ensemble : avancement global + longueur moyenne des articles."""
    avancement()
    contenu()


# Surveillance dans le temps (journal d'instantanés + carte de contrôle)
#
# Le scraping tourne en continu, des jours durant. On veut repérer le moment où
# le taux de réussite d'un média s'effondre (ex. son HTML change, le bypass
# casse). `snapshot` note régulièrement les compteurs cumulés (réussis/échecs par
# média) dans un journal ; le taux « entre deux instantanés » se déduit par
# différence. `tendance` affiche cette série ; un décrochage sous la carte de
# contrôle (moyenne − 3σ de l'historique du média) déclenche une notif ntfy.


def _compteurs_db():
    """Compteurs cumulés (réussis, échecs) par média, lus dans urls.db."""
    with _connexion() as conn:
        rows = conn.execute(
            "SELECT media, etat, COUNT(*) FROM urls WHERE etat IN (1, 2) "
            "GROUP BY media, etat"
        ).fetchall()
    par_media = {}
    for media, etat, n in rows:
        par_media.setdefault(media, {1: 0, 2: 0})[etat] = n
    return {m: (c[2], c[1]) for m, c in par_media.items()}   # (réussis, échecs)


def _lire_journal():
    """Lignes du journal (ordre chronologique d'écriture) ; [] s'il n'existe pas."""
    if not JOURNAL.exists():
        return []
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _series_par_media(journal):
    """journal -> {media: [(réussis, échecs), ...]} en ordre chronologique."""
    series = {}
    for ligne in journal:
        series.setdefault(ligne["media"], []).append(
            (int(ligne["reussis"]), int(ligne["echecs"]))
        )
    return series


def _intervalles(points):
    """Compteurs cumulés -> taux par intervalle : [(n_articles, taux), ...].

    Réussis et échecs sont cumulés depuis la base. Mais un échec peut redevenir
    une réussite quand une URL est rejouée avec succès : le compteur d'échecs
    baisse alors d'un instantané à l'autre. Sans précaution, l'écart négatif fait
    grimper le taux au-dessus de 100 %. On borne chaque écart à 0 : un intervalle
    où les échecs n'augmentent pas compte simplement comme 100 % de réussite, et
    le taux reste toujours dans [0, 1].
    """
    intervalles = []
    for (r0, e0), (r1, e1) in zip(points, points[1:]):
        reussis = max(0, r1 - r0)
        echecs = max(0, e1 - e0)
        n = reussis + echecs
        if n > 0:
            intervalles.append((n, reussis / n))
    return intervalles


def _carte_controle(intervalles):
    """Bornes (moyenne, sigma, borne_basse) calculées sur l'historique.

    L'historique = tous les intervalles sauf le dernier (celui qu'on teste).
    Renvoie None s'il n'y a pas assez de recul, ou si l'historique est plat.
    """
    if len(intervalles) < MIN_BASELINE + 1:
        return None
    taux = [t for _, t in intervalles[:-1]]
    moyenne = mean(taux)
    sigma = stdev(taux)
    if sigma == 0:
        return None
    return moyenne, sigma, moyenne - SEUIL_SIGMA * sigma


def snapshot(min_nouveaux=0):
    """Enregistre un instantané des compteurs dans le journal de suivi.

    Écrit une ligne par média (réussis/échecs cumulés), horodatée. Si
    `min_nouveaux` > 0, n'enregistre que si au moins ce nombre d'articles ont été
    traités depuis le dernier instantané : c'est le déclencheur « tous les N »
    utilisé par le pipeline (insensible aux relances, car les compteurs vivent en
    base). Sur un nouvel instantané, vérifie chaque média et notifie (ntfy) en
    cas de décrochage. Renvoie True si un instantané a été écrit.
    """
    compteurs = _compteurs_db()
    if not compteurs:
        print("Aucun article traité pour l'instant — rien à enregistrer.")
        return False

    journal = _lire_journal()
    total = sum(r + e for r, e in compteurs.values())
    if journal:
        dernier = journal[-1]["horodatage"]
        total_precedent = sum(int(l["reussis"]) + int(l["echecs"])
                              for l in journal if l["horodatage"] == dernier)
    else:
        total_precedent = 0

    if min_nouveaux and total - total_precedent < min_nouveaux:
        return False   # pas assez de nouveaux articles : on n'enregistre rien

    horodatage = datetime.now().isoformat(timespec="seconds")
    nouveau_fichier = not JOURNAL.exists()
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nouveau_fichier:
            w.writerow(["horodatage", "media", "reussis", "echecs"])
        for media in sorted(compteurs):
            reussis, echecs = compteurs[media]
            w.writerow([horodatage, media, reussis, echecs])

    print(f"Instantané enregistré : {total} articles traités au total "
          f"({len(compteurs)} médias).")
    _verifier_decrochages()
    return True


def _verifier_decrochages():
    """Pour chaque média, teste le dernier intervalle et notifie un décrochage."""
    for media, points in _series_par_media(_lire_journal()).items():
        intervalles = _intervalles(points)
        bornes = _carte_controle(intervalles)
        if not bornes:
            continue
        moyenne, _sigma, borne = bornes
        n, taux = intervalles[-1]
        if taux < borne:
            titre = f"Chute du taux de reussite : {media}"
            corps = (f"{media} : {taux:.0%} sur les {n} derniers articles "
                     f"(habituel {moyenne:.0%}, seuil {borne:.0%}). "
                     f"Le bypass décroche.")
            print(f"  ⚠ {corps}")
            _notifier(titre, corps)


def _notifier(titre, corps):
    """Notification ntfy si STAGE_NTFY_TOPIC est défini (sinon ne fait rien).

    Topic et serveur viennent de l'environnement (rien en dur). Toute erreur
    réseau est avalée : une notification ratée ne doit jamais casser le run.
    """
    topic = os.environ.get("STAGE_NTFY_TOPIC")
    if not topic:
        return
    base = os.environ.get("STAGE_NTFY_URL", "https://ntfy.sh").rstrip("/")
    requete = urllib.request.Request(
        f"{base}/{topic}",
        data=corps.encode("utf-8"),
        headers={"Title": titre, "Priority": "high", "Tags": "warning"},
        method="POST",
    )
    try:
        urllib.request.urlopen(requete, timeout=10)
    except Exception as e:
        print(f"  (notification ntfy échouée : {type(e).__name__})")


PAGE_TENDANCE = DATA_DIR / "tendance.html"


def _seuil_carte(taux):
    """Borne basse de la carte de contrôle (moyenne − 3σ), ou None.

    Même logique que les alertes : None s'il n'y a pas assez de recul ou si
    l'historique est plat (σ nul). En pointillés sur le graphe.
    """
    if len(taux) < 2:
        return None
    sigma = stdev(taux)
    return mean(taux) - SEUIL_SIGMA * sigma if sigma else None


def tendance(media=None):
    """Écrit une page HTML interactive du taux de réussite, batch par batch.

    Une courbe par média : en abscisse le numéro de batch (un intervalle entre
    deux instantanés du journal), en ordonnée le taux de réussite. Cliquer un
    média dans la légende masque/affiche sa courbe ; la borne basse de la carte
    de contrôle apparaît en pointillés. Page autonome : Plotly est chargé depuis
    un CDN à l'ouverture, rien à installer côté Python. `media` limite la page à
    un seul média. Source : suivi_journal.csv.
    """
    journal = _lire_journal()
    if not journal:
        print("\nJournal de suivi vide. Prends un premier instantané :\n"
              "  python -m scripts.suivi snapshot")
        return

    series = _series_par_media(journal)
    courbes = {}                         # media -> {batches, taux, n, seuil}
    for m in ((media,) if media else sorted(series)):
        intervalles = _intervalles(series.get(m, []))
        if intervalles:
            taux = [100 * t for _, t in intervalles]
            courbes[m] = {
                "batches": list(range(1, len(taux) + 1)),
                "taux": taux,
                "n": [n for n, _ in intervalles],
                "seuil": _seuil_carte(taux),
            }

    if not courbes:
        print("Pas encore assez d'instantanés pour tracer une courbe "
              "(il en faut au moins deux). Relance après quelques snapshots.")
        return

    PAGE_TENDANCE.write_text(_html_tendance(courbes), encoding="utf-8")
    print(f"Page écrite : {PAGE_TENDANCE}\n"
          f"Ouvre-la dans un navigateur (sur le serveur : récupère le fichier, "
          f"ou `python -m http.server` dans {DATA_DIR}).")


# Palette qualitative (Plotly D3) : une couleur stable par média, en boucle.
COULEURS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


def _html_tendance(courbes):
    """Construit la page HTML autonome (Plotly via CDN) à partir des courbes.

    Au départ aucune courbe n'est tracée (trop de médias se chevauchent) : la
    légende sert de cases à cocher, on clique les médias qu'on veut voir. Chaque
    clic affiche/masque la courbe et son seuil ensemble (mêmes legendgroup). Une
    couleur stable par média. La page remplit la hauteur de la fenêtre.
    """
    import json

    noms = sorted(courbes)
    traces = []
    for i, m in enumerate(noms):
        c = courbes[m]
        couleur = COULEURS[i % len(COULEURS)]
        traces.append({
            "x": c["batches"], "y": c["taux"], "name": m,
            "customdata": c["n"],
            "type": "scatter", "mode": "lines",
            "line": {"color": couleur}, "legendgroup": m,
            "visible": "legendonly",     # masqué au départ : on coche dans la légende
            "hovertemplate": f"{m}<br>batch %{{x}} — %{{y:.1f}} %"
                             "<br>%{customdata} articles<extra></extra>",
        })
        # Borne basse de la carte de contrôle : pointillés, seulement si elle est
        # exploitable (None = pas assez de recul, <= 0 = seuil sans signification).
        # Même legendgroup que la courbe : la case de la légende les (dé)coche ensemble.
        if c["seuil"] is not None and c["seuil"] > 0:
            traces.append({
                "x": [c["batches"][0], c["batches"][-1]],
                "y": [c["seuil"], c["seuil"]],
                "name": f"seuil {m}", "type": "scatter", "mode": "lines",
                "line": {"dash": "dash", "color": couleur, "width": 1},
                "legendgroup": m, "showlegend": False, "hoverinfo": "skip",
                "visible": "legendonly",
            })

    # Une graduation tous les `pas` batchs : au plus ~15 étiquettes sur l'axe X,
    # sinon elles se chevauchent (il peut y avoir des centaines de batchs).
    n_max = max((len(c["batches"]) for c in courbes.values()), default=1)
    pas = max(1, -(-n_max // 15))        # division entière arrondie au plafond

    layout = {
        "title": "Taux de réussite par média",
        "yaxis": {"title": "taux de réussite (%)", "range": [0, 102]},
        "xaxis": {"title": "batch (intervalle entre deux instantanés)",
                  "tick0": 1, "dtick": pas},
        "template": "plotly_white",
        "hovermode": "closest",
        "legend": {"title": {"text": "médias (cliquer pour afficher)"}},
        "margin": {"t": 60},
    }

    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<title>Tendance du scraping</title>"
        "<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>"
        "<style>html,body{height:100%;margin:0}"
        "#g{width:100%;height:100vh}</style>"
        "</head><body>"
        "<div id='g'></div><script>"
        f"Plotly.newPlot('g', {json.dumps(traces)}, {json.dumps(layout)}, "
        "{responsive:true});"
        "</script></body></html>"
    )


# Ligne de commande

# Indicateurs prenant un nom de média facultatif (ceux lus dans les CSV).
INDICATEURS = {
    "resume": resume,
    "avancement": avancement,
    "echecs": echecs,
    "contenu": contenu,
    "dates": dates,
    "sections": sections,
    "auteurs": auteurs,
    "acces": acces,
    "tendance": tendance,
    "snapshot": snapshot,
}
SANS_MEDIA = {"resume", "avancement", "echecs", "snapshot"}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    nom = argv[0] if argv else "resume"
    if nom in ("-h", "--help", "help"):
        print(__doc__)
        return

    fonction = INDICATEURS.get(nom)
    if fonction is None:
        sys.exit(f"Indicateur inconnu : {nom}\n"
                 f"Disponibles : {', '.join(INDICATEURS)}")

    media = argv[1] if len(argv) > 1 else None
    if nom in SANS_MEDIA:
        fonction()
    else:
        fonction(media)


if __name__ == "__main__":
    main()
