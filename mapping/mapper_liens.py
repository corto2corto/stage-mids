"""Agent qui explore un site (sans sitemap exploitable) pour construire la liste
de ses URLs d'articles, page par page a partir de l'accueil.

    python -m mapping.mapper_liens blast https://www.blast-info.fr

Le motif de reconnaissance des articles est trouve par l'agent (regex), puis
applique par du code classique a tous les liens vus -- l'agent ne juge jamais
un lien "a la main". Le CSV est ecrit au fil de l'eau, independamment de ce
que dit l'agent, pour survivre a un plantage en tache de fond.

Bornes dures (verifiees par le code avant chaque appel, jamais laissees a
l'appreciation du modele) :
  - MAX_PAGES pages visitees
  - STAGNATION pages consecutives sans nouvelle URL trouvee
  - MAX_TOKENS tokens cumules (entree + sortie) sur toute la session
"""
import csv
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import anthropic

MEDIA, RACINE = sys.argv[1], sys.argv[2].rstrip("/")
DOMAINE = urlparse(RACINE).netloc
SORTIE = f"exploration/{MEDIA}_url.csv"

MAX_PAGES = 150
STAGNATION = 15
MAX_TOKENS = 300_000   # ~0,60 $ au tarif Sonnet actuel (2 $/M tokens en entree)

visitees = set()
liens_vus = {}          # url -> texte du lien (contexte donne a l'agent)
articles = set()
motif_courant = None
stagnation = 0
dernier_compte = 0


def sauvegarder():
    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url"])
        for u in sorted(articles):
            w.writerow([u])


def appliquer_motif(regex: str) -> str:
    global motif_courant
    motif_courant = regex
    try:
        motif = re.compile(regex)
    except re.error as e:
        return f"Regex invalide : {e}"
    avant = len(articles)
    matches, non_matches = [], []
    for u in liens_vus:
        chemin = urlparse(u).path
        if motif.match(chemin):
            articles.add(u)
            if len(matches) < 5:
                matches.append(u)
        elif len(non_matches) < 5:
            non_matches.append(u)
    sauvegarder()
    return (f"{len(articles)} articles au total ({len(articles) - avant} nouveaux).\n"
            f"Exemples matches : {matches}\nExemples non-matches : {non_matches}")


def visiter(url: str) -> str:
    global stagnation, dernier_compte
    if url in visitees:
        return "Deja visitee."
    visitees.add(url)
    try:
        r = requests.get(url, timeout=10,
                          headers={"User-Agent": "Mozilla/5.0 (recherche academique, mapping-agent)"})
    except Exception as e:
        return f"Echec : {e}"
    time.sleep(1)  # politesse envers le serveur

    soup = BeautifulSoup(r.text, "html.parser")
    nouveaux = []
    for a in soup.find_all("a", href=True):
        u = urljoin(url, a["href"]).split("#")[0]
        if urlparse(u).netloc != DOMAINE or u in liens_vus:
            continue
        liens_vus[u] = a.get_text(strip=True)[:80]
        nouveaux.append(u)

    if motif_courant:
        appliquer_motif(motif_courant)
    stagnation = stagnation + 1 if len(articles) == dernier_compte else 0
    dernier_compte = len(articles)

    echantillon = [(u, liens_vus[u]) for u in nouveaux[:40]]
    return f"{len(nouveaux)} nouveaux liens.\n" + "\n".join(f"{u}  ({t})" for u, t in echantillon)


def etat() -> str:
    return f"{len(visitees)}/{MAX_PAGES} pages visitees, {len(articles)} articles trouves, {stagnation} pages sans nouveaute."


OUTILS = [
    {"name": "visiter",
     "description": "Telecharge une page et liste ses nouveaux liens internes.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "appliquer_motif",
     "description": "Applique une regex (sur le CHEMIN de l'URL, ex '^/[a-z-]+/\\d{4}/\\d{2}/\\d{2}/[a-z0-9-]+$') "
                     "a tous les liens vus jusqu'ici, pour classer les articles. Peut etre rappele pour affiner.",
     "input_schema": {"type": "object", "properties": {"regex": {"type": "string"}}, "required": ["regex"]}},
    {"name": "etat",
     "description": "Donne l'avancement (pages visitees, articles trouves, stagnation).",
     "input_schema": {"type": "object", "properties": {}}},
]
FONCTIONS = {"visiter": visiter, "appliquer_motif": appliquer_motif, "etat": etat}

client = anthropic.Anthropic()
messages = [{"role": "user", "content": (
    f"Tu explores le site {RACINE} pour trouver toutes ses URLs d'articles. "
    f"Commence par visiter la page d'accueil, repere le motif des URLs d'articles "
    f"(different des pages de categorie/tags/pagination), verifie-le avec appliquer_motif, "
    f"puis visite des pages de categorie et suis la pagination pour en trouver d'autres. "
    f"Budget : {MAX_PAGES} pages max. Arrete-toi (reponds sans appeler d'outil) des que "
    f"tu juges avoir fait le tour ou que la stagnation est elevee."
)}]

tokens_utilises = 0
while len(visitees) < MAX_PAGES and stagnation < STAGNATION:
    if tokens_utilises >= MAX_TOKENS:
        print(f"Budget de {MAX_TOKENS} tokens atteint, arret.")
        break

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        tools=OUTILS,
        messages=messages,
    )
    tokens_utilises += response.usage.input_tokens + response.usage.output_tokens
    print(f"[{tokens_utilises} tokens cumules] ", end="")

    if response.stop_reason != "tool_use":
        for bloc in response.content:
            if bloc.type == "text":
                print(bloc.text)
        break

    messages.append({"role": "assistant", "content": response.content})
    resultats = []
    for bloc in response.content:
        if bloc.type == "tool_use":
            sortie = FONCTIONS[bloc.name](**bloc.input)
            print(f"{bloc.name}({bloc.input}) -> {sortie[:100]}")
            resultats.append({"type": "tool_result", "tool_use_id": bloc.id, "content": sortie})
    messages.append({"role": "user", "content": resultats})

sauvegarder()
print(f"\nTermine : {len(articles)} URLs dans {SORTIE} "
      f"({len(visitees)} pages visitees, {tokens_utilises} tokens).")
