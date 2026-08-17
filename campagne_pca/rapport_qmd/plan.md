# Campagne PCA 48 h — plan (31/07/2026 18h → 02/08/2026 18h, heure de Paris)

Explorer les hyperparamètres de la PCA des fenêtres de sauts et mesurer leur
effet sur la concentration du spectre. Validé par Corto le 31/07/2026 :
autorisation 48 h de lancer des jobs sur gallica (tmux dédié) et de
committer/pousser/puller sans re-demander. Le scrapping n'est pas touché.

## L'espace des configurations

| Axe | Valeurs | Coût |
|---|---|---|
| média | lemonde (fait), lefigaro, lesechos, mediapart (base à construire) | chaîne complète : heures |
| grille | journalier, blocs 3 j, blocs 7 j | pics_masse par grille : heures |
| demi-fenêtre `d` | 5, 10, 15 (réf.), 25, 50 | gratuit (NMS+fenêtres+PCA en mémoire) |
| seuil de surprise | 3 (recalcul pics), 4 (réf.), 5, 6 | ≥ 4 gratuit ; 3 = pics_masse à rejouer |
| filtre vocabulaire | tous (réf.), sans_verbes, noms, noms_propres | gratuit (catégories précalculées) |
| normalisation | z-score, fixé (les autres sont des témoins connus) | — |

Les nouveaux passages de `pics_masse` se font directement à seuil 3
(`pics_<media>_s3.csv`) : sur-ensemble des pics à 4, plus jamais à recalculer.

## Évaluer une configuration

`rupture/campagne.py` rejoue la fin de chaîne en mémoire et écrit une ligne
par config dans `data/campagne/resultats.csv` (serveur), plus le spectre et
les 8 premières composantes en CSV légers. Métriques (toutes loggées, pas de
score unique) :

- `K50` : composantes pour 50 % de variance ; `K50_frac` = K50/(D−1) pour
  comparer des fenêtres de tailles différentes (une fenêtre z-scorée de
  dimension D vit dans D−1 dimensions ; le spectre plat donne 100/(D−1) %
  par composante) ;
- `cum3, cum6, cum10` : variance cumulée à K fixé ; `gain6` = cum6/(6/(D−1)),
  le rapport au spectre plat (1 = aucune structure) ;
- `rang_eff` : rang effectif 1/Σλ² (participation ratio) et `rang_eff_frac` ;
- effectifs à chaque étape : pics ≥ seuil, après NMS, bords, centres écartés,
  fenêtres finales — une « victoire » obtenue en vidant l'échantillon se voit.

Garde-fous : normalisation z fixée ; les configs gagnantes seront inspectées
(profils des composantes) avant d'en conclure quoi que ce soit — une
concentration de variance peut être un artefact (cf. la norme colonne à
63,5 %).

## Stratégie (demande de Corto)

**Pas de montée par coordonnées d'emblée.** Premières ~24 h : exploration
large — balayer les axes gratuits sur toutes les grilles disponibles, lancer
les chaînes lourdes (Figaro, Échos, seuil 3, Mediapart) pour ouvrir de
nouveaux axes. Après ~24 h, quand `resultats.csv` est fourni : choisir une
direction (raffiner autour des zones intéressantes, croiser les axes
gagnants).

## Ordre de marche indicatif

1. **Salve 1 (soir 1)** : balayage gratuit sur lemonde (3 grilles × d × seuil
   ≥ 4 × filtres) ≈ 180 configs, séquentiel en tmux ; en parallèle, chaînes
   lourdes lefigaro et lesechos (scan vocab → masse → pics_masse s3 →
   agreger 3j/7j → pics_masse s3 sur les grilles) et pics_masse lemonde s3.
2. **Jour 2 matin** : récolte, balayage gratuit sur Figaro/Échos, catégories
   grammaticales étendues à leurs vocabulaires, construction base Mediapart.
3. **Jour 2 après-midi → fin** : axe seuil 3 partout, Mediapart, direction
   choisie d'après les résultats, combinaisons, raffinement.
4. **Dernières heures** : synthèse (classement commenté, figures, PDF),
   commit final.

## Règles serveur

- Tout job lourd : tmux `campagne_pca`/`campagne_media`, `nice -n 10`,
  `OMP_NUM_THREADS` borné. Jamais la session tmux du scrapping.
- Charge surveillée à chaque réveil (~20-30 min) : si load > 16 (20 cœurs),
  pause de la file ; disque `/data` et RAM vérifiés.
- Un seul processus écrit `resultats.csv` (le balayage est séquentiel).
- Sorties campagne dans `data/campagne/` (serveur), jamais dans les fichiers
  officiels de `data/` ; `pics_masse` seuil 3 écrit `pics_*_s3.csv`, ne
  touche pas aux `pics_*.csv` livrés.
- Déploiement du code par git (push Mac → pull gallica), jamais de scp code.

## Fichiers

- `campagne_pca/rapport_qmd/suivi.md` — journal horodaté + prompt de reprise (source de
  vérité pour reprendre la campagne dans une nouvelle session).
- `campagne_pca/data/resultats.csv` — copie Mac (scp depuis le serveur) du
  `data/campagne/resultats.csv`, committée régulièrement.
- `campagne_pca/data/vocab_categories.csv` — mot → catégorie grammaticale
  (classification spaCy + Lexique sur le Mac), committé, lu par
  `rupture/campagne.py` côté serveur.
- `rupture/campagne.py` — le runner paramétré.
