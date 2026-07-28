# Assemble le dossier de livraison resultats_PCA/ a partir de data/ et de
# rupture/sorties/ : copies renommees des .npz de PCA, CSV derives (spectre,
# composantes, pics, fenetres) et figures. Ne recalcule rien — tout vient des
# sorties de rupture/pca.py, rupture/nms.py et rupture/fenetres_masse.py.
# Trois grilles livrees : journalier (v1 brute et v2 nettoyee), blocs de 3
# jours et blocs de 7 jours (une seule version, le nettoyage y est sans objet).
# Usage : cd /data/elias/stage-mids && .venv/bin/python -m resultats_PCA.preparer
import os
import shutil

import numpy as np
import pandas as pd

DONNEES = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIES = os.path.join(ICI, "..", "rupture", "sorties")
FIGURES = os.path.join(ICI, "figures")
os.makedirs(FIGURES, exist_ok=True)

NORMES = (("z", "zscore"), ("01", "minmax"), ("col", "colonne"))
GRILLES = (("journalier", "lemonde", ("v1", "v2")),   # (etiquette, media, versions livrees)
           ("3j", "lemonde3j", ("",)),
           ("7j", "lemonde7j", ("",)))
JOURS = [f"j{d:+d}" for d in range(-15, 16)]

for etiquette, media, versions in GRILLES:
    fin = "" if etiquette == "journalier" else f"_{etiquette}"
    spectres = {}
    for version in versions:
        for norme, nom in NORMES:
            source = f"{DONNEES}/pca_{media}_{norme}{'_v2' if version == 'v2' else ''}.npz"
            colonne = f"{version}_{nom}" if version else nom
            shutil.copyfile(source, f"{ICI}/pca_{media}_{colonne}.npz")
            spectres[colonne] = np.load(source)["variance"]

    pd.DataFrame(spectres, index=np.arange(1, 32)).rename_axis("rang").to_csv(
        f"{ICI}/spectre{fin}.csv", float_format="%.8f")

    reference = "v2_zscore" if versions[0] else "zscore"
    composantes = np.load(f"{ICI}/pca_{media}_{reference}.npz")["composantes"]
    nom_csv = "composantes_v2_zscore.csv" if versions[0] else f"composantes{fin}_zscore.csv"
    pd.DataFrame(composantes, index=np.arange(1, 32), columns=JOURS).rename_axis(
        "composante").to_csv(f"{ICI}/{nom_csv}", float_format="%.8f")

    shutil.copyfile(f"{DONNEES}/fenetres_{media}.npz", f"{ICI}/entree_fenetres_{media}.npz")
    shutil.copyfile(f"{DONNEES}/pics_{media}_nms.csv", f"{ICI}/pics_{etiquette}.csv")

    d = np.load(f"{DONNEES}/fenetres_{media}.npz")
    table = pd.DataFrame(d["fenetres"], columns=JOURS)
    for cle in ("surprise", "N_t", "X_t", "date", "mot"):
        table.insert(0, cle, d[cle])
    table.to_csv(f"{ICI}/fenetres_{etiquette}.csv", index=False, float_format="%.2f")
    print(f"{etiquette:<11} {len(table):>6} fenetres | pca_{media}_*.npz, spectre{fin}.csv, "
          f"{nom_csv}, pics_{etiquette}.csv, fenetres_{etiquette}.csv", flush=True)

FIGS = (("pics_lemonde_internet_bnb2.png", "pics_internet.png"),
        ("nms_syrienne.png", "nms_syrienne.png"),
        ("pca_lemonde_variance.png", "spectre_v1.png"),
        ("pca_lemonde_variance_v2.png", "spectre_v2.png"),
        ("pca_lemonde_composantes.png", "composantes_v1.png"),
        ("pca_lemonde_composantes_v2.png", "composantes_v2.png"),
        ("pca_lemonde_plan12.png", "plan_c1c2_v1.png"),
        ("pca_lemonde_archetypes.png", "archetypes_v1.png"),
        ("pca_lemonde_reconstruction.png", "reconstruction_v1.png"),
        ("pca_lemonde_corpusvide.png", "artefact_corpus_vide_v1.png"),
        ("pca_lemonde3j_variance.png", "spectre_3j.png"),
        ("pca_lemonde3j_composantes.png", "composantes_3j.png"),
        ("pca_lemonde3j_archetypes.png", "archetypes_3j.png"),
        ("pca_lemonde7j_variance.png", "spectre_7j.png"),
        ("pca_lemonde7j_composantes.png", "composantes_7j.png"),
        ("pca_lemonde7j_archetypes.png", "archetypes_7j.png"))
for source, nom in FIGS:
    chemin = f"{SORTIES}/{source}"
    if os.path.exists(chemin):
        shutil.copyfile(chemin, f"{FIGURES}/{nom}")
    else:
        print(f"  {nom} : source absente de rupture/sorties, copie existante laissee en place")

print("FINI ->", os.path.relpath(ICI), flush=True)
