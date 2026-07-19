# Relève l'état frais du serveur gallica (ssh, lecture seule) et injecte les
# valeurs mécaniques dans site/static/dashboard.html : heure de mise à jour,
# barre disque, tailles et dernières écritures des bases.
# Les sections éditoriales (« En ce moment », avancement, cartes) ne sont pas touchées.
#
# Usage (sur le Mac, depuis la racine du dépôt) : python3 -m scripts.maj_dashboard

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DASHBOARD = Path(__file__).resolve().parent.parent / "site" / "static" / "dashboard.html"
PARIS = ZoneInfo("Europe/Paris")
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]

# Toutes les dates sont relevées en epoch (+%s) : pas de conversion UTC à la main.
COMMANDE_SSH = r'''
echo "=== date ==="; date +%s
echo "=== tmux ==="; tmux ls 2>/dev/null || echo "(aucune session)"
echo "=== process python ==="; ps -eo pid,etime,%cpu,%mem,args | grep "[p]ython" | grep -v vscode-server
echo "=== bases ==="; ls -l --time-style=+%s /data/elias/stage-mids/data/corpus/*.db /data/elias/stage-mids/data/urls.db 2>/dev/null
echo "=== disque ==="; df -h /data | tail -1
echo "=== pane scrapping ==="; tmux capture-pane -p -t scrapping 2>/dev/null | grep -v "^$" | tail -12
echo "=== pane build ==="; tmux capture-pane -p -t build 2>/dev/null | grep -v "^$" | tail -8
'''


def decouper_sections(texte):
    sections, nom = {}, None
    for ligne in texte.splitlines():
        m = re.match(r"^=== (.+) ===$", ligne)
        if m:
            nom = m.group(1)
            sections[nom] = []
        elif nom:
            sections[nom].append(ligne)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def taille_fr(octets):
    go = octets / 1024**3
    if go >= 10:
        return f"{go:.0f} Go"
    if go >= 1:
        return f"{go:.1f}".replace(".", ",") + " Go"
    return f"{octets / 1024**2:.0f} Mo"


def unite_fr(valeur):  # "1.9T" -> "1,9 To", "5.0T" -> "5 To"
    nombre, unite = valeur[:-1], valeur[-1]
    nombre = nombre.rstrip("0").rstrip(".").replace(".", ",")
    return f"{nombre} {unite}o"


def date_fr(ts, maintenant):
    d = datetime.fromtimestamp(ts, PARIS)
    if d.date() == maintenant.date():
        return f"aujourd'hui {d:%H} h {d:%M}"
    return f"{d.day} {MOIS[d.month - 1]}"


def remplacer(html, motif, remplacement, quoi):
    html, n = re.subn(motif, remplacement, html)
    if n != 1:
        print(f"ATTENTION : « {quoi} » non injecté ({n} occurrence(s) du motif)")
    return html


# --- Relevé ---
print("Relevé de l'état du serveur (ssh gallica, lecture seule)…", file=sys.stderr)
resultat = subprocess.run(["ssh", "gallica", COMMANDE_SSH], capture_output=True, text=True, timeout=60)
if resultat.returncode != 0:
    sys.exit(f"Échec du ssh : {resultat.stderr.strip()}")
sections = decouper_sections(resultat.stdout)

maintenant = datetime.fromtimestamp(int(sections["date"]), PARIS)
html = DASHBOARD.read_text()

# --- Heure de mise à jour ---
heure = f"{maintenant.day} {MOIS[maintenant.month - 1]} {maintenant.year}, {maintenant:%H} h {maintenant:%M}"
html = remplacer(html, r'(<strong id="maj-heure">)[^<]*(</strong>)', rf"\g<1>{heure}\g<2>", "heure de mise à jour")

# --- Disque /data ---
champs = sections["disque"].split()
total, utilise, libre, pct = champs[1], champs[2], champs[3], int(champs[4].rstrip("%"))
html = remplacer(html, r'(aria-label="Disque /data rempli à )\d+( %")', rf"\g<1>{pct}\g<2>", "aria-label disque")
html = remplacer(html, r'(id="disque-rempli" style="width:)\d+(%")', rf"\g<1>{pct}\g<2>", "barre disque")
detail = f"<strong>{unite_fr(utilise)}</strong> / {unite_fr(total)} ({pct} %) — {unite_fr(libre)} libres"
html = remplacer(html, r'(<span class="disque-txt" id="disque-detail">).*?(</span>)', rf"\g<1>{detail}\g<2>", "détail disque")

# --- Bases : tailles + dernières écritures ---
bases_serveur = {}  # nom de fichier -> (octets, epoch mtime)
for ligne in sections["bases"].splitlines():
    champs = ligne.split()
    bases_serveur[champs[-1].rsplit("/", 1)[-1]] = (int(champs[4]), int(champs[5]))

bases_html = re.findall(r'data-taille="([^"]+)"', html)
for nom in bases_html:
    if nom not in bases_serveur:
        print(f"ATTENTION : {nom} affichée dans le dashboard mais absente du serveur")
        continue
    octets, mtime = bases_serveur[nom]
    html = remplacer(html, rf'(data-taille="{nom}">)[^<]*(</td>)', rf"\g<1>{taille_fr(octets)}\g<2>", f"taille {nom}")
    html = remplacer(html, rf'(data-ecriture="{nom}">)[^<]*(</td>)', rf"\g<1>{date_fr(mtime, maintenant)}\g<2>", f"écriture {nom}")

DASHBOARD.write_text(html)

# --- Résumé pour la passe éditoriale ---
print(f"Dashboard mis à jour : {heure} (heure de Paris)")
print(f"Disque /data : {utilise} / {total} ({pct} %)")
non_affichees = sorted(set(bases_serveur) - set(bases_html))
if non_affichees:
    print(f"Bases sur le serveur non affichées : {', '.join(non_affichees)}")
for nom in ("tmux", "process python", "pane scrapping", "pane build"):
    print(f"\n=== {nom} ===\n{sections.get(nom) or '(vide)'}")
