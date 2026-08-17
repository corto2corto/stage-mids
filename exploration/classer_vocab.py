# Classification grammaticale du vocabulaire pour la campagne PCA (tourne sur
# le MAC, pas gallica : spaCy + Lexique383 y sont installes). Pour chaque mot
# des CSV passes en argument (colonne mot) :
# - les formes elidees de la tokenisation (l'economie, s'agit, d'euros...)
#   sont classees sur leur forme de base (economie, agit, euros) ;
# - Lexique383 (125 653 formes flechies, fiable sur des formes isolees en
#   minuscules) : toutes analyses verbales -> verbe, sinon NOM prime sur ADJ ;
# - un mot NOM-seul de frequence lexique < 0,5/million que spaCy etiquette
#   PROPN une fois capitalise est un nom propre homographe d'un mot commun
#   rare (hollande le tissu, allemagne, gaulle) -> nom_propre ; les memes a
#   frequence >= 0,5 (paris...) sont listes pour arbitrage manuel via
#   AMBIGUS_VALIDES ;
# - les mots absents du lexique (les bases ngram sont en minuscules) sont
#   tranches par spaCy sur la forme capitalisee, PROPN -> nom_propre.
# Complete campagne_pca/vocab_categories.csv (mot, categorie, source) sans
# reclasser l'existant, pour etendre aux vocabulaires des autres medias.
# Usage : .venv/bin/python -m exploration.classer_vocab <vocab1.csv> [...]
import os
import re
import sys

import pandas as pd
import spacy
from pylexique import Lexique383

SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "campagne_pca", "vocab_categories.csv")
ELISION = re.compile(r"^(l|d|s|n|j|m|t|c|qu|jusqu|lorsqu|puisqu|quelqu)'(.+)$")
SEUIL_FREQ = 0.5   # /million ; en dessous, l'homographe commun est negligeable
# noms propres homographes d'un mot commun FREQUENT, arbitres a la main
# d'apres la liste d'audit imprimee par ce script (villes surtout)
AMBIGUS_VALIDES = {"paris", "tours", "nancy", "nice", "angers", "caen",
                   "rennes", "metz", "brest", "sèvres", "orange",
                   # arbitres d'apres l'audit du 31/07/2026 (top-10k lemonde) :
                   # villes/pays/lieux, prenoms clairs, institutions — les
                   # homographes trop frequents (pierre, olivier, madeleine,
                   # manche, marais, mont...) restent des noms communs
                   "canada", "cannes", "chili", "damas", "vichy", "york",
                   "los", "landes", "havre", "élysée", "figaro", "napoléon",
                   "reich", "jean", "jacques", "claude", "gilles", "joseph",
                   "jules", "marc", "max", "maxime", "renaud", "robert",
                   "serge", "sophie", "sylvie", "thomas", "tom", "xavier",
                   "jack",
                   # audit figaro/echos du 31/07/2026
                   "blair", "auvergne", "rochelle", "charlotte", "virginie",
                   "véronique", "universal", "coca", "bull"}

mots = []
for chemin in sys.argv[1:]:
    v = pd.read_csv(chemin, dtype={"mot": str}, keep_default_na=False)
    mots.extend(v["mot"])
deja = set()
if os.path.exists(SORTIE):
    deja = set(pd.read_csv(SORTIE, dtype={"mot": str}, keep_default_na=False)["mot"])
nouveaux = [m for m in dict.fromkeys(mots) if m not in deja]
print(f"{len(mots)} mots lus, {len(deja)} deja classes, {len(nouveaux)} nouveaux")

lex = Lexique383().lexique
nlp = spacy.load("fr_core_news_md", disable=("parser", "ner", "lemmatizer"))

# 1re passe : Lexique sur la forme de base ; on met de cote ce qui attend spaCy
resolus = {}          # mot -> (categorie, source)
attente = []          # (mot, base, regle) a trancher par spaCy sur Base
audit = []            # candidats nom propre a homographe frequent, non arbitres
for m in nouveaux:
    e = ELISION.match(m)
    base = e.group(2) if e else m
    entree = lex.get(base)
    if entree is None:
        attente.append((m, base, "absent"))
        continue
    cgrams = {x.cgram for x in (entree if isinstance(entree, list) else [entree])}
    freq = max(float(x.freqfilms2 or 0) if str(x.freqfilms2) not in ("", "0") else 0.0
               for x in (entree if isinstance(entree, list) else [entree]))
    freq = max(freq, max(float(x.freqlivres or 0) if str(x.freqlivres) not in ("", "0") else 0.0
                         for x in (entree if isinstance(entree, list) else [entree])))
    if cgrams <= {"VER", "AUX"}:
        resolus[m] = ("verbe", "lexique")
    elif "NOM" in cgrams:
        if base in AMBIGUS_VALIDES:
            resolus[m] = ("nom_propre", "manuel")
        elif cgrams == {"NOM"} and freq < SEUIL_FREQ:
            attente.append((m, base, "nom_rare"))
        else:
            resolus[m] = ("nom", "lexique")
            if cgrams == {"NOM"}:
                attente.append((m, base, "audit"))
    elif "ADJ" in cgrams:
        resolus[m] = ("adj", "lexique")
    else:
        resolus[m] = ("autre", "lexique")

# 2e passe : spaCy sur les formes capitalisees mises en attente
CORRESPONDANCE = {"NOUN": "nom", "VERB": "verbe", "AUX": "verbe", "ADJ": "adj"}
for (m, base, regle), doc in zip(attente, nlp.pipe(b.capitalize() for _, b, _ in attente)):
    propn = doc[0].pos_ == "PROPN"
    if regle == "absent":
        resolus[m] = ("nom_propre", "spacy") if propn else \
                     (CORRESPONDANCE.get(doc[0].pos_, "autre"), "spacy")
    elif regle == "nom_rare":
        resolus[m] = ("nom_propre", "lexique+spacy") if propn else ("nom", "lexique")
    elif regle == "audit" and propn and base not in AMBIGUS_VALIDES:
        audit.append(m)

df = pd.DataFrame([(m,) + resolus[m] for m in nouveaux],
                  columns=["mot", "categorie", "source"])
df.to_csv(SORTIE, mode="a" if deja else "w", header=not deja, index=False)
print(f"{len(df)} classes -> {SORTIE}")
print(df["categorie"].value_counts().to_string())
if audit:
    print(f"\nAUDIT — noms communs frequents que spaCy capitalise en PROPN "
          f"({len(audit)}) ; ajouter les vrais noms propres a AMBIGUS_VALIDES "
          f"et relancer :\n" + " ".join(sorted(audit)))
