# Campagne PCA 48 h — suivi

## Prompt de reprise (coller tel quel dans une nouvelle session Claude)

> Reprends la campagne PCA 48 h. Lis `campagne_pca/rapport_qmd/plan.md` puis ce fichier
> (`campagne_pca/rapport_qmd/suivi.md`) en entier, vérifie l'état des tmux sur gallica
> (`ssh gallica 'tmux ls'`), récolte les résultats
> (`scp gallica:/data/elias/stage-mids/data/campagne/resultats.csv campagne_pca/`),
> consigne ici, puis continue le programme du plan en réarmant la boucle de
> réveils (~20-30 min). Autorisation 48 h donnée le 31/07/2026 : jobs serveur
> en tmux dédié + git en autonomie, fin le 02/08 ~18h (Paris). Surveiller la
> charge serveur (pause de la file si load > 16).

## CAMPAGNE CLOSE — bilan final (02/08/2026 ~18h)

**Livrable principal : `campagne_pca/rapport_pdf/rapport.pdf`** (4 pages, source qmd,
figures). Journal complet ci-dessous, tout est committé et poussé.

**Chiffres.** 7 salves + compléments, ~4 000 configurations évaluées
(1 753 au balayage principal `resultats.csv`, 2 304 au double témoin
`resultats_rotation.csv`), 4 médias × 3 grilles × fenêtres ±5→±70 ×
seuils 3-6 × 4 filtres × 2 vocabulaires × brut/log. Aucun incident serveur
(un crash de script réparé et rejoué ; scrapping jamais touché).

**Résultats clés** (détail au rapport et aux réveils 4-7) :
1. La « meilleure PCA » dépend de la question : **formes d'événement**
   (brut, journalier, ±25-50, s6 — Mediapart 1,62 > Échos 1,44 > Monde
   1,33 > Figaro 1,28 en part ancrée) vs **texture/régimes** (log, agrégé,
   grandes fenêtres — hiérarchie des médias inverse ; piste pour les
   breakpoints de rachat).
2. La métrique naïve (cum6) piège trois fois : dimension, marges/petite
   matrice, composition — d'où gain6, exces6 (nul colonnes), n apparié,
   alignement6 (nul rotation). Dispersion inter-graines 0,0045.
3. Vocabulaire 40k : dilue (−0,08). Filtres grammaticaux : non décisifs.
   Log : +0,76 d'exces6 au maximum, mais noie l'ancrage sur l'événement.
4. Boilerplate : métrique robuste (2,55 → 2,48 sans les mots suspects).
   **Correction du 14/08/2026** — la piste « boilerplate Mediapart » des
   réveils ci-dessous est fausse (mots ordinaires à faible effectif, cf.
   `rapport.qmd`) ; le vrai boilerplate est celui du Figaro, identifié
   depuis : crédit `Source : AFP` des brèves (11/2007-05/2008) et encart
   publicitaire `SERVICE >> bwin` (09-12/2011).

**Acquis d'infra réutilisables** : base ngram Mediapart
(`scripts/ngram_mediapart.py`), pics s ≥ 3 pour les 4 médias × 3 grilles
(`pics_*_s3.csv`), chaînes complètes Figaro/Échos/Mediapart, variante 40k
(`lemondev40k*`), runner `rupture/campagne.py` (--log, --sous_ech,
--graine, --nul_rotation), catégories grammaticales de 39,5k mots
(`vocab_categories.csv`), `masse.py`/`pics_masse.py` paramétrés sans
toucher aux sorties officielles.

**Questions laissées à Corto** :
- Ménage : `data/campagne/` sur gallica ne fait que 41 Mo (2,5k petits
  CSV) — laissé tel quel, dis-moi si tu veux que je supprime.
  `campagne_pca/data/data_local/` sur le Mac (~700 Mo de npz) peut être vidé
  quand tu veux.
- Suites possibles (notées au rapport) : nettoyage anti-boilerplate par
  média, kernel PCA si le linéaire bute, fenêtres par mot (Bouchot),
  breakpoints sous la lentille texture.

## Journal

### 31/07 18h00 — Validation et mise en place

- Corto valide le dispositif : autorisation serveur+git 48 h, spaCy sur le
  Mac, base Mediapart à construire (53 095 articles en base, pas de base
  ngram), exploration large d'abord (pas de montée par coordonnées avant
  ~24 h de résultats).
- État serveur au départ : 20 cœurs, load ~10 (scrapping + autres users),
  3,1 To libres sur /data, 23 Go RAM dispo.
- Chaîne relue (`masse` → `pics_masse` → `nms` → `fenetres_masse` → `pca`) :
  tout est rejouable par média/grille via `VOCAB_DIR` ; `nms()`,
  `nettoyer()`, `normaliser()`, `pca()` importables → runner en mémoire.
- Pics existants : `pics_lemonde{,3j,7j}.csv` (seuil 4). Les p sous 10⁻⁴
  n'étant pas conservées, l'axe seuil 3 demande un rejeu `pics_masse`
  (fait à s3 pour ne plus jamais recalculer).

### 31/07 18h30 — Infra prête, validée en local

- `rupture/campagne.py` écrit et **validé contre la livraison** : config de
  référence (lemonde d15 s4 tous n5000) → 164 254 pics → 123 465 NMS →
  121 805 fenêtres, cum6 = 33,3 %, v1..v6 identiques ; lemonde3j (n0) →
  49 771 fenêtres, 37,9 % — chiffres exacts du README. ~2 s par config.
- `pics_masse.py` : 4e argument surprise (défaut 4 = historique) ; s ≠ 4 →
  sorties `pics_<media>_s<s>.csv`, rien d'officiel touché. Appliqué V2.2 du
  to_do au passage (surprise 4 décimales, p_t en %.6e) — vaut pour tous les
  nouveaux passages.
- `exploration/scan_vocab.py` : scan vocab généralisé (média en argument).
- Classification grammaticale (`exploration/classer_vocab.py`, sur le Mac —
  spaCy + pylexique + setuptools<81 installés au venv local via uv) :
  Lexique383 d'abord (verbe si analyses toutes verbales, NOM prime sur ADJ),
  élisions décomposées (l'économie → économie), homographes rares tranchés
  par fréquence lexique < 0,5/million + spaCy PROPN sur forme capitalisée
  (hollande, allemagne, gaulle → nom_propre), cas fréquents arbitrés à la
  main (paris, cannes, vichy, élysée, prénoms jean/jacques/claude…).
  Top-10k lemonde : 5 793 noms, 2 040 verbes, 1 314 adj, 517 noms propres,
  336 autres → `campagne_pca/data/vocab_categories.csv` (committé, lu par le
  serveur).
- **Fait notable** : le top-10k par jours actifs (coupe 7 121 j) exclut les
  mots récents — macron, covid, trump n'y sont pas. Le filtre noms_propres
  ne contient que des noms installés dans la durée. La variante ≥ 1 000
  jours actifs (39 316 mots, déjà notée au to_do) lèverait ça — candidate
  pour la nuit 2.
- **Teaser** (validation locale) : filtre noms_propres seul → cum6 41,5 %
  (gain6 2,08) contre 33,3 % (1,66) en référence — mais 9 647 fenêtres
  contre 121 805. À confirmer/croiser en salve 1.
- Données lemonde rapatriées en local (`campagne_pca/data/data_local/`, hors git)
  pour valider et comme labo de secours si ssh tombe.

### 31/07 18h45 — Réveil 1 : salve 1 déjà finie, tout relancé avec témoin nul

- **Salve 1 finie en < 20 min** (180 configs, ~3 s pièce) et chaînes Figaro
  (6 764 jours, 2004→2024, 42 047 pics s3) et Échos (10 381 jours,
  1991→2024, 33 762 pics s3) **entièrement terminées** — pics_masse tourne
  en ~1-2 min sur ces grilles courtes, l'estimation « heures » venait du
  Monde et de ses 26 917 jours.
- **Enseignements salve 1** (lemonde seul, moyennes par axe) : gain6 monte
  avec la demi-fenêtre (1,28 à d5 → 4,12 à d50), avec le seuil (2,20 s4 →
  2,71 s6), avec l'agrégation (2,21 journalier → 2,64 hebdo) et avec le
  filtre noms_propres (2,86 vs 2,31 tous). Les axes se cumulent : top =
  3j/7j × d50 × s6 × noms_propres, gain6 ≈ 6. MAIS n_fenetres y tombe à
  ~900-2 700.
- **Garde-fou ajouté — témoin nul** (`exces6`) : colonnes mélangées
  indépendamment (mêmes variances marginales par jour, corrélations
  temporelles détruites). Verdict : la référence (gain6 1,66) garde
  exces6 1,17 ; l'extrême d50×s6×noms_propres (gain6 5,23) retombe à
  exces6 1,29. Une grande part du gain6 brut vient donc des variances
  marginales (le jour du pic varie plus que les bords) et de la petite
  taille d'échantillon — l'ordre des configs semble néanmoins conservé.
  D'où la salve 2 : tout rejoué avec le témoin (schéma unique, l'ancien
  resultats.csv archivé en resultats_salve1_sans_nul.csv sur gallica).
- Vocabulaires Figaro/Échos classés (2 861 nouveaux mots, 567 noms propres
  — leurs corpus récents font entrer les noms d'actualité) ; 9 homographes
  arbitrés à la main (blair, auvergne, rochelle, universal, bull, coca,
  charlotte, virginie, véronique).
- **Mediapart lancé** : `scripts/ngram_mediapart.py` (CSV du pipeline,
  478 Mo, 53 095 articles 2008→2026) puis chaîne complète en tmux
  `campagne_mediapart`.
- Serveur : pic de charge à 15,9 au lancement simultané, redescendu à ~14 ;
  tous mes jobs en nice 10, priorité cédée aux autres utilisateurs.

### 31/07 19h15 — Réveil 2 : salve 2 récoltée, Mediapart fini, leçon de méthode

- **Tout est fini en avance** : salve 2 (660 configs), pics s3 lemonde
  (2,4 min pour 111 624 pics — pics_masse est rapide partout, l'espace de
  configs coûte bien moins que prévu), chaîne Mediapart complète (6 630
  jours 2008→2026, N médian 9 092, 19 268 pics s3). nettoie mediapart = 2000
  (5000 toucherait 25 % des jours de ce petit corpus).
- **Salve 2 (avec témoin nul) — première lecture** : en exces6 moyen par
  axe, seuil et filtre semblent plats (~1,25 partout), seuls résistent la
  demi-fenêtre (1,19→1,33), l'agrégation (1,20→1,31) et le média (Figaro
  1,30 > Monde 1,24 > Échos 1,21). Nouveau top brut : lefigaro7j × d50 ×
  s3-4 × vocab large, exces6 1,64 à n confortable (8-15k fenêtres).
- **MAIS test à n apparié (local, lemonde d15)** : la référence
  sous-échantillonnée à n=9 647 donne exces6 1,164 ± 0,003 quand
  noms_propres y est à **1,231** ; à n=31 232 elle donne 1,169 quand s6 est
  à **1,204**. Les effets seuil et noms_propres sont donc **réels** — les
  moyennes plates par axe étaient un artefact de composition (les configs à
  petit n, où exces6 s'écrase, tirent les moyennes vers le bas). Corollaire
  utile : exces6 de la référence est quasi stable de n=122k à n=10k (à
  D=31) — les comparaisons appariées sont fiables dans cette gamme.
- **Conséquence** : salve 4 = comparaisons systématiques à n apparié
  (option --sous_ech à ajouter au runner, tirage seedé, taille cible dans le
  tag), pour requalifier proprement chaque axe. En attendant, ne pas
  conclure des moyennes brutes de resultats.csv.
- Salve 3 lancée (mediapart 240, s3 lemonde 60, ±35/±70 partout 96) +
  chaîne 40k (masse.py paramétré en nom de sortie, X dense 4,2 Go, sorties
  lemondev40k*). Vocab mediapart classé (+866 mots, rien à arbitrer).

## Scripts .sh de scripts/ — commandes pour reproduire (fichiers supprimés)

Patron commun : `cd /data/elias/stage-mids`, `VOCAB_DIR=/data/elias/stage-mids/data`,
threads BLAS/OMP bridés à 8 (sur 20, pour laisser tourner le scrapping),
lancement en tmux dédié, log dans `data/logs/<nom>.log`.

- **Nouveau média** (`chaine_media.sh <media>`, `set -e`, threads=2, nice 10) :
  ```
  python -m exploration.scan_vocab <media>
  python -m rupture.masse <media>
  python -m rupture.pics_masse <media> bnb 2 3
  python -m rupture.agreger <media> 3
  python -m rupture.agreger <media> 7
  python -m rupture.pics_masse <media>3j bnb 2 3
  python -m rupture.pics_masse <media>7j bnb 2 3
  ```

- **Kernel PCA hebdo** (`kernel_hebdo.sh`, séquentiel, petit → gros corpus) :
  ```
  python -m campagne_pca.scripts.kernel_hebdo mediapart7j --pics _s3
  python -m campagne_pca.scripts.kernel_hebdo lesechos7j  --pics _s3
  python -m campagne_pca.scripts.kernel_hebdo lefigaro7j  --pics _s3
  python -m campagne_pca.scripts.kernel_hebdo lemonde7j
  ```

- **Grille de gamma hebdo** (`kernel_grille.sh`, spectre entier + 50 vecteurs
  propres, 3h à 20h selon média) :
  ```
  python -m campagne_pca.scripts.kernel_grille mediapart7j --pics _s3
  python -m campagne_pca.scripts.kernel_grille lesechos7j  --pics _s3
  python -m campagne_pca.scripts.kernel_grille lefigaro7j  --pics _s3
  ```

- **Grille de gamma à 3j** (`kernel_grille_3j.sh`, même grille, `--demi 10 --seuil 5`
  acté le 08/08 — seuil=5 donne des effectifs comparables à la config page 1) :
  ```
  python -m campagne_pca.scripts.kernel_grille mediapart3j --demi 10 --seuil 5 --pics _s3
  python -m campagne_pca.scripts.kernel_grille lesechos3j  --demi 10 --seuil 5 --pics _s3
  python -m campagne_pca.scripts.kernel_grille lefigaro3j  --demi 10 --seuil 5 --pics _s3
  ```

- **Le Monde, grille journalière** (`kernel_lemonde_journalier.sh`, `--demi 15
  --seuil 6` acté le 08/08 — plus gros calibrage qui tienne en RAM, Gram 8,1 Go,
  31 882 fenêtres ; un seul gamma d'abord pour calibrer le temps) :
  ```
  python -m campagne_pca.scripts.kernel_grille lemonde --demi 15 --seuil 6 --mults 1
  ```

### 31/07 19h45 — Réveil 3 : crash réparé, salves 3b+4 lancées

- **Salve 3 : crash à la config 300/396** — mediapart7j × d50 × s6 ×
  noms_propres n'a que 84 fenêtres pour D=101 : l'écriture du spectre
  supposait n ≥ D. Corrigé (le runner écrit min(n, D) valeurs, métriques
  blindées, v1..v6 rembourrées à 0 si n < 6). Sections s3-lemonde (60) et
  mediapart (240) intactes ; la section ±35/±70 n'avait pas commencé.
  Rejouée en salve 3b (96 configs + rejeu de la config crashée — sa ligne
  est en double dans resultats.csv, **dédupliquer par tag en gardant la
  dernière** à l'analyse).
- **Option --sous_ech ajoutée** (tirage seedé, suffixe _e<N> dans le tag) et
  validée en local : lemonde d15 à n=5 000 → exces6 1,16 (stable vs 1,17 à
  n complet) ; le cas n<D passe (80 fenêtres pour D=101 sans crash).
- **Salve 4 à n apparié lancée** à la suite de 3b dans le même tmux (un
  écrivain à la fois) : 384 configs, tout à --sous_ech 5000.
- Chaîne 40k : masse + pics journalier finis, grilles 3j/7j en cours ;
  vocab (39 316 mots) rapatrié, classification en tâche de fond sur le Mac.
- La config crashée rejouée confirme : 84 fenêtres → exces6 1,06, les
  configs minuscules ne portent aucun signal honnête.

### 01/08 07h35 — Buffer : archétypes Les Échos (sains)

- lesechos d50 s6 (10 520 fenêtres) : multiplicité max 8 dans les top-200
  des composantes 1-3 (« grèce ») — pas de boilerplate, contrairement à
  Mediapart. Archétypes = vrais événements : crise grecque (05/2012),
  Fukushima (« l'archipel » 03/2011), Covid (« mesures » 03/2020), séisme
  d'Albanie (11/2019). La config recommandée « formes d'événement » est
  saine sur ce corpus ; Mediapart reste à nettoyer avant interprétation.

### 01/08 01h45 — Nuit : archétypes Mediapart et contrôle boilerplate

- Archétypes de mediapart_d50_s6 (la config de tête) : les extrêmes des
  composantes 1-3 sont pollués par des mots de boilerplate/artefacts du
  corpus Mediapart (« articles » 51 fois sur 200, « phrases » 27,
  « développés », « chèque »… — textes d'interface et refontes du site, qui
  produisent des marches ancrées sur des dates).
- **Contrôle** : en excluant les 6 mots à multiplicité ≥ 10, alignement6
  passe de 2,552 à **2,481** (n=5000) — la métrique globale est robuste, le
  boilerplate ne fabrique pas le résultat. Caveat pour la synthèse :
  nettoyer ces mots avant toute interprétation fine des composantes
  Mediapart ; plus largement, un filtre anti-boilerplate par média serait
  un chantier utile (hérite du problème « stop words à corriger »).
- Données mediapart/lesechos rapatriées en data_local (archétypes en local).

### 31/07 23h35 — Réveil 7 : salve 6 récoltée, alignement6 renverse la lecture

- resultats_rotation.csv : 2 304 configs (1 302 à n=5000 exact), dispersion
  inter-graines médiane 0,0045 → tout est significatif.
- **alignement6 (part ancrée sur l'événement), brut, n apparié :**
  - médias : mediapart 1,618 > lesechos 1,386 > lemonde 1,315 > lefigaro
    1,246 — **ordre inverse d'exces6**. Figaro = texture lente abondante peu
    ancrée ; Mediapart = peu de texture mais presque tout est ancré.
  - grille : 1j 1,535 > 3j 1,264 > 7j 1,173 (l'agrégation floute
    l'alignement) — inverse d'exces6 aussi.
  - demi : 1,21 (±10) → 1,585 (±50) ; seuil : s4 1,283 → s6 1,525 — les
    grands pics ont de vraies formes, visibles loin autour (cohérent avec
    les marches de régime vues au réveil 5).
  - filtre : quasi plat (1,363-1,392).
  - **log : alignement6 ≈ 0,94-1,09 partout** — le log noie la part ancrée
    (parfois < 1 : le nul décalé se concentre plus que l'observé). Brut
    pour les formes d'événement, log pour la texture.
  - top : mediapart_d50_s6 → **2,58** ; lesechos_d50_s6 → 2,07.
- **Lecture d'ensemble pour la synthèse** : deux lentilles complémentaires.
  (1) Formes d'événement (objectif classification des sauts) : journalier,
  brut, ±25-50, s6 ; Mediapart/Échos en tête. (2) Texture/régimes (bonne
  entrée pour les breakpoints de rachat) : log, grilles agrégées, Figaro en
  tête. La « meilleure PCA » dépend de la question — c'est LE message.

### 31/07 21h30 — Réveil 6 : 40k dilue, le log est le levier, double nul lancé

- **Salve 5 récoltée** (1 753 configs cumulées). Deux verdicts :
  - **40k vs 10k à n apparié : −0,084 ± 0,026 d'exces6** (76 paires, toutes
    grilles) — la queue du vocabulaire (mots à 1 000-7 000 jours actifs)
    dilue la structure. Réponse à la question du to_do : ne pas étendre le
    vocabulaire pour la PCA.
  - **Log : +0,13 à +0,76 d'exces6** (24 jauges, monotone en fenêtre,
    maximal sur Figaro ±50 : 1,61 → 2,37). La note d'appel de Benoît était
    la bonne piste.
- **MAIS nul par décalage circulaire (implémenté, testé)** : lemonde ±15
  brut → alignement6 1,27 (structure ancrée sur le pic) ; lemonde ±50 log →
  alignement6 1,01 (le spectre est reproduit par les fenêtres décalées :
  autocorrélation générique, pas de forme d'événement). Décomposition
  propre : marges (nul colonne) + texture autocorrélée (rotation vs
  colonne) + structure ancrée (observé vs rotation).
- Salve 6 lancée pour la nuit : grille appariée × {brut, log} × graines
  1-3, double nul partout (~2 300 configs).

### 31/07 20h55 — Réveil 5 : inspection des composantes de tête

- `campagne_pca/scripts/inspection_composantes.py` (indicateurs : croisements de
  zéro, part d'énergie au centre |j| ≤ D/8, corrélation à une rampe) +
  figures dans `campagne_pca/rapport_qmd/figures/`.
- **lefigaro7j × d50 (le top)** : composantes 1-3 = pic sec central PLUS
  plateaux avant/après — des **marches de régime ancrées sur l'événement**
  (le mot change durablement de niveau à son pic), pas de la dérive
  générique pure. L'indicateur « corr rampe » (0,55-0,72) lisait la marche
  comme une rampe ; la figure tranche. Structure à l'échelle de l'année,
  ancrée sur j=0 → le nul par décalage circulaire pourra le confirmer
  (une marche ancrée ne survit pas au décalage).
- **lemonde ±15** : indicateurs retrouvent les profils livrés (87 % centre
  pour le pic isolé, marche de niveau, bascule) — validation.
- **mediapart ±15** : composantes 1-3 à 90-100 % d'énergie au centre — des
  pics « secs » sans montée ni retombée ; cohérent avec exces6 1,07. Fait
  éditorial en soi (événements sans traîne chez Mediapart).
- Salve 5 : 187/288 configs 40k au réveil, se termine.

### 31/07 20h20 — Réveil 4 : salve 4 récoltée, le comparatif propre

- Salves 3b (97) et 4 (384) finies, chaîne 40k complète (313 927 pics s3
  sur la grille 7j, 45 échecs). Salve 5 lancée. resultats.csv : 1 441
  configs (dédupliquer par tag, garder la dernière).
- **Salve 4, n apparié à 5 000 (217 configs valides)** :
  - **médias** : lefigaro 1,306 > lemonde 1,245 > lesechos 1,196 >
    mediapart 1,068 — l'effet le plus net de la campagne. Mediapart n'a
    presque aucune corrélation temporelle au-delà des marges.
  - **grille** : 1j 1,164 → 3j 1,225 → 7j 1,313 (monotone).
  - **demi-fenêtre** : ±10 1,190 → ±50 1,260 (monotone).
  - **seuil** : s4 1,223 vs s6 1,206 — petit et de signe instable selon le
    média (le test lemonde-seul du réveil 2 donnait s6 > s4). Non robuste.
  - **filtre** : plat (1,215-1,221) ; seules 5 configs noms_propres
    atteignent n=5000, l'effet +0,07 vu sur lemonde d15 (réveil 2) ne se
    généralise pas clairement. À requalifier « petit, localisé ».
  - Top : lefigaro7j × d50 × s4 × vocab large, exces6 1,61.
- **Réserve d'interprétation (pour la synthèse et le nul de demain)** :
  grille 7j × d50 = fenêtres de ±350 jours de parution — la structure
  captée peut être de la dérive lente (tendances, époques) autant que des
  formes d'événement. Le nul par décalage circulaire par ligne (préserve
  l'autocorrélation de chaque fenêtre, détruit l'alignement sur le pic)
  départagera : prévu en resultats_rotation.csv sur les configs de tête.
