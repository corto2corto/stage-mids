"""Surveillance du test des groupes : toutes les 60 s, un point de situation —
rythme de scraping par média (+N/min), blocages BDD relevés dans grp.log, et
contrôle qualité des 3 derniers CSV écrits (longueur du contenu, métadonnées).

À lancer depuis la racine du clone v2, dans une fenêtre tmux :
  python -m exploration.surveiller_test_grp >> exploration/test_run_grp/surveillance.log
"""

import csv
import sqlite3
import time
from pathlib import Path

DOSSIER = Path("/data/elias/stage-mids-v2/exploration/test_run_grp")

precedent = {}
while True:
    conn = sqlite3.connect(DOSSIER / "urls.db", timeout=10)
    lignes = conn.execute("SELECT media, SUM(etat=2), SUM(etat=1) FROM urls "
                          "WHERE etat > 0 GROUP BY media ORDER BY media").fetchall()
    conn.close()

    bloques = sum(1 for l in open(DOSSIER / "grp.log", encoding="utf-8", errors="replace")
                  if "database is locked" in l or "OperationalError" in l)
    total_ok = sum(ok for _, ok, _ in lignes)
    total_ko = sum(ko for _, _, ko in lignes)
    print(f"\n[{time.strftime('%H:%M:%S')}] {total_ok} succès, {total_ko} échecs, "
          f"blocages BDD : {bloques}")

    for media, ok, ko in lignes:
        delta = ok + ko - precedent.get(media, 0)
        precedent[media] = ok + ko
        print(f"  {media:<24} {ok:>4} ok {ko:>4} ko   +{delta}/min")

    # Qualité d'écriture : dernière ligne des 3 CSV les plus récemment modifiés.
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
