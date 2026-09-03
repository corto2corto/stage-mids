# Exporte, pour le site (ngram-press, onglet Tests statistiques), un fichier par
# PCA de sauts deja calculee : tout ce qu'il faut pour dessiner les trois figures
# des rapports de presentation sans rien recalculer — les quatre premieres
# composantes et leurs parts de variance, les tranches de projection (recette de
# la figure 4 d'Aubrun, Morel, Benzaquen, Bouchaud, PNAS 2025 : fenetres triees
# par projection, decoupees aux quantiles 10/35/65/90 %, profil moyen par
# tranche) et les fenetres archetypes des deux cotes.
# Deux familles de sources, meme sortie :
# - corpus unifie / etendu : fenetres_<nom>.npz de data/pics_*, PCA rejouee aux
#   seuils 4 et 6 exactement comme exporter_presentation.py (z-score par fenetre,
#   orientation vers la queue lourde des projections, seuil 4 aligne sur le
#   seuil 6) ; archetypes parmi le vocabulaire parlant, >= 20 occurrences au pic ;
# - campagne par media : caches data/cache_pca/<prefixe>.npz (un seul seuil, PCA
#   deja faite), archetypes filtres par volume comme figures_lib.filtre_volume().
# Toutes les composantes sont orientees vers la queue lourde de leurs projections
# (convention du corpus unifie ; les caches de campagne ne l'etaient pas).
# Sorties dans campagne_pca/site_pca/ : <id>.npz (champs decrits dans README.md)
# et catalogue.csv (une ligne par PCA).
# Usage : .venv/bin/python -m campagne_pca.scripts.exporter_site [id...]
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from rupture.pca import normaliser, pca
from campagne_pca.scripts.configs import CONFIGS, verifier

ICI = Path(__file__).resolve().parent.parent            # campagne_pca/
DATA, SORTIE = ICI / "data", ICI / "site_pca"
N_COMP, N_ARCH = 4, 4
QUANTILES = np.array([0, .10, .35, .65, .90, 1])         # figure 4 d'Aubrun et al.
UNITES = {1: "jours", 3: "blocs de 3 jours", 7: "semaines"}
VOCAB_MONDE = "top-10 000 du Monde (jours actifs 1944-2025)"

# corpus unifie / etendu : fenetres, vocabulaire parlant, pas, vocabulaire de la PCA
UNIFIES = {
    "unifie1j": ("pics_unifie/fenetres_unifie.npz", "pics_unifie/vocab600.txt", 1, VOCAB_MONDE),
    "unifie3j": ("pics_unifie/fenetres_unifie3j.npz", "pics_unifie/vocab600.txt", 3, VOCAB_MONDE),
    "etendu1j": ("pics_etendu/fenetres_etendu.npz", "pics_etendu/vocab_parlant_etendu.txt", 1,
                 "étendu, 11 780 mots (top-10 000 + 1 780 mots récents)"),
    "etendu3j": ("pics_etendu/fenetres_etendu3j.npz", "pics_etendu/vocab_parlant_etendu.txt", 3,
                 "étendu, 11 780 mots (top-10 000 + 1 780 mots récents)"),
}


def orienter(comp, proj):
    """Chaque composante tournee vers la queue lourde de ses projections."""
    signes = np.sign((proj ** 3).sum(axis=0))
    signes[signes == 0] = 1
    return comp * signes[:, None], proj * signes


def charger_unifie(nom):
    fichier, parlant, pas, vocab = UNIFIES[nom]
    fen = np.load(DATA / fichier)
    PARLANT = set((DATA / parlant).read_text(encoding="utf-8").split("\n")) - {""}
    res = {}
    for s in (4, 6):
        m = fen["surprise"] >= s
        Z, garde = normaliser(fen["fenetres"][m].astype(np.float64), "z")
        comp, var, proj = pca(Z)
        comp, proj = orienter(comp, proj)
        mot, occ = fen["mot"][m][garde].astype(str), fen["X_t"][m][garde].astype(np.int64)
        res[s] = dict(seuil=float(s), Z=Z, comp=comp, var=var, proj=proj, mot=mot,
                      date=fen["date"][m][garde].astype(np.int64), occ=occ, plancher=20.0,
                      eligibles=np.where(np.isin(mot, list(PARLANT)) & (occ >= 20))[0])
    # le signe est arbitraire et la regle queue-lourde peut trancher autrement
    # selon le seuil : le seuil 4 est aligne sur le seuil 6 (exporter_presentation)
    ali = np.sign(np.einsum("ij,ij->i", res[4]["comp"], res[6]["comp"]))
    ali[ali == 0] = 1
    res[4]["comp"], res[4]["proj"] = res[4]["comp"] * ali[:, None], res[4]["proj"] * ali
    meta = dict(id=nom, famille="corpus unifié", corpus="corpus unifié (36 médias)",
                vocabulaire=vocab, pas_jours=pas, demi=15, source=fichier, attendu=None)
    return meta, [res[4], res[6]]


def charger_cache(prefixe):
    p = CONFIGS[prefixe]
    fichier = f"cache_pca/{prefixe}.npz"
    g = np.load(DATA / fichier)
    Z, proj, volume = g["Z"].astype(np.float64), g["proj"].astype(np.float64), g["volume"]
    demi = (Z.shape[1] - 1) // 2
    assert demi == p["demi"] and float(g["seuil"]) == p["seuil"], prefixe
    comp, proj = orienter(g["composantes"], proj)
    # filtre de volume des archetypes, copie de figures_lib.filtre_volume(mini=3)
    plancher = max(np.percentile(volume, p["vol_q"]) if p["vol_q"] > 0 else 0, p["vol_min"])
    eligibles = np.where(volume >= plancher)[0]
    if len(eligibles) < 3:
        plancher, eligibles = 0.0, np.arange(len(volume))
    res = dict(seuil=p["seuil"], Z=Z, comp=comp, var=g["variance"], proj=proj,
               mot=g["mots"].astype(str), date=g["dates"].astype(np.int64),
               occ=volume.astype(np.int64), plancher=float(plancher), eligibles=eligibles)
    meta = dict(id=prefixe, famille="campagne par média", corpus=p["media_nom"],
                vocabulaire="top-10 000 du média", pas_jours=p["pas_jours"], demi=demi,
                source=fichier, attendu=p["fenetres"])
    return meta, [res]


def exporter(meta, seuils):
    """Un .npz par PCA : axe 0 = seuil, axe 1 = composante."""
    D = 2 * meta["demi"] + 1
    S = len(seuils)
    out = dict(
        composantes=np.zeros((S, N_COMP, D)), variance=np.zeros((S, N_COMP)),
        spectre=np.zeros((S, D)),
        tranches_moyenne=np.zeros((S, N_COMP, len(QUANTILES) - 1, D)),
        tranches_n=np.zeros((S, N_COMP, len(QUANTILES) - 1), int),
    )
    for cote in ("pos", "neg"):
        out[f"arch_{cote}_z"] = np.zeros((S, N_COMP, N_ARCH, D))
        out[f"arch_{cote}_mot"] = np.full((S, N_COMP, N_ARCH), "", dtype="<U32")
        out[f"arch_{cote}_date"] = np.zeros((S, N_COMP, N_ARCH), np.int64)
        out[f"arch_{cote}_occ"] = np.zeros((S, N_COMP, N_ARCH), np.int64)
        out[f"arch_{cote}_proj"] = np.zeros((S, N_COMP, N_ARCH))
    for a, r in enumerate(seuils):
        out["composantes"][a], out["variance"][a] = r["comp"][:N_COMP], r["var"][:N_COMP]
        out["spectre"][a] = r["var"]
        elig = r["eligibles"] if len(r["eligibles"]) >= N_ARCH else np.arange(len(r["Z"]))
        for k in range(N_COMP):
            p = r["proj"][:, k]
            bords = np.quantile(p, QUANTILES)
            for b in range(len(QUANTILES) - 1):
                sel = (p >= bords[b]) & (p <= bords[b + 1])
                out["tranches_moyenne"][a, k, b] = r["Z"][sel].mean(axis=0)
                out["tranches_n"][a, k, b] = sel.sum()
            ordre = elig[np.argsort(p[elig])]
            for cote, idx in (("pos", ordre[-N_ARCH:][::-1]), ("neg", ordre[:N_ARCH])):
                out[f"arch_{cote}_z"][a, k] = r["Z"][idx]
                out[f"arch_{cote}_mot"][a, k] = r["mot"][idx]
                out[f"arch_{cote}_date"][a, k] = r["date"][idx]
                out[f"arch_{cote}_occ"][a, k] = r["occ"][idx]
                out[f"arch_{cote}_proj"][a, k] = p[idx]
    np.savez(SORTIE / f"{meta['id']}.npz",
             id=meta["id"], famille=meta["famille"], corpus=meta["corpus"],
             vocabulaire=meta["vocabulaire"], pas_jours=meta["pas_jours"], demi=meta["demi"],
             unite=UNITES[meta["pas_jours"]], source=meta["source"],
             seuils=np.array([r["seuil"] for r in seuils]),
             n_fenetres=np.array([len(r["Z"]) for r in seuils]),
             offsets=np.arange(-meta["demi"], meta["demi"] + 1),
             tranches_quantiles=QUANTILES,
             arch_plancher=np.array([r["plancher"] for r in seuils]), **out)
    return dict(id=meta["id"], famille=meta["famille"], corpus=meta["corpus"],
                vocabulaire=meta["vocabulaire"], pas_jours=meta["pas_jours"],
                demi=meta["demi"], unite=UNITES[meta["pas_jours"]],
                seuils=";".join(f"{r['seuil']:g}" for r in seuils),
                n_fenetres=";".join(str(len(r["Z"])) for r in seuils),
                fenetres_annoncees=meta["attendu"] if meta["attendu"] else "",
                plancher_archetypes=";".join(f"{r['plancher']:g}" for r in seuils),
                source=meta["source"])


SORTIE.mkdir(exist_ok=True)
ids = sys.argv[1:] or [*UNIFIES, *CONFIGS]
lignes = []
for nom in ids:
    t0 = time.time()
    meta, seuils = charger_unifie(nom) if nom in UNIFIES else charger_cache(nom)
    lignes.append(exporter(meta, seuils))
    if meta["attendu"]:
        verifier(nom, len(seuils[0]["Z"]))
    r = seuils[-1]
    arch = ", ".join(f"{r['mot'][i]} {r['date'][i]}" for i in
                     r["eligibles"][np.argsort(r["proj"][r["eligibles"], 0])][-2:][::-1])
    print(f"{nom:14s} {lignes[-1]['n_fenetres']:>14s} fenetres, seuils {lignes[-1]['seuils']}, "
          f"variance {' '.join(f'{v:.1%}' for v in r['var'][:N_COMP])}, "
          f"comp1+ : {arch}  ({time.time() - t0:.1f} s)")

if not sys.argv[1:]:
    pd.DataFrame(lignes).to_csv(SORTIE / "catalogue.csv", index=False)
    print(f"{len(lignes)} PCA -> {SORTIE}")
