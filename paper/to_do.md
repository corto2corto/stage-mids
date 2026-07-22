# Stage MIDS — À faire

## Notations

- $X^w_t$ = nombre total d'occurrences du mot $w$ à l'instant $t$
- $N_t$ = nombre total de mots dans le corpus à l'instant $t$
- $f_t = \frac{X^w_t}{N_t}$ = fréquence du mot $w$ à l'instant $t$

Le problème avec $f_t$ est que ce n'est pas un entier ; je préférerais conserver la structure entière de $X_t$, mais il faut tout de même une forme de normalisation par rapport à $N_t$. Pour cela, je propose de normaliser la moyenne de n'importe quel modèle probabiliste par rapport à $N_t$.

## Détection de pics (spikes)

### Étape 1 : ajuster un modèle binomial négatif

La loi binomiale négative de paramètres $p \in (0,1)$, $r > 0$ est définie par

$$\mathbb{P}(X = k) = \frac{\Gamma(k + r)}{\Gamma(k + 1) \Gamma(r)} p^k (1-p)^r.$$

Sa moyenne et sa variance valent

$$\mathbb{E}[X] = \frac{r(1-p)}{p} \quad \text{et} \quad \mathrm{Var}[X] = \frac{r(1-p)}{p^2}.$$

Une paramétrisation courante consiste à poser $m = r(1-p)/p$, de sorte que $\mathbb{E}[X] = m$ et $\mathrm{Var}(X) = m + m^2/r$. C'est la paramétrisation que nous utiliserons, c'est-à-dire

$$\mathbb{P}(X = k) = \frac{\Gamma(k + r)}{\Gamma(k + 1) \Gamma(r)} \left(\frac{r}{m+r}\right)^k \left(\frac{m}{m+r}\right)^r.$$

- D'après GPT, ajuster une binomiale négative avec cette paramétrisation peut se faire avec `statsmodels.discrete.discrete_model.NegativeBinomial`, avec $\phi = r^{-1}$.
- Les queues sont exponentielles, i.e. $p_n \approx e^{-c n}$ pour un certain $c$. Les queues deviennent plus légères quand $r$ augmente.
- Quand $r \to \infty$, la loi converge vers une loi de Poisson de paramètre $m$ ; ce modèle est donc très polyvalent, absorbant les lois de Poisson, géométrique et de Pascal.
- Comme $X^w_t$ peut fortement dépendre du nombre de mots $N_t$, il est naturel de normaliser le modèle linéairement avec $N_t$, i.e. de paramétrer $X_t \sim \mathrm{NB}(\mu N_t, r)$. Il est apparemment possible d'ajuster ce modèle sur les observations $(X_t, N_t)$ à l'aide du paramètre `exposure` de `statsmodels.discrete.discrete_model.NegativeBinomial`. Dans ce cas, $\mu$ sera la fréquence moyenne du mot $w$.
- Une fois le modèle ajusté et les paramètres optimaux $\mu_*, r_*$ trouvés, il est important de tracer la densité de $\mathrm{NB}(\mu_* \times 100000, r_*)$ par-dessus l'histogramme des données (le graphe de droite sur les graphes d'Elias) pour voir si l'ajustement est bon ou non.

Diagnostics pour la qualité de l'ajustement ? Je ne sais pas. Vérifier peut-être la moyenne, la variance, l'asymétrie (skewness) et l'aplatissement (kurtosis) ?

**MAJ 20/07/2026** : le fit bascule vers un mélange Bernoulli × NB décalée (les jours à zéro cassent le fit) — voir « 2. Passer au mélange Bernoulli × NB » en Phase 2.

### Étape 2 : détecter les pics

Une fois un modèle ajusté, disons $\mu_*, r_*$, on peut détecter les valeurs aberrantes (outliers) dans les données. Notons $P_t$ la densité de probabilité de $\mathrm{NB}(\mu_* N_t, r_*)$. On pose

$$p_t = P_t([X_t, +\infty]),$$

qui est la $p$-valeur de $X_t$ sous le modèle ajusté. On déclare $X_t$ comme aberrant si $p_t$ est trop petit, disons $p_t < 0{,}0001$.

Remarques.

- $\log_{10}(p_t)$ est appelé la « surprise » de l'observation $X_t$. Plus elle est élevée, plus l'observation est surprenante.
- On peut procéder en plusieurs tours : ajuster un premier modèle NB2, puis retirer tous les « outliers évidents » (ceux ayant une surprise très élevée), puis réajuster un modèle sur les données restantes, retirer à nouveau les outliers, etc.
- Diag : tracer l'histogramme des $p_t$, il devrait être à peu près uniforme, sauf pour quelques outliers trop proches de $0$ ?

### Étape 3 : clusters d'activité anormale

*(Ébauche à valider — cette section n'a jamais été rédigée.)*

Un pic est rarement isolé : un jour aberrant est souvent entouré de jours eux aussi au-dessus du bulk, et l'étape 2 les compte comme autant de pics distincts alors qu'il s'agit d'un seul événement (typiquement le Covid, plusieurs semaines continues). L'objet naturel est donc la *période d'activité anormale*, pas le jour aberrant.

Piste :

- Fusionner en un même cluster les jours aberrants ($p_t < 10^{-4}$) séparés de moins de $g$ jours (trou toléré à régler, de l'ordre de quelques jours).
- Caractériser chaque cluster : date de début, durée, jour de surprise maximale, surprise cumulée.
- N'en retenir qu'un représentant, le jour de surprise maximale — c'est la NMS de la Phase 2 §4, en formulation « périodes » plutôt que « fenêtres qui se recouvrent ».

Même objet que « passer des sauts isolés aux périodes d'activité anormale » (Pour plus tard), vu depuis la détection de pics. Reste à trancher : garder la période entière comme datapoint, ou seulement son pic.

### Étape 4 : séries temporelles ?

Si ce qui précède ne fonctionne pas très bien, on pourrait ajouter un modèle autorégressif sur les paramètres. @Elias : il serait bien de tracer la fonction d'autocorrélation de $X_t$, ou plutôt de $f_t$ ; je m'attends fortement à observer des autocorrélations intéressantes dans $f_t$.

On ajusterait typiquement quelque chose comme $m_t = N_t \times e^{R_t}$ avec $R_t$ un processus AR(1) ?

## Nouveautés à intégrer (par ordre de difficulté)

Cette section rassemble les pistes issues des échanges les plus récents, classées de la plus simple à la plus difficile à mettre en œuvre. (La loi de Poisson, la batterie d'indicateurs/graphes et le rappel sur la $p$-valeur — anciennement en « Facile » — sont désormais faits : loi paramétrable dans `pics.py`, indicateurs et graphes produits par `/fiche`.)

### Moyen

- **Regarder le différentiel de fréquences $X_t - X_{t-1}$**, et pas seulement $X_t$. Ce différentiel peut être négatif : on obtient donc des sauts vers le haut (quantile supérieur) *et* vers le bas (quantile inférieur). Un saut anormal *vers le bas* peut s'interpréter comme une volonté de censure ou d'invisibilisation. Il faudra comparer ce signal à la fréquence elle-même.

- **Distinguer soigneusement le différentiel de la fréquence.** Difficulté observée : les pics négatifs semblent souvent n'être que le contrecoup d'un pic positif précédent (retour à la normale après une hausse), plutôt qu'une vraie censure. Deux pistes complémentaires :
  - passer à un modèle autorégressif d'ordre supérieur, AR(2) ou AR(3), pour absorber cet effet de rebond ;
  - garder à l'esprit qu'il est aussi possible qu'il n'y ait tout simplement pas de phénomène de censure sur les mots regardés.

- **Cadrer outliers vs breakpoints.** Distinction à garder claire : pour l'instant on cherche des *outliers* (périodes courtes d'activité anormale : un jour, une semaine, un mois — typiquement le Covid), car c'est le plus simple et probablement déjà très significatif. La question des *breakpoints* (changement total et définitif de toute la distribution, typiquement un rachat comme Bolloré → JDD) viendra dans un second temps.

### Difficile

- **Ajuster une loi commune à plusieurs mots.** Au lieu d'ajuster les occurrences d'un seul mot, ajuster simultanément les occurrences de tout (ou d'une partie) du vocabulaire, pour disposer d'un critère d'outlier partagé. Plus difficile que l'approche mot par mot ; à tenter dans un second temps.

- **Détecter les breakpoints (ruptures durables).** Au-delà des pics ponctuels, détecter un déplacement définitif de la distribution après un événement (rachat de journal). Suppose des outils de détection de rupture, pas seulement de détection d'outliers.
  - Ressource externe repérée : **tsseg** (<https://github.com/fchavelli/tsseg>), framework de segmentation / changepoint detection clé en main pour séries temporelles. On y met la série et il la segmente ; sa doc est un gros catalogue d'algos de changepoint detection. À garder en tête pour cette étape.
  - Points de départ conseillés quand on ne sait pas quel algo prendre : **GGS** (Greedy Gaussian Segmentation) et **ClaSP**. Tenter, avec un *gut check* en plottant la série (par ex. « guerre », ou « pas » dans Le Monde sur toute la période).

- **Question ouverte : le bruit décroît-il vraiment en $\sqrt{n}$ en lexicométrie ?** Intuition de Benoît : probablement *non* (comportement non-diffusif). Deux raisons avancées :
  - les mots ne sont pas des variables indépendantes : le texte est un tissu ;
  - la taille d'échantillon effective (*effective sample size*) est très inférieure à la taille brute $n$ (nombre de tokens) : on ne peut pas répéter « inflation » trois fois par phrase (facteur constant), et le texte se répète (effet non linéaire, ESS probablement concave en $n$).

  Conséquence pratique : on observe des valeurs plus extrêmes sur un petit corpus (un hebdo) que sur un grand (un quotidien). Le modèle standard « mots i.i.d. » donnerait une loi binomiale à variance décroissant en $\sqrt{n}$ ; il n'existe pas de littérature sur la construction d'intervalles de confiance en lexicométrie. Piste suggérée : du **bootstrap** pour mesurer empiriquement le rythme de convergence.

## Phase 2 : classification des sauts (juillet 2026)

Décision : arrêter de raffiner la détection de pics et avancer vite vers un POC de classification des sauts, qu'on raffinera ensuite. Les tâches ci-dessous sont dans l'ordre où les faire.

### 1. Corriger le plotting des points rouges — terminé (élucidé le 17/07/2026)

Sur certaines séries (ex. « chomage »), des pics au-dessus du seuil ne sont pas coloriés en rouge (années 88–90). Hypothèse : le plotting affiche un nombre fixe de points rouges (environ 21) au lieu de tous les points au-dessus du seuil.

- [x] Compter les points rouges sur plusieurs figures : **de 0 à 144 selon la fiche** (chomage 20, mitterrand 21, immigration 23, chirac 24, guerre 144, covid 0…). L'hypothèse du nombre fixe est fausse — plusieurs fiches autour de 20–25 ont donné cette impression.
- [x] Chercher un cap dans le code : **aucun** — `fig_serie` (rapport_lib.py) colorie tous les jours avec $p_t < 10^{-4}$, vérifié en recalculant chomage (20 recalculés = 20 sur la fiche).
- [x] Expliquer les pics 88–90 non rouges : **la figure montre $f_t$ mais la détection opère sur $(X_t, N_t)$**. Les pics visibles de 1988–90 sur chomage sont de deux sortes : des jours à corpus quasi vide ($N_t$ = 252 à 1 100 mots, 1 occurrence suffit à faire $f_t \approx 400$ pour 100 000, mais $p_t \approx 3 \times 10^{-2}$ — pas surprenant du tout sous la loi du jour) et des pics réels modérés ($X_t \approx 30$, $p_t \approx 4 \times 10^{-3}$) au-dessus du seuil $10^{-4}$. Ce n'est ni un artefact ni un bug : rien à corriger dans le code.
- [ ] (option à discuter) Rendre le seuil lisible sur la figure : tracer la fréquence critique du jour (quantile $10^{-4}$ de $\mathrm{NB}(\mu N_t, r)$ ramené en fréquence) et/ou signaler les jours à $N_t$ minuscule, pour que les pics non marqués s'expliquent d'eux-mêmes.

### 2. Passer au mélange Bernoulli × NB décalée (20/07/2026)

Constat : les jours à zéro occurrence sont très fréquents et ce sont souvent eux qui cassent le fit (visible sur les histogrammes). Cas extrême mesuré : covid sur 1944–2025 a 92 % de jours à zéro, le fit donne $\hat r = 0{,}02$, queue si lourde qu'aucune $p$-valeur ne descend sous $10^{-3}$ : zéro pic détecté. Ce modèle remplace la piste « restreindre à la période d'activité » : les zéros structurels sont portés par la Bernoulli au lieu d'être découpés.

Forme paramétrique : $p\,\delta_0 + (1-p)\,(\mathrm{NB} + 1)$, avec $p$ la probabilité de zéro occurrence.

- [x] Séparer les jours à $X_t = 0$ des jours à $X_t \geq 1$ ; estimer $p$ = part des jours à zéro (Bernoulli). **Fait** (`rupture/pics.py`, route `/fiche`).
- [x] Fiter la NB uniquement sur les jours à $X_t \geq 1$, sur $Y_t = X_t - 1$ (la NB commence à 0), toujours avec l'exposure $N_t$. **Fait.**
- [x] Ne **pas** supprimer purement les jours à zéro : ils restent dans le modèle via la Bernoulli. **Fait.**
- [x] Y ajouter le double fit validé : retirer les outliers évidents puis réajuster. **Fait et testé** (campagne du 20/07, `double_fit.pdf` : +54 pics, tous des événements réels).
- [x] Recalculer les $p$-valeurs des jours à $X_t \geq 1$ : sous le mélange, $p_t = (1-p)\,\mathbb{P}(\mathrm{NB} \geq X_t - 1)$. **Tranché (21/07/2026)** : convention du mélange conservée ; seuil de détection $10^{-4}$ par défaut, outliers évidents à $10^{-6}$ par défaut pour le refit.
- [x] Vérifier sur les mots tests : **fait** (fiches_bnb.pdf, 20 mots) — χ²/ddl amélioré ou égal presque partout, internet débloqué (4 → 24 pics) ; covid reste à 0 pic (sa vie active est une vague unique : relève de l'étape 4), les autres comptages restent du même ordre.

Pipeline final câblé dans `rupture/` (21/07/2026) : `extraire` (mécanisme unique, aussi utilisé par l'API) → `serie` → `pics` (loi et nombre de fits paramétrables) → `fenetres`.

### 3. Construire le dataset de sauts

Objectif : une matrice $N \times D$ de fenêtres centrées sur les sauts, avec $N \approx 100\,000$ attendu.

**Choix du gros vocabulaire (actés le 21/07/2026).** Modèle zéro : unigrammes du Monde seulement — l'extension aux autres médias (et bi/trigrammes) est à faire une fois la chaîne validée. Exclusions : mots outils (`MOTS_OUTILS`), tokens commençant par un chiffre (mêmes règles que les tops) et tokens d'une seule lettre (résidus de tokenisation, ex. « t ») ; graphies avec/sans accents fusionnées comme dans `extraire` (sinon pics dupliqués dans la matrice) ; noms propres conservés. Plancher de fréquence : le critère est le nombre de **jours actifs** ($X_t \geq 1$), le total d'occurrences est abandonné — c'est le nombre de jours non nuls qui conditionne le fit de la NB du mélange et la forme des fenêtres pour la PCA. Sélection : **top-10 000 par jours actifs** (coupe ≈ 7 100 jours actifs sur ~26 800 jours de parution).

- [x] Recensement du vocabulaire : scan complet fait le 21/07/2026 (`exploration/scan_vocab_lemonde.py`, 3 min 20, 286 M lignes) → `data/vocab_lemonde_unigram.csv` (441 081 mots ; 413 588 après exclusions et fusion des graphies). Repères : ≥ 1 000 jours actifs = 39 316 mots, ≥ 5 000 = 13 545, top-10 000 = coupe à 7 121.
- [ ] **Comparaison à faire plus tard** : refaire la chaîne avec la variante seuil ≥ 1 000 jours actifs (39 316 mots, ~4× le top-10 000) et comparer ce que la queue du vocabulaire apporte ou pollue (dataset de sauts, PCA).
- [x] Extraire les séries du vocabulaire retenu : **fait le 21/07/2026** (`rupture/masse.py`, une passe sur `unigram`, 5 min 30) → `data/vocab_series_lemonde.npz` (X 26 917 jours × 10 000 mots int32, dates, N, mots, clés ; 126 Mo). Règle d'absorption actée : l'unité est la **graphie**, une graphie < 1 % de la dominante de sa clé désaccentuée est un doublon OCR sommé jour par jour dans celle-ci (« chomâge » → « chômage »), au-delà mot à part entière (« retraite » / « retraité » séparés). Validé contre `extraire.serie()` : retraite/internet/mitterrand identiques à l'occurrence près, chomage = +78 occurrences OCR récupérées (voulu).
- [ ] Sélectionner tous les couples (mot, date) dont la surprise dépasse $4$, c'est-à-dire $p$-valeur $< 10^{-4}$.
- [ ] Pour chaque saut, extraire la fenêtre de la série sur $\pm d$ jours autour de la date, avec $d = 15$, soit une dimension $D = 1 + 2d = 31$.
- [ ] Garder pour chaque ligne les métadonnées (mot, date, fréquence, $p$-valeur) à côté de la matrice.

### 4. Dédoublonner les pics rapprochés (NMS)

Si un mot a plusieurs pics à moins de $d$ jours d'écart, les fenêtres se recouvrent et les mêmes données entrent plusieurs fois dans la matrice.

**Décision (22/07/2026)** : NMS **glouton non-transitif**, pas de groupement par recouvrement — le groupement de proche en proche est du single-linkage, dont l'effet de chaînage soude les longues périodes en « groupes géants » réduits à un datapoint (mesuré : 164 groupes de plus de 90 jours de parution d'étendue, ex. « syrienne » 203 pics sur 760 jours). Algorithme : tri par surprise décroissante, chaque pic retenu supprime ses voisins à moins de 31 jours de parution **de lui** ; un pic supprimé ne supprime personne. 31 = largeur de fenêtre → aucune paire de fenêtres gardées ne se chevauche, par construction. Justifications détaillées au journal du 22/07/2026.

- [x] Implémentation : `rupture/nms.py` (`pics_<media>.csv` → `pics_<media>_nms.csv`, colonne `n_absorbes` en plus), avec contre-vérification indépendante par `scipy.signal.find_peaks(height=4, distance=31)` et écarts consignés dans `pics_<media>_nms_ecarts.txt`.
- [x] Testé en local sur les 164 254 pics du serveur : 123 465 gardés (75,2 %), médiane 10 représentants par mot ; 46 mots avec écart de contre-vérif sur 9 817 — 45 égalités de surprise (arrondi 2 décimales du CSV), 1 pic à exactement 31 jours du maximum mais non-maximum local du signal (compris, conforme à notre critère). Aucun bug.
- [x] Documenter les choix faits (taille du voisinage, critère de conservation) : journal du 22/07/2026.
- [ ] Produire la sortie officielle sur gallica : `python -m rupture.nms lemonde`.

### 5. Normaliser les fenêtres avant la PCA

Ne pas faire la PCA sur les occurrences ni les fréquences brutes : elle détecterait juste que certains mots sont plus fréquents que d'autres.

- [ ] Option par défaut : stocker les $z$-scores le long de la fenêtre.
- [ ] Alternative à tester : normalisation de chaque fenêtre sur $[0,1]$.
- [ ] Vérifier ce que fait l'option de normalisation intégrée des fonctions de PCA (remarque de Benoît) : elle standardise colonne par colonne, ce qui n'est pas la même chose que normaliser chaque fenêtre.

### 6. PCA : le modèle zéro

Faire une PCA sur la matrice $N \times D$, sans ondelette ni autre transformation.

- [ ] Lancer la PCA et tracer la variance expliquée par composante.
- [ ] Visualiser les premières composantes comme des profils temporels. Attendu : des directions simples et peu informatives, genre « activité déjà forte avant le saut et qui continue après » ou « activité nulle avant, forte après », pas trop loin de Sornette.
- [ ] Consigner les résultats comme *modèle zéro* : analyse à l'aveugle, les mots ne sont que des séries temporelles (on oublie l'identité des mots et les dates). Important pour l'article à venir.

### 7. CSV des pics à transmettre

- [ ] Extraire un petit CSV avec les colonnes (mot, date, fréquence du pic, $p$-valeur du pic) et le transmettre.

Statistiques à en tirer :

- nombre total de sauts par jour (co-jumps) ;
- histogramme des $\log(p)$ des sauts (amplitudes) — voir s'il y a des valeurs extrêmes ;
- nombre de pics par mot.

### Pour plus tard (noté, pas à faire maintenant)

- Passer des sauts isolés aux *périodes d'activité anormale* (remarque de Benoît, objectif de long terme partagé — rejoint l'étape 3 de la détection de pics).
- Enrichir les datapoints avec le profil *par journal* : au lieu d'une fenêtre, les $J$ fenêtres des $J \approx 14$ journaux autour du même pic. C'est là qu'on attend de vrais résultats.
- Intégrer d'une façon ou d'une autre les co-jumps (sauts de mots différents à la même date) dans l'analyse.
- **Comparaison avec le corpus GIEC (Cosmos / Carbon Brief).** Base Cosmos, présentée comme la plus grande base de recherche sur le changement climatique (<https://interactive.carbonbrief.org/cosmos/index.html>). Piste : suivre l'évolution de certains termes dans les rapports du GIEC depuis sa création (1988) à aujourd'hui — par ex. « justice climatique », « adaptation » — et mettre ça en regard de notre base d'articles de presse.

## Pistes d'analyse notées en juin-juillet 2026 (déplacées du journal)

Notes prises au fil des échanges du début du stage, quand le corpus n'était pas
encore constitué. Ce qui a été fait depuis est barré de la liste : le site de
suivi, les premiers comptages de mots et le choix du format de base (SQLite,
une base n-grammes par journal) sont réglés.

- Analyser les prénoms (qui parle de qui, et quand).
- Séries temporelles.
- Comptage de mots pondéré : TF-IDF.
- Sauts intrinsèques et extrinsèques (voir l'article de Mala).
- MOR / traitement automatique des langues.
- Analyse de sentiment : voir si BERT est utilisable sur le corpus.
- Vérifier les archives du Monde (note d'origine incomplète : vérifier la
  couverture réelle des archives récupérées, en particulier les premières
  décennies).
