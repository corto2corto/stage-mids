# Résultats de la PCA — sauts lexicaux du Monde (1944-2025)

Sorties de l'analyse en composantes principales du « modèle zéro »
(phase 3 du mémoire), rassemblées sous des noms cohérents pour être
vérifiées. Le document qui les commente est `presentation_sauts.qmd`,
dans ce dossier.

Emplacement : `/data/elias/stage-mids/resultats_PCA/` sur gallica. Les
données (`.npz`, `.csv`, `figures/`) ne sont pas versionnées ; seuls ce
README, le document et `verifier.py` sont dans git.

## Vérifier

```bash
cd /data/elias/stage-mids
.venv/bin/python -m resultats_PCA.verifier
```

Rejoue toute la chaîne depuis les données sources avec les fonctions de
`rupture/pca.py` et compare aux fichiers livrés. N'écrit rien, ~30 s.
Contrôle les tailles, l'orthonormalité des composantes, la cohérence
variances/projections, le rejeu complet, le fait que les composantes
mesurent une forme et non un niveau, et une reconstruction.

Ce qu'il faut voir : aux sections 2 et 4, des écarts négligeables (< 1e-6)
et un rejeu à |cos| = 1,000000. La section 5 est un contrôle de méthode et
non un test d'égalité — les variantes `colonne` doivent y dépasser 0,9,
c'est leur défaut et elles sont livrées pour ça, tandis que `zscore` reste
sous 0,3 et que `minmax` se situe vers 0,5. La section 6 doit retrouver
48 / 52 / 62 / 89 %, les chiffres de la figure de reconstruction.

## Les fichiers

`pca_lemonde_<version>_<normalisation>.npz`

**Version.** `v1` = brut, 123 310 fenêtres. `v2` = jours à corpus quasi
vide (moins de 5 000 mots publiés) interpolés, fenêtres à centre douteux
écartées, 121 805 fenêtres. **`v2` est l'analyse de référence.**

**Normalisation.** `zscore` = moyenne 0 et écart-type 1 le long de chaque
fenêtre, **retenue**. `minmax` = fenêtre ramenée sur [0, 1], contrôle.
`colonne` = standardisation colonne par colonne, c'est-à-dire l'option
intégrée des PCA clé en main : **témoin négatif**, livré exprès pour que
son défaut soit vérifiable (sa composante 1 est corrélée à 0,99 au niveau
moyen brut, elle mesure « ce mot est-il fréquent » et non la forme).

Six fichiers, donc : `v1`/`v2` × `zscore`/`minmax`/`colonne`.

### Contenu d'un `.npz`

| Clé | Forme | Contenu |
|---|---|---|
| `composantes` | (31, 31) | une composante par ligne ; `composantes[0]` est le profil temporel de la composante 1, de −15 à +15 jours de parution |
| `variance` | (31,) | part de variance expliquée, décroissante, de somme 1 |
| `projections` | (n, 31) | coordonnée de chaque fenêtre sur chaque composante |
| `garde` | (n,) | indices des fenêtres retenues dans `entree_fenetres_lemonde.npz` |

Le signe d'une composante est arbitraire ; seul compte le contraste entre
projections positives et négatives.

### L'entrée : `entree_fenetres_lemonde.npz`

Copie de `data/fenetres_lemonde.npz`. 123 310 lignes alignées sur les
indices de `garde` : `fenetres` (123310 × 31, fréquences pour 100 000
mots), `mot`, `date` (AAAAMMJJ), `X_t`, `N_t`, `f_t`, `p_t`, `surprise`,
`n_absorbes`.

> ⚠️ `fenetres[garde]` renvoie les fenêtres **brutes**, avant
> interpolation. Pour retrouver la matrice exacte passée à la PCA en V2,
> appliquer d'abord `rupture.pca.nettoyer(...)` — c'est ce que fait
> `verifier.py`. Cela demande `data/vocab_series_lemonde.npz`, qui
> fournit le `N_t` de chaque jour.

### Sans Python

`spectre.csv` (les 31 variances des 6 variantes côte à côte) et
`composantes_v2_zscore.csv` (31 composantes en lignes, colonnes `j-15` à
`j+15`) s'ouvrent dans un tableur ou dans R.

## Chiffres à retrouver

Variance expliquée en %, analyse de référence :

```
rang    1     2     3     4     5     6     7     8     9    10  ...   30    31
     9.17  6.21  5.31  4.62  4.21  3.78  3.57  3.55  3.47  3.30  ...  2.25  0.00
```

Cumul : 20,7 % à K = 3, 33,3 % à K = 6, 62,1 % à K = 15.

Deux repères pour juger ces chiffres. La 31e valeur propre vaut
exactement 0 : une fenêtre z-scorée a une somme nulle, le nuage vit dans
30 dimensions. Et un nuage **sans aucune structure** donnerait 100/30 =
**3,33 %** par composante — seules les 9 premières passent au-dessus.

## Refaire les calculs

```bash
cd /data/elias/stage-mids
.venv/bin/python -m rupture.pca lemonde 5000   # V2 (défaut)
.venv/bin/python -m rupture.pca lemonde 0      # V1
```

Sorties dans `data/pca_lemonde_<norme>[_v2].npz`. Ce dossier-ci n'en est
qu'une copie renommée, plus les figures de `rupture/sorties/` et deux CSV
dérivés.
