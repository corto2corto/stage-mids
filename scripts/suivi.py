"""
Suivi de l'avancement du scraping.

Ce script NE FAIT QUE LIRE les données produites par le scraping :
- la base sqlite `urls.db`  -> pour savoir où on en est (combien d'URLs traitées) ;
- les CSV de sortie (un par média) -> pour les statistiques de contenu.

Il ne modifie rien et ne touche à aucun module du dossier scraping/.

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
from collections import Counter
from pathlib import Path
from statistics import mean, median

# Source unique de vérité pour l'emplacement des données ; surchargeable en local.
from scraping.stockage import DATA_DIR as _DATA_DIR_DEFAUT

DATA_DIR = Path(os.environ.get("STAGE_DATA_DIR", _DATA_DIR_DEFAUT))
BASE = DATA_DIR / "urls.db"
DOSSIER_CSV = DATA_DIR / "csv"

# Les CSV contiennent des articles entiers : on relève la limite de taille d'un champ.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# --------------------------------------------------------------------------- #
# Helpers : affichage et accès aux données
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
# Indicateurs lus dans la base sqlite
# --------------------------------------------------------------------------- #

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
        ["média", "total", "réussis", "échecs", "restants", "% traité"],
        lignes,
    )
    return par_media


def _ligne_avancement(media, compte):
    total = compte[0] + compte[1] + compte[2]
    traites = compte[1] + compte[2]
    pct = f"{100 * traites / total:.1f}%" if total else "—"
    return [media, total, compte[2], compte[1], compte[0], pct]


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


# --------------------------------------------------------------------------- #
# Indicateurs lus dans les CSV de sortie
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
# Ligne de commande
# --------------------------------------------------------------------------- #

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
}
SANS_MEDIA = {"resume", "avancement", "echecs"}


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
