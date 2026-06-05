"""Détection des paywalls : vérifie qu'un article récupéré n'est pas tronqué.

Deux contrôles, dans cet ordre :
1. Corps vide → échec. Si l'extraction du corps (sélecteurs de extraction.py)
   ne renvoie rien, l'article n'a pas été chargé/débloqué. C'est le cas de
   le_monde paywallé : le message de coupure est HORS du conteneur d'article,
   donc aucune phrase-signal n'aiderait — seul un corps vide trahit le blocage.
2. Phrase-signal → échec. Sur les sites à paywall « dur », un article bloqué
   contient une phrase caractéristique (« il vous reste X% »…). Sa présence
   signifie bypass échoué = article incomplet : on ne stocke pas.

Un média absent de SIGNAUX_PAYWALL (paywall « mou » : texte toujours complet)
est considéré OK par défaut dès lors que son corps n'est pas vide. Idem pour un
signal laissé vide, en attendant de régler le bypass du site.

ÉTAT (2026-06-04) : signaux calés après analyse d'un échantillon de 10 articles
par média (cf. exploration/echantillon_tailles2.txt) :
- les_echos : signal renseigné (« contenu réservé aux abonnés »), validé sur les
  2 articles récents tronqués ; les 8 archives complètes passent bien le check.
- le_monde : regex élargie. Le format récent (« Il vous reste X % de cet article
  à lire ») ne couvrait que 2/10 ; les archives utilisent « Envie de lire la
  suite ? » → les deux sont désormais captés. Cas non couvert : une page « boutique »
  sans corps ni phrase paywall (échec de chargement) — relève d'un contrôle de
  longueur, pas d'un signal.
- telerama : regex élargie à « réservé(e) aux abonnés » pour capter aussi le badge
  court « Réservé aux abonnés » (le regex précédent ratait 1 article sur 4 tronqués).
- nice_matin : ajouté (« débloquer votre article »), capte les 7 articles tronqués.
- le_nouvel_observateur : corps présent sur les 10 articles (bypass OK) → reste vide.
- le_figaro, le_capital, le_journal_du_dimanche, valeurs_actuelles : aucun article
  tronqué dans l'échantillon (paywall mou ou bypass OK) → laissés hors du dict.

PIÈGES à éviter (libellés d'UI présents sur TOUTES les pages, complètes comprises) :
« réservée à nos inscrits » (telerama) et « réservée aux utilisateurs connectés »
(nice_matin) ne sont PAS des signaux de troncature.

Tout nouveau média scrapé devra aussi être ajouté à SIGNAUX_PAYWALL (ou laissé
hors du dict s'il s'agit d'un paywall mou).
"""

import re

from bs4 import BeautifulSoup

from scraping import extraction

# Phrase-signal de troncature par média (recherchée sans tenir compte de la casse).
# Sa présence dans le texte = article tronqué = bypass échoué.
SIGNAUX_PAYWALL = {
    # Bypass validé : signaux confirmés (ils disparaissent quand le bypass marche).
    "le_figaro":   r"il vous reste\s*\d+\s*%\s*à découvrir",
    # le_monde : deux formats de troncature cohabitent (récent = « il vous reste
    # X % », archives = « Envie de lire la suite ? »).
    "le_monde":    r"il vous reste\s*[\d.,]+\s*%\s*de cet article à lire|envie de lire la suite",
    # telerama : badge « Cet article est réservé aux abonnés » OU « Réservé aux
    # abonnés ». NE matche PAS « réservée à nos inscrits » (UI présente partout).
    "telerama":    r"réservée?s? aux abonnés",
    "les_echos":   r"contenu réservé aux abonnés",
    # paris_match : signal RETIRÉ. La comparaison avec/sans bypass montre que
    # « La suite… réservée aux abonnés » persiste même bypass actif et sur des
    # articles qui se lisent comme complets → risque de rejeter du bon contenu.
    # Priorité = ne pas perdre d'articles → on ne met aucun signal (OK par défaut).
    "paris_match": "",
    # nice_matin : « Abonnez-vous… ou regardez une publicité pour débloquer votre
    # article ». On vise le fragment distinctif (les libellés « réservée aux
    # utilisateurs connectés » sont sur toutes les pages → inutilisables).
    "nice_matin":  r"débloquer votre article",
    # le_nouvel_observateur : corps présent sur tout l'échantillon (bypass OK), seul
    # un badge « Abonné » apparaît sur les teasers → pas de signal de troncature.
    "le_nouvel_observateur": "",
}


def bypass_reussi(media, html):
    """Retourne True si l'article semble complet.

    Échec (False) si le corps extrait est vide, OU si une phrase-signal de paywall
    est présente. Un média sans signal défini (paywall mou, ou signal pas encore
    réglé) est considéré OK par défaut, dès lors que son corps n'est pas vide.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Corps vide = article non chargé/débloqué (cf. le_monde paywallé).
    regle = extraction.MEDIAS[media]["corps"]
    if not extraction.extraire_corps(regle, soup).strip():
        return False

    # 2. Phrase-signal de troncature.
    motif = SIGNAUX_PAYWALL.get(media)
    if not motif:
        return True
    texte = soup.get_text(" ", strip=True)
    return re.search(motif, texte, re.IGNORECASE) is None
