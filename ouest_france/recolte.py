"""Récolte les articles du groupe Ouest-France depuis leur API Algolia, au
format CSV du pipeline (scraping/stockage.COLONNES).

L'API sert le texte intégral — y compris pour les articles payants — donc pas
de scraping ni de bypass. Deux points à respecter, détaillés dans
ouest_france/algolia.md :
- le champ `texte` n'existe que sur l'index `articles_bydate_desc`, jamais sur
  `articles` ;
- une requête ne rend jamais plus de 1000 résultats. On découpe donc le temps
  en tranches et, si une tranche dépasse 1000, on la coupe en deux jusqu'à
  passer sous le plafond (pas de perte silencieuse).

Un CSV par titre du groupe, comme les autres médias du pipeline. Attention :
Ouest-France sort dans `ouest_france2.csv` et NON `ouest_france.csv` — ce
dernier appartient à l'autre chaîne de scraping et ne doit pas être touché.

La colonne `auteur` reste vide : l'index n'a pas d'auteur (cf. la tâche
auteur-ouest-france dans .claude/taches.md).

Les clés ne valent que ~24 h. Le script en récupère une au démarrage si
OF_ALGOLIA_KEY n'est pas posée, et la renouvelle tout seul quand elle expire,
via ouest_france/recuperer_cle.py (Firefox headless) — une récolte de plusieurs
jours tourne donc sans intervention.

    python -m ouest_france.recolte 1990 2026              # tout le groupe
    python -m ouest_france.recolte 1990 2026 --titre of   # un seul titre
    python -m ouest_france.recolte 2026-03-10 2026-03-11  # une période précise
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scraping.stockage import COLONNES, DATA_DIR

APP_ID = "C8KP7JV01T"
INDEX = "articles_bydate_desc"          # le seul qui renvoie le champ `texte`
PLAFOND = 1000                          # maximum de résultats atteignables par requête
PARIS = ZoneInfo("Europe/Paris")
ATTENTE = 1.5                           # secondes entre deux appels
ESSAIS = 5                              # reprises sur erreur réseau
QUOTA_ESSAIS = 8                        # reprises sur quota (429), plus patientes

# Les 8 titres du groupe (champ `source`) et le nom de leur CSV.
# « ouest_france2 » et pas « ouest_france » : ce dernier est le CSV de l'autre
# chaîne de scraping, à ne surtout pas écraser.
TITRES = {
    "of": "ouest_france2",
    "co": "le_courrier_de_l_ouest",
    "po": "presse_ocean",
    "ml": "le_maine_libre",
    "im": "le_marin",
    "api": "agence_api",
    "vv": "voiles_et_voiliers",
    "fl": "ouest_france_fil",          # desk faits divers / insolite, 2026 seulement
}

RECUPERER_CLE = Path(__file__).resolve().parent/"recuperer_cle.py"
_cle = os.environ.get("OF_ALGOLIA_KEY", "")


def renouveler():
    """Va chercher une clé fraîche avec ouest_france/recuperer_cle.py (Firefox).
    Les clés ne valent que ~24 h : une récolte longue en consomme plusieurs."""
    global _cle
    print("    clé expirée — récupération d'une nouvelle clé…")
    resultat = subprocess.run([sys.executable, str(RECUPERER_CLE), "--export"],
                              capture_output=True, text=True, timeout=300)
    for ligne in resultat.stdout.splitlines():
        if ligne.startswith('export OF_ALGOLIA_KEY="'):
            _cle = ligne.split('="', 1)[1].rstrip('"')
            print("    nouvelle clé obtenue")
            return True
    print(f"    échec de la récupération : {resultat.stderr.strip()[:200]}")
    return False


def interroger(corps):
    """Une requête Algolia, avec reprise sur erreur réseau, quota ou clé expirée.

    Le quota (429) a son propre budget d'essais, bien plus large que celui des
    erreurs réseau : mesuré le 13/08, il se déclenche après quelques milliers de
    requêtes avec la même clé, et une clé fraîche le lève aussitôt. On attend
    donc *et* on renouvelle la clé, au lieu d'abandonner la journée."""
    essai = quota = 0
    while True:
        requete = urllib.request.Request(
            f"https://{APP_ID}-dsn.algolia.net/1/indexes/{INDEX}/query",
            data=json.dumps(corps).encode(),
            headers={
                "X-Algolia-Application-Id": APP_ID,
                "X-Algolia-API-Key": _cle,
                "Referer": "https://www.ouest-france.fr/",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                return json.loads(reponse.read())
        except urllib.error.HTTPError as erreur:
            if erreur.code in (401, 403) and renouveler():
                continue
            if erreur.code == 429:
                quota += 1
                if quota > QUOTA_ESSAIS:
                    raise
                entete = erreur.headers.get("Retry-After") or ""
                pause = int(entete) if entete.isdigit() else min(15 * 2 ** (quota - 1), 300)
                print(f"    ! quota Algolia atteint — pause de {pause} s "
                      f"et clé renouvelée ({quota}/{QUOTA_ESSAIS})")
                time.sleep(pause)
                renouveler()
                continue
            essai += 1
            if essai >= ESSAIS:
                raise
            time.sleep(2 ** essai)
        except Exception as erreur:
            essai += 1
            if essai >= ESSAIS:
                raise
            pause = 2 ** essai
            print(f"    ! {erreur} — nouvel essai {essai}/{ESSAIS} dans {pause} s")
            time.sleep(pause)


def filtres(debut, fin, source):
    """Tranche temporelle [debut, fin) + articles web uniquement (print=0)."""
    corps = {"numericFilters": [f"datePublication>={debut}",
                               f"datePublication<{fin}", "print=0"]}
    if source:
        corps["filters"] = f"source:{source}"
    return corps


def ligne_csv(article):
    """Un hit Algolia → une ligne au format du pipeline."""
    url = article.get("url") or ""
    if url.startswith("/"):
        url = "https://www.ouest-france.fr" + url

    # section = premier segment du chemin, la rubrique telle que le site l'emploie
    chemin = url.split("//", 1)[-1].split("/")[1:]
    section = chemin[0] if chemin else ""

    horodatage = article.get("datePublication")
    date = (datetime.fromtimestamp(horodatage, PARIS).isoformat()
            if horodatage else "")

    return {
        "id": article.get("objectID", ""),
        "url": url,
        "titre": article.get("titre", ""),
        "auteur": "",                       # absent de l'index, voir taches.md
        "date": date,
        "section": section,
        "free": "non" if article.get("payant") else "oui",
        "contenu": article.get("texte") or "",
    }


def recolter(debut, fin, source, ecrire):
    """Récolte la tranche [debut, fin). Se coupe en deux si elle est pleine.

    On ne se fie PAS à `nbHits` pour décider de couper : Algolia l'approxime
    dès que le volume est gros, et une sous-estimation ferait perdre des
    articles en silence. Le seul signal sûr est le nombre de résultats rendus :
    s'il atteint le plafond, il y en a peut-être d'autres derrière."""
    corps = {"query": "", "hitsPerPage": PLAFOND, "attributesToHighlight": [],
             **filtres(debut, fin, source)}
    hits = interroger(corps)["hits"]
    time.sleep(ATTENTE)

    if len(hits) >= PLAFOND and fin - debut > 1:
        milieu = debut + (fin - debut) // 2
        return (recolter(debut, milieu, source, ecrire)
                + recolter(milieu, fin, source, ecrire))
    if len(hits) >= PLAFOND:
        print(f"    ! tranche pleine sur une seule seconde ({debut}) : "
              f"des articles peuvent manquer")

    for article in hits:
        ecrire(ligne_csv(article))
    return len(hits)


def annee_vide(annee, source):
    """Vrai si ce titre n'a rien publié cette année-là — inutile de parcourir
    ses 365 jours (les petits titres n'existent que sur quelques années)."""
    debut = int(datetime(annee, 1, 1, tzinfo=PARIS).timestamp())
    fin = int(datetime(annee + 1, 1, 1, tzinfo=PARIS).timestamp())
    corps = {"query": "", "hitsPerPage": 1, "attributesToRetrieve": [],
             "attributesToHighlight": [], **filtres(debut, fin, source)}
    vide = not interroger(corps)["hits"]
    time.sleep(ATTENTE)
    return vide


def borne(valeur, fin):
    """« 2024 » (année entière) ou « 2024-03-10 » (jour précis)."""
    if len(valeur) == 4:
        return datetime(int(valeur), 12, 31, tzinfo=PARIS) if fin \
            else datetime(int(valeur), 1, 1, tzinfo=PARIS)
    return datetime.strptime(valeur, "%Y-%m-%d").replace(tzinfo=PARIS)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("debut", help="année (2024) ou date (2024-03-10)")
parser.add_argument("fin", help="année (2026) ou date (2026-03-11)")
parser.add_argument("--titre", choices=sorted(TITRES),
                    help="un seul titre du groupe (défaut : tous)")
parser.add_argument("--dossier", type=Path, default=DATA_DIR/"csv",
                    help="où écrire les CSV")
args = parser.parse_args()

if not _cle and not renouveler():
    sys.exit("aucune clé disponible (poser OF_ALGOLIA_KEY ou vérifier recuperer_cle.py)")

titres = [args.titre] if args.titre else list(TITRES)
args.dossier.mkdir(parents=True, exist_ok=True)
debut, dernier = borne(args.debut, fin=False), borne(args.fin, fin=True)

# Journal d'avancement : le dernier jour terminé pour chaque titre. Permet de
# reprendre une récolte de plusieurs jours sans relire des CSV de plusieurs Go.
suivi = args.dossier/"recolte_avancement.json"
avancement = json.loads(suivi.read_text()) if suivi.exists() else {}

for titre in titres:
    sortie = args.dossier/f"{TITRES[titre]}.csv"
    jour = debut
    if titre in avancement:
        # Le jour noté est terminé : on repart du suivant. Si la récolte s'est
        # interrompue en plein jour, ce jour-là n'a pas été noté et sera refait
        # en entier — quelques doublons possibles, à dédoublonner sur `id`.
        reprise = datetime.fromisoformat(avancement[titre]).replace(tzinfo=PARIS)
        jour = max(jour, reprise + timedelta(days=1))

    if jour > dernier:
        print(f"\n=== {titre} : déjà récolté jusqu'au {avancement[titre]}, rien à faire ===")
        continue

    print(f"\n=== {titre} → {sortie}"
          + (f" (reprise au {jour:%Y-%m-%d})" if titre in avancement else "") + " ===")
    total = 0
    annees_sautees = []
    # Les jours en échec sont rejoués en fin de titre : sans ça le curseur
    # avancerait par-dessus et la journée serait perdue sans que ça se voie.
    echecs = [datetime.fromisoformat(j).replace(tzinfo=PARIS)
              for j in avancement.get(f"{titre}_echecs", [])]

    nouveau_fichier = not sortie.exists() or sortie.stat().st_size == 0
    with open(sortie, "a", newline="", encoding="utf-8") as f:
        redacteur = csv.DictWriter(f, fieldnames=COLONNES)
        if nouveau_fichier:
            redacteur.writeheader()

        def ecrire(ligne):
            redacteur.writerow(ligne)

        def faire_le_jour(jour):
            """Récolte une journée. Rend False si elle a échoué."""
            global total
            suivant = jour + timedelta(days=1)
            try:
                nouveaux = recolter(int(jour.timestamp()), int(suivant.timestamp()),
                                    titre, ecrire)
            except Exception as erreur:
                print(f"[{jour:%Y-%m-%d}] échec : {erreur}")
                return False
            total += nouveaux
            if nouveaux:
                print(f"[{jour:%Y-%m-%d}] +{nouveaux}  (total {total})")
            f.flush()
            return True

        while jour <= dernier:
            # Les petits titres n'existent que sur quelques années : sauter
            # d'un bloc évite des centaines de requêtes pour rien.
            if jour.month == 1 and jour.day == 1 and annee_vide(jour.year, titre):
                annees_sautees.append(jour.year)
                jour = datetime(jour.year + 1, 1, 1, tzinfo=PARIS)
                continue

            if not faire_le_jour(jour):
                echecs.append(jour)
            avancement[titre] = f"{jour:%Y-%m-%d}"
            avancement[f"{titre}_echecs"] = [f"{j:%Y-%m-%d}" for j in echecs]
            suivi.write_text(json.dumps(avancement, indent=2))
            jour += timedelta(days=1)

        if echecs:
            print(f"    reprise des {len(echecs)} jour(s) en échec…")
            restants = [j for j in echecs if not faire_le_jour(j)]
            avancement[f"{titre}_echecs"] = [f"{j:%Y-%m-%d}" for j in restants]
            suivi.write_text(json.dumps(avancement, indent=2))
            if restants:
                print(f"    ! {len(restants)} jour(s) toujours en échec, "
                      f"notés dans {suivi.name} — relancer plus tard")

    if annees_sautees:
        print(f"    (années sans publication, sautées : "
              f"{annees_sautees[0]}-{annees_sautees[-1]}, {len(annees_sautees)} ans)")
    print(f"--- {titre} terminé : {total} article(s) dans {sortie}")
