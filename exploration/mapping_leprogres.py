"""Construit la liste des URLs d'articles Le Progrès (leprogres.fr) via les
pages d'archives datees https://www.leprogres.fr/archives/YYYY/JJ-MM
(ATTENTION format jour-mois, pas mois-jour -- verifie par smoke-test manager :
archives/2018 liste bien des href /archives/2018/JJ-MM). Pas de pagination :
une page par jour. Chaque page annuelle https://www.leprogres.fr/archives/YYYY
liste les jours de l'annee sous forme de href relatifs /archives/YYYY/JJ-MM.
Chaque page-jour contient les liens articles au format href relatif
/<rubrique>/YYYY/MM/DD/<slug> (ordre YYYY/MM/DD, different de l'URL page-jour
elle-meme qui est en JJ-MM) -- tous les hrefs conformes sont gardes et
dedupliques globalement. Pas de filtre par date de page : le smoke-test a
montre qu'une page-jour melange occasionnellement quelques articles de la
veille (ex. un article date 07/05 vu sur la page du 07/06), mais comme la
deduplication est globale (pas un decompte par jour), ça ne cree ni doublon
ni erreur -- juste un decompte "urls_mois" legerement approximatif, sans
consequence sur le CSV final.

Profondeur 2018 -> 2026 (avant 2018 : rien, anciennes URLs renvoient 410).
~3 100 pages-jour (365/366 jours x 9 ans, dont 2026 partielle) a 1.5s de
politesse -> environ 2s/page tout compris -> environ 1h45 de crawl.

    python -m exploration.mapping_leprogres

Relancable par annee : editer la constante ANNEES pour ne refaire que les
annees manquantes/interrompues -- le fichier de sortie est complete par
ajout (pas ecrase), les URLs deja presentes sont chargees au demarrage et
jamais reecrites. Tolere les 410/404 (pages/articles depublies) : ignore et
continue.
"""
import csv
import os
import re
import time

from tqdm import tqdm

from scraping import basic

ANNEES = range(2018, 2027)  # 2018 -> 2026 inclus (pre-2018 : rien, 410)
DOMAINE = "https://www.leprogres.fr"
SORTIE = "exploration/leprogres_url.csv"
MOTIF_JOUR = re.compile(r'href="(?:https://www\.leprogres\.fr)?/archives/(\d{4})/(\d{2})-(\d{2})"')
MOTIF_ARTICLE = re.compile(r'href="(?:https://www\.leprogres\.fr)?(/[^/"]+/\d{4}/\d{2}/\d{2}/[^"]+)"')

deja = set()
if os.path.exists(SORTIE):  # reprise : les URLs deja ecrites ne sont pas redemandees
    with open(SORTIE, newline="", encoding="utf-8") as f:
        deja.update(l[0] for l in list(csv.reader(f))[1:] if l)
    print(f"{len(deja)} URLs deja presentes dans {SORTIE}")

nouveau_fichier = not os.path.exists(SORTIE)
sortie = open(SORTIE, "a", newline="", encoding="utf-8")
w = csv.writer(sortie)
if nouveau_fichier:
    w.writerow(["url"])

session = basic.ouvrir_session()

for annee in ANNEES:
    try:
        r = session.get(f"{DOMAINE}/archives/{annee}", timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"archives/{annee} : echec ({e}), annee ignoree")
        continue

    jours = sorted(set((a, j, m) for a, j, m in MOTIF_JOUR.findall(r.text) if a == str(annee)))
    print(f"{annee} : {len(jours)} jours a parcourir")
    time.sleep(1.5)  # politesse envers le serveur

    mois_courant, urls_mois = None, 0
    for a, j, m in tqdm(jours, desc=str(annee)):
        page = f"{DOMAINE}/archives/{a}/{j}-{m}"
        try:
            r = session.get(page, timeout=30)
            if r.status_code in (404, 410):
                time.sleep(1.5)
                continue  # page depubliee, tant pis pour ce jour
            r.raise_for_status()
        except Exception as e:
            print(f"{page} : echec ({e}), ignoree")
            time.sleep(1.5)
            continue

        if m != mois_courant:  # progression par mois
            if mois_courant is not None:
                print(f"{a}-{mois_courant} : {urls_mois} URLs, {len(deja)} cumulees")
            mois_courant, urls_mois = m, 0

        nouvelles = {DOMAINE + chemin for chemin in MOTIF_ARTICLE.findall(r.text)} - deja
        for u in nouvelles:
            w.writerow([u])
        sortie.flush()  # ecriture au fil de l'eau : reprise facile en cas d'interruption
        deja.update(nouvelles)
        urls_mois += len(nouvelles)

        time.sleep(1.5)  # politesse envers le serveur
    print(f"{a}-{mois_courant} : {urls_mois} URLs, {len(deja)} cumulees")

sortie.close()
print(f"Termine : {len(deja)} URLs dans {SORTIE}")
