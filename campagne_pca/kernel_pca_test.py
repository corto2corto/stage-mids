# Test rapide : la kernel PCA (RBF) concentre-t-elle mieux la variance que la
# PCA lineaire sur les fenetres de sauts ? Config de reference d15/s4/tous,
# lemonde et lesechos. Pas de figures composantes/archetypes/reconstruction :
# la kernel PCA n'a pas de vecteurs dans l'espace des D jours, seulement des
# projections -> on compare juste les spectres de variance expliquee.
# La kernel PCA calcule une matrice de Gram N x N (N = nb de fenetres) :
# a 130k fenetres ca sature la RAM (~135 Go en float64) -> sous-echantillonnage.
# Usage : .venv/bin/python -m campagne_pca.kernel_pca_test
import os

import numpy as np
import pandas as pd
from sklearn.decomposition import KernelPCA

from rupture.nms import nms
from rupture.pca import normaliser, pca

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.environ.get("VOCAB_DIR", os.path.join(ICI, "data_local"))
DEMI, SEUIL = 15, 4
N_ECH = 8000
GRAINE = 0

MEDIAS = {
    "lemonde": "pics_lemonde.csv",
    "lesechos": "pics_lesechos_s3.csv",
}


def charger_fenetres(media, fichier_pics):
    g = np.load(f"{DONNEES}/vocab_series_{media}.npz")
    X, grille_dates, grille_N = g["X"], g["dates"], g["N"]
    position = {int(dt): i for i, dt in enumerate(grille_dates)}
    colonne = {m: j for j, m in enumerate(g["mots"])}

    p = pd.read_csv(f"{DONNEES}/{fichier_pics}")
    p = p[p["surprise"] >= SEUIL].assign(pos=lambda x: x["date"].map(position))
    gardes = [gr.index.to_numpy()[nms(gr["pos"].to_numpy(), gr["surprise"].to_numpy(),
                                     2 * DEMI + 1)[0]]
              for _, gr in p.groupby("mot", sort=False)]
    p = p.loc[np.concatenate(gardes)]
    pos, col = p["pos"].to_numpy(), p["mot"].map(colonne).to_numpy(int)
    complet = (pos - DEMI >= 0) & (pos + DEMI < len(grille_dates))
    pos, col = pos[complet], col[complet]
    lignes = pos[:, None] + np.arange(-DEMI, DEMI + 1)
    brut = X[lignes, col[:, None]]
    F = (1e5 * brut / grille_N[lignes]).astype(np.float64)
    Z, _ = normaliser(F, "z")
    return Z


rng = np.random.default_rng(GRAINE)
for media, fichier_pics in MEDIAS.items():
    Z = charger_fenetres(media, fichier_pics)
    D = Z.shape[1]
    rang = D - 1
    if len(Z) > N_ECH:
        Z_ech = Z[rng.choice(len(Z), N_ECH, replace=False)]
    else:
        Z_ech = Z

    _, variance_lin, _ = pca(Z_ech)

    kpca = KernelPCA(n_components=rang, kernel="rbf", gamma=1.0 / D)
    kpca.fit_transform(Z_ech)
    variance_kernel = kpca.eigenvalues_ / kpca.eigenvalues_.sum()

    cum_lin = np.cumsum(variance_lin[:6])[-1] * 100
    cum_kernel = np.cumsum(variance_kernel[:6])[-1] * 100
    print(f"{media} : {len(Z)} fenetres au total, {len(Z_ech)} echantillonnees x {D} blocs")
    print(f"  lineaire (6 premieres, %) : {np.round(variance_lin[:6] * 100, 1)} "
          f"| cum6 = {cum_lin:.1f} %")
    print(f"  kernel RBF (6 premieres, %) : {np.round(variance_kernel[:6] * 100, 1)} "
          f"| cum6 = {cum_kernel:.1f} %")
