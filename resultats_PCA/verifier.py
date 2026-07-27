# Verification independante des resultats de PCA livres dans resultats_PCA/.
# Rejoue toute la chaine depuis fenetres_lemonde.npz avec les fonctions de
# rupture/pca.py, puis compare aux fichiers livres. Lecture seule.
# Usage : cd /data/elias/stage-mids && .venv/bin/python -m resultats_PCA.verifier
import os

import numpy as np

from rupture.pca import DEMI, nettoyer, normaliser, pca

DONNEES = os.environ.get("VOCAB_DIR", "/data/elias/stage-mids/data")
ICI = os.path.dirname(os.path.abspath(__file__))
SEUIL = 5000
VARIANTES = {"v1_zscore": ("z", 0), "v1_minmax": ("01", 0), "v1_colonne": ("col", 0),
             "v2_zscore": ("z", SEUIL), "v2_minmax": ("01", SEUIL), "v2_colonne": ("col", SEUIL)}

print("=" * 72)
print("1. FICHIERS LIVRES")
print("=" * 72)
livre = {}
for nom in VARIANTES:
    livre[nom] = np.load(f"{ICI}/pca_lemonde_{nom}.npz")
    n = livre[nom]["projections"].shape[0]
    print(f"  {nom:<12} {n:>7d} fenetres x 31 jours")

print()
print("=" * 72)
print("2. COHERENCE INTERNE (chaque fichier, isolement)")
print("=" * 72)
for nom, d in livre.items():
    V, var, P = d["composantes"], d["variance"], d["projections"].astype(np.float64)
    ecart_ortho = np.abs(V @ V.T - np.eye(31)).max()
    somme_var = var.sum()
    # la variance expliquee doit etre proportionnelle a la variance des projections
    var_proj = P.var(axis=0)
    ecart_var = np.abs(var_proj / var_proj.sum() - var).max()
    print(f"  {nom:<12} base orthonormee (ecart max) {ecart_ortho:.2e} | "
          f"somme des variances {somme_var:.10f} | "
          f"variance vs projections (ecart max) {ecart_var:.2e}")

print()
print("=" * 72)
print("3. SPECTRE : variance expliquee par composante (%)")
print("=" * 72)
print("  rang  " + "".join(f"{nom:>13}" for nom in VARIANTES))
for k in list(range(8)) + [29, 30]:
    ligne = "".join(f"{livre[nom]['variance'][k] * 100:>13.3f}" for nom in VARIANTES)
    print(f"  {k + 1:>4}  " + ligne)
print("  (la 31e valeur propre du z-score vaut exactement 0 : une fenetre")
print("   z-scoree a une somme nulle, le nuage vit dans 30 dimensions)")

print()
print("=" * 72)
print("4. REJEU COMPLET DEPUIS LES DONNEES SOURCES")
print("=" * 72)
source = np.load(f"{DONNEES}/fenetres_lemonde.npz")
F0 = source["fenetres"]
print(f"  entree : {F0.shape[0]} fenetres x {F0.shape[1]} jours "
      f"({DONNEES}/fenetres_lemonde.npz)")

series = np.load(f"{DONNEES}/vocab_series_lemonde.npz")
position = {int(dt): i for i, dt in enumerate(series["dates"])}
pos = np.array([position[int(dt)] for dt in source["date"]])
N_fen = series["N"][pos[:, None] + np.arange(-DEMI, DEMI + 1)]

for etiquette, seuil in (("v1", 0), ("v2", SEUIL)):
    if seuil:
        F, idx, n_jours, n_fen = nettoyer(F0, N_fen, seuil)
        print(f"  nettoyage {etiquette} : {len(idx)} fenetres gardees, "
              f"{n_jours} jours interpoles dans {n_fen} fenetres")
    else:
        F, idx = F0, np.arange(len(F0))
    for norme, suffixe in (("z", "zscore"), ("01", "minmax"), ("col", "colonne")):
        Fn, garde = normaliser(F, norme)
        V, var, P = pca(Fn)
        ref = livre[f"{etiquette}_{suffixe}"]
        # une composante est definie au signe pres : on compare les |cosinus|
        cos = np.abs((V * ref["composantes"]).sum(axis=1))
        print(f"    {etiquette}_{suffixe:<8} |cos| min sur les 30 composantes "
              f"{cos[:30].min():.6f} | ecart max sur la variance "
              f"{np.abs(var - ref['variance']).max():.2e} | "
              f"memes fenetres {np.array_equal(idx[garde], ref['garde'])}")

print()
print("=" * 72)
print("5. CONTROLE DE METHODE : les composantes mesurent-elles une FORME")
print("   ou seulement un NIVEAU ?")
print("=" * 72)
print("  Correlation entre la projection sur la composante 1 et le niveau")
print("  moyen brut de la fenetre. Proche de 1 = la composante ne mesure que")
print("  << ce mot est-il frequent >>, pas la forme du saut.")
niveau_tout = F0.astype(np.float64).mean(axis=1)
for nom, d in livre.items():
    c1 = d["projections"][:, 0].astype(np.float64)
    r = np.corrcoef(c1, niveau_tout[d["garde"]])[0, 1]
    verdict = "TEMOIN : artefact de niveau" if abs(r) > 0.9 else "OK : mesure une forme"
    print(f"  {nom:<12} r = {r:+.3f}   {verdict}")

print()
print("=" * 72)
print("6. RECONSTRUCTION D'UNE FENETRE CONNUE")
print("=" * 72)
d = livre["v2_zscore"]
F2, idx2, _, _ = nettoyer(F0, N_fen, SEUIL)
Z, garde2 = normaliser(F2, "z")
Zc = Z - Z.mean(axis=0)
mots, dates = source["mot"][d["garde"]], source["date"][d["garde"]]
cible = np.where((mots == "jaunes") & (dates == 20181208))[0]
if len(cible):
    i = cible[0]
    print(f"  fenetre << jaunes >> du 08/12/2018 (ligne {i})")
    print(f"  projections c1..c4 : {np.round(d['projections'][i, :4], 3)}")
    for K in (1, 3, 6, 15):
        approx = d["composantes"][:K].T @ d["projections"][i, :K]
        part = 1 - ((Zc[i] - approx) ** 2).sum() / (Zc[i] ** 2).sum()
        print(f"    avec {K:>2} composantes : {part * 100:>5.1f} % de la forme restituee")
else:
    print("  fenetre introuvable (mot ou date absents du jeu V2)")

print()
print("Fin. Tous les ecarts ci-dessus doivent etre negligeables (< 1e-6),")
print("sauf la ligne 5 ou seules les variantes << colonne >> doivent depasser 0,9.")
