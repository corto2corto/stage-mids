# Résultats de la PCA — sauts lexicaux du Monde (1944-2025)

Sorties de l'analyse en composantes principales du « modèle zéro »
(phase 3 du mémoire), rassemblées sous des noms cohérents pour être
vérifiées. Le document qui les commente est `presentation_sauts.qmd`,
dans ce dossier.

Trois grilles de temps sont livrées : le **journalier** (l'analyse de
référence), et deux timelines agrégées en **blocs de 3 jours** et de
**7 jours** de parution, qui rejouent la même chaîne à des échelles plus
lentes.

Emplacement complet : `/data/elias/stage-mids/resultats_PCA/` sur gallica.
Sur GitHub sont versionnés le README, le document, les scripts, les figures
et les CSV légers (`spectre*.csv`, `composantes*_zscore.csv`) ; les `.npz`
(14 Mo pièce) et les gros CSV (`pics_*.csv`, `fenetres_*.csv`) restent sur
le serveur — ils se régénèrent avec `preparer.py`.

## Vérifier

```bash
cd /data/elias/stage-mids
.venv/bin/python -m resultats_PCA.verifier
```

Rejoue toute la chaîne depuis les données sources avec les fonctions de
`rupture/pca.py` et compare aux fichiers livrés. N'écrit rien, ~1 min.
Contrôle les tailles, l'orthonormalité des composantes, la cohérence
variances/projections, le rejeu complet, le fait que les composantes
mesurent une forme et non un niveau, une reconstruction, et enfin les deux
grilles agrégées.

Ce qu'il faut voir : aux sections 2, 4 et 7, des écarts négligeables (< 1e-6)
et un rejeu à |cos| = 1,000000. La section 5 est un contrôle de méthode et
non un test d'égalité — les variantes `colonne` doivent y dépasser 0,9,
c'est leur défaut et elles sont livrées pour ça, tandis que `zscore` reste
sous 0,3 et que `minmax` se situe vers 0,5. La section 6 doit retrouver
48 / 52 / 62 / 89 %, les chiffres de la figure de reconstruction. La
section 7 doit montrer les composantes des grilles agrégées alignées sur
leurs homologues journalières : cosinus ≥ 0,80 sur les quatre premières.

## Les fichiers

### Les PCA

`pca_lemonde_<version>_<normalisation>.npz` — grille journalière.

**Version.** `v1` = brut, 123 310 fenêtres. `v2` = jours à corpus quasi
vide (moins de 5 000 mots publiés) interpolés, fenêtres à centre douteux
écartées, 121 805 fenêtres. **`v2` est l'analyse de référence.**

**Normalisation.** `zscore` = moyenne 0 et écart-type 1 le long de chaque
fenêtre, **retenue**. `minmax` = fenêtre ramenée sur [0, 1], contrôle.
`colonne` = standardisation colonne par colonne, c'est-à-dire l'option
intégrée des PCA clé en main : **témoin négatif**, livré exprès pour que
son défaut soit vérifiable (sa composante 1 est corrélée à 0,99 au niveau
moyen brut, elle mesure « ce mot est-il fréquent » et non la forme).

`pca_lemonde3j_<normalisation>.npz` et `pca_lemonde7j_<normalisation>.npz`
— grilles agrégées, 49 771 et 26 457 fenêtres. Pas de version ici : le
plus petit bloc pèse 17 785 mots (3 jours) et 55 684 mots (7 jours), le
nettoyage V2 n'a rien à corriger et tout seuil y donne le même résultat.

Douze fichiers, donc : 6 en journalier (`v1`/`v2` × trois normalisations),
3 par grille agrégée.

### Contenu d'un `.npz`

| Clé | Forme | Contenu |
|---|---|---|
| `composantes` | (31, 31) | une composante par ligne ; `composantes[0]` est le profil temporel de la composante 1, de −15 à +15 jours (ou blocs) de parution |
| `variance` | (31,) | part de variance expliquée, décroissante, de somme 1 |
| `projections` | (n, 31) | coordonnée de chaque fenêtre sur chaque composante |
| `garde` | (n,) | indices des fenêtres retenues dans `entree_fenetres_<média>.npz` |

Le signe d'une composante est arbitraire ; seul compte le contraste entre
projections positives et négatives.

### Les entrées : `entree_fenetres_lemonde[3j|7j].npz`

Copies de `data/fenetres_<média>.npz`. Lignes alignées sur les indices de
`garde` : `fenetres` (n × 31, fréquences pour 100 000 mots), `mot`, `date`
(AAAAMMJJ — le jour du milieu du bloc sur les grilles agrégées), `X_t`,
`N_t`, `f_t`, `p_t`, `surprise`, `n_absorbes`.

> ⚠️ `fenetres[garde]` renvoie les fenêtres **brutes**, avant
> interpolation. Pour retrouver la matrice exacte passée à la PCA en V2,
> appliquer d'abord `rupture.pca.nettoyer(...)` — c'est ce que fait
> `verifier.py`. Cela demande `data/vocab_series_lemonde.npz`, qui
> fournit le `N_t` de chaque jour. Sur les grilles agrégées la question ne
> se pose pas : les fenêtres livrées sont exactement celles de la PCA.

### Sans Python

Quatre familles de CSV, déclinées par grille (sans suffixe pour le
journalier, `_3j` et `_7j` pour les grilles agrégées) :

| Fichier | Contenu |
|---|---|
| `spectre.csv`, `spectre_3j.csv`, `spectre_7j.csv` | les 31 variances expliquées, une colonne par variante |
| `composantes_v2_zscore.csv`, `composantes_3j_zscore.csv`, `composantes_7j_zscore.csv` | les 31 composantes en lignes, colonnes `j-15` à `j+15` |
| `pics_journalier.csv`, `pics_3j.csv`, `pics_7j.csv` | un saut gardé par ligne après NMS : `mot`, `date`, `X_t`, `N_t`, `f_t`, `p_t`, `surprise`, `n_absorbes` |
| `fenetres_journalier.csv`, `fenetres_3j.csv`, `fenetres_7j.csv` | la matrice des fenêtres en clair : `mot`, `date`, `X_t`, `N_t`, `surprise`, puis les 31 fréquences `j-15` … `j+15` (pour 100 000 mots, brutes) |

Les deux premières familles sont légères et versionnées sur GitHub ; les
deux dernières pèsent de 1 à 24 Mo et restent sur gallica.

## Chiffres à retrouver

Variance expliquée en %, analyse de référence (journalier v2, z-score) :

```
rang    1     2     3     4     5     6     7     8     9    10  ...   30    31
     9.17  6.21  5.31  4.62  4.21  3.78  3.57  3.55  3.47  3.30  ...  2.25  0.00
```

Cumul : 20,7 % à K = 3, 33,3 % à K = 6, 62,1 % à K = 15. Sur les grilles
agrégées : 11,49 / 7,99 / 5,63 / 4,82 / 4,26 / 3,76 % en 3 jours et
11,86 / 9,14 / 6,42 / 5,29 / 4,68 / 3,84 % en hebdomadaire, soit 37,9 % et
41,2 % à K = 6.

Deux repères pour juger ces chiffres. La 31e valeur propre vaut
exactement 0 : une fenêtre z-scorée a une somme nulle, le nuage vit dans
30 dimensions. Et un nuage **sans aucune structure** donnerait 100/30 =
**3,33 %** par composante — seules les 9 premières passent au-dessus en
journalier, les 8 premières sur les grilles agrégées.

## Refaire les calculs

```bash
cd /data/elias/stage-mids
.venv/bin/python -m rupture.pca lemonde 5000    # journalier V2 (défaut)
.venv/bin/python -m rupture.pca lemonde 0       # journalier V1
.venv/bin/python -m rupture.pca lemonde3j 0     # blocs de 3 jours
.venv/bin/python -m rupture.pca lemonde7j 0     # blocs de 7 jours
```

Sorties dans `data/pca_<média>_<norme>[_v2].npz`. Les grilles agrégées
elles-mêmes se construisent avec `rupture/agreger.py`, puis la chaîne
habituelle (`pics_masse.py`, `nms.py`, `fenetres_masse.py`).

Ce dossier-ci n'est qu'une copie renommée de ces sorties, plus les figures
de `rupture/sorties/` et les CSV dérivés. Il se réassemble entièrement
avec :

```bash
.venv/bin/python -m resultats_PCA.preparer
```
