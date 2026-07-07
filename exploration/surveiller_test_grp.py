"""Surveillance du test : toutes les 60 s, un point de situation — rythme par
média (+N/min), blocages BDD, qualité des derniers CSV écrits, et santé du
serveur (load, RAM dispo, iowait, RSS cumulée des Firefox). Chaque point est
aussi consigné en une ligne dans metriques.csv pour le rapport final.

À lancer depuis la racine du clone v2, dans une fenêtre tmux :
  python -m exploration.surveiller_test_grp >> exploration/test_run_grp/surveillance.log
"""

import csv
import os
import sqlite3
import subprocess
import time
from pathlib import Path

DOSSIER = Path("/data/elias/stage-mids-v2/exploration/test_run_grp")
METRIQUES = DOSSIER / "metriques.csv"

if not METRIQUES.exists():
    METRIQUES.write_text("horodatage,ok,ko,debit_min,load1,ram_dispo_go,"
                         "iowait_pct,firefox_rss_go,csv_mo,blocages\n")

precedent = {}
cpu_prec = None
while True:
    conn = sqlite3.connect(DOSSIER / "urls.db", timeout=10)
    lignes = conn.execute("SELECT media, SUM(etat=2), SUM(etat=1) FROM urls "
                          "WHERE etat > 0 GROUP BY media ORDER BY media").fetchall()
    conn.close()

    bloques = sum(1 for l in open(DOSSIER / "grp.log", encoding="utf-8", errors="replace")
                  if "database is locked" in l or "OperationalError" in l)
    total_ok = sum(ok for _, ok, _ in lignes)
    total_ko = sum(ko for _, _, ko in lignes)
    debit = total_ok + total_ko - precedent.get("_total", 0)
    precedent["_total"] = total_ok + total_ko

    # Santé serveur : load, RAM dispo, iowait (delta /proc/stat), RSS Firefox.
    load1 = os.getloadavg()[0]
    meminfo = {l.split(":")[0]: int(l.split()[1])
               for l in open("/proc/meminfo") if ":" in l}
    ram_dispo = meminfo["MemAvailable"] / 1024 / 1024
    cpu = [int(x) for x in open("/proc/stat").readline().split()[1:]]
    if cpu_prec:
        delta = [a - b for a, b in zip(cpu, cpu_prec)]
        iowait = 100 * delta[4] / max(sum(delta), 1)
    else:
        iowait = 0.0
    cpu_prec = cpu
    ps = subprocess.run(["ps", "-eo", "rss,comm"], capture_output=True, text=True)
    rss_ff = sum(int(l.split()[0]) for l in ps.stdout.splitlines()[1:]
                 if "firefox" in l) / 1024 / 1024
    csv_mo = sum(f.stat().st_size for f in DOSSIER.glob("csv/*.csv")) / 1024 / 1024

    print(f"\n[{time.strftime('%H:%M:%S')}] {total_ok} succès, {total_ko} échecs, "
          f"débit {debit}/min, blocages BDD {bloques} | load {load1:.1f}, "
          f"RAM dispo {ram_dispo:.1f} Go, iowait {iowait:.0f}%, "
          f"firefox {rss_ff:.1f} Go, csv {csv_mo:.1f} Mo")
    with open(METRIQUES, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')},{total_ok},{total_ko},{debit},"
                f"{load1:.1f},{ram_dispo:.1f},{iowait:.0f},{rss_ff:.2f},"
                f"{csv_mo:.1f},{bloques}\n")

    for media, ok, ko in lignes:
        d = ok + ko - precedent.get(media, 0)
        precedent[media] = ok + ko
        print(f"  {media:<24} {ok:>5} ok {ko:>4} ko   +{d}/min")

    recents = sorted(DOSSIER.glob("csv/*.csv"), key=lambda p: p.stat().st_mtime,
                     reverse=True)[:3]
    for chemin in recents:
        with open(chemin, newline="", encoding="utf-8") as f:
            rangees = list(csv.DictReader(f))
        if not rangees:
            continue
        der = rangees[-1]
        vides = [c for c in ("titre", "date", "contenu") if not (der.get(c) or "").strip()]
        verdict = f"CHAMPS VIDES : {', '.join(vides)}" if vides else "métadonnées OK"
        print(f"  csv {chemin.stem:<21} {len(rangees)} lignes, "
              f"contenu={len(der.get('contenu') or '')} car., {verdict}")

    time.sleep(60)
