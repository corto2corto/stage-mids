# Fichiers du catalogue des PCA pour le site

Un fichier `.npz` par PCA de sauts déjà calculée, produit par
`campagne_pca/scripts/exporter_site.py`, plus `catalogue.csv` (une ligne par
PCA). Rien n'est recalculé ailleurs : le site (ngram-press, onglet « Tests
statistiques ») copie ces fichiers dans son dossier `pca/`, les sert en JSON et
dessine les trois figures des rapports de présentation.

Dix-huit PCA, deux familles :

- **corpus unifié** (`unifie1j`, `unifie3j`, `etendu1j`, `etendu3j`) : PCA
  rejouée aux seuils 4 et 6 depuis `data/pics_unifie/` et `data/pics_etendu/`,
  exactement comme `exporter_presentation.py` ;
- **campagne par média** (`configA` à `configH`, `hebdo*`, `optimale`,
  `lemonde`, `lemonde3j`, `lemonde7j`) : lues telles quelles dans les caches
  `data/cache_pca/`, un seul seuil ; paramètres dans `scripts/configs.py`.

Toutes les composantes sont orientées vers la queue lourde de leurs projections
(côté des archétypes), et au corpus unifié le seuil 4 est aligné sur le seuil 6.

## Champs d'un fichier

Axes : `S` = nombre de seuils (2 au corpus unifié, 1 en campagne), `4` =
composante, `D` = longueur d'une fenêtre (2·demi + 1).

| Champ | Forme | Contenu |
|---|---|---|
| `id`, `famille`, `corpus`, `vocabulaire`, `source`, `unite` | scalaires | identité de la PCA ; `unite` = « jours », « blocs de 3 jours » ou « semaines » |
| `pas_jours`, `demi` | scalaires | pas de la grille en jours, demi-fenêtre en pas |
| `seuils` | (S,) | seuils de surprise, dans l'ordre de l'axe 0 |
| `n_fenetres` | (S,) | fenêtres entrées dans la PCA à chaque seuil |
| `offsets` | (D,) | positions −demi … +demi, axe des abscisses |
| `composantes` | (S, 4, D) | les quatre premières composantes |
| `variance` | (S, 4) | leur part de variance |
| `spectre` | (S, D) | parts de variance de toutes les composantes |
| `tranches_quantiles` | (6,) | bornes 0, 0,10, 0,35, 0,65, 0,90, 1 |
| `tranches_moyenne` | (S, 4, 5, D) | profil moyen (z-score) des fenêtres de chaque tranche de projection |
| `tranches_n` | (S, 4, 5) | effectif de chaque tranche |
| `arch_plancher` | (S,) | occurrences minimales au pic pour être archétype (20 au corpus unifié, filtre de volume de `figures_lib` en campagne, 0 = pas de filtre) |
| `arch_pos_z`, `arch_neg_z` | (S, 4, 4, D) | les quatre fenêtres réelles (z-score) de projection la plus positive, resp. la plus négative, sur chaque composante |
| `arch_pos_mot`, `arch_pos_date`, `arch_pos_occ`, `arch_pos_proj` (idem `neg`) | (S, 4, 4) | mot, date AAAAMMJJ, occurrences au pic, projection de chaque archétype |

Les trois figures : `composantes` + `variance` (grille 2 × 2) ; `tranches_*`
(figure 4 d'Aubrun, Morel, Benzaquen, Bouchaud, PNAS 2025 — les trois tranches du
milieu se refondent en une seule en pondérant par `tranches_n`) ; `arch_*`
(grille 4 × 4, côté positif, ou 2 + 2 avec le côté négatif). Au corpus unifié
les archétypes sont pris parmi le vocabulaire parlant (`vocab600.txt`,
`vocab_parlant_etendu.txt`) ; en campagne parmi toutes les fenêtres au-dessus du
plancher de volume.
