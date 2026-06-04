"""Détection des paywalls : vérifie qu'un article récupéré n'est pas tronqué.

Principe : sur les sites à paywall « dur », un article bloqué contient une
phrase-signal caractéristique (« il vous reste X% »…). Si cette phrase est
présente dans le HTML, le bypass a échoué et l'article est incomplet : on ne
doit pas le stocker.

Un média absent de SIGNAUX_PAYWALL (paywall « mou » : texte toujours complet)
est considéré OK par défaut. Idem pour un signal laissé vide, en attendant de
régler le bypass du site.

ÉTAT (2026-06-04) : signal paris_match renseigné (« La suite de cet article est
réservée aux abonnés », confirmé sur 8/8 articles). Restent sans signal :
le_nouvel_observateur (seul un badge apparaît, pas de vraie troncature) et
les_echos (échantillon = archives en texte complet, à reconfirmer sur du récent).
Tout nouveau média scrapé devra aussi être ajouté à SIGNAUX_PAYWALL (ou laissé
hors du dict s'il s'agit d'un paywall mou).
"""

import re

from bs4 import BeautifulSoup

# Phrase-signal de troncature par média (recherchée sans tenir compte de la casse).
# Sa présence dans le texte = article tronqué = bypass échoué.
SIGNAUX_PAYWALL = {
    # Bypass validé : signaux confirmés (ils disparaissent quand le bypass marche).
    "le_figaro": r"il vous reste\s*\d+\s*%\s*à découvrir",
    "le_monde":  r"il vous reste\s*[\d.,]+\s*%\s*de cet article à lire",
    "telerama":  r"cet article est réservé aux abonnés",
    "paris_match": r"la suite de cet article est réservée aux abonnés",
    # Signal encore à définir (TODO) :
    # - le_nouvel_observateur : seul le *badge* « Article réservé aux abonnés »
    #   apparaît (idem le_monde sur des articles complets) → pas un signal fiable.
    # - les_echos : échantillon = archives 1991 en texte complet (paywall cosmétique),
    #   mais le corpus visé est récent → à reconfirmer sur des URLs récentes.
    "le_nouvel_observateur": "",
    "les_echos":             "",
}


def bypass_reussi(media, html):
    """Retourne True si l'article semble complet (aucune phrase-signal de paywall).

    Un média sans signal défini (paywall mou, ou signal pas encore réglé) est
    considéré OK par défaut.
    """
    motif = SIGNAUX_PAYWALL.get(media)
    if not motif:
        return True
    texte = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return re.search(motif, texte, re.IGNORECASE) is None
