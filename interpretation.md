# Interprétation — que disent les 40 fiches, et quel modèle pour les rachats ?

*Prolonge `fiches_mots.pdf` (40 mots × Poisson/binomiale négative/χ², Le Monde 1944–2025).
Les tests de rupture de la section 4 ont été refaits sur nos propres séries pour ce document.*

---

## 1. Ce que les 40 fiches montrent

**La loi de Poisson est rejetée partout, et ce n'est pas un accident.** Si chaque
occurrence d'un mot était un tirage indépendant parmi les $N_t$ mots du jour, les
comptages $X_t$ suivraient une loi de Poisson (variance = moyenne). Or nos Var/Moy
observés vont de ~2 à plus de 50 (*confinement* : 52). La raison est linguistique avant d'être statistique : un
mot n'apparaît pas indépendamment de lui-même. Un attentat, une élection, une loi en
débat déclenchent *plusieurs* articles qui répètent le mot des dizaines de fois — les
occurrences arrivent en **rafales** (*burstiness*). C'est un fait établi depuis
longtemps en statistique textuelle : Church & Gale (1995) et Katz (1996) ont montré
que les mots « à contenu » violent systématiquement Poisson et qu'un mélange de
Poisson — dont la binomiale négative est le cas le plus courant — est le bon point de
départ. Nos fiches redécouvrent ce résultat sur 80 ans du *Monde*.

**La binomiale négative encaisse les rafales, et le paramètre r̂ les mesure.** La NB,
c'est une Poisson dont l'intensité varie d'un jour à l'autre selon une loi Gamma :
les jours ne sont plus interchangeables, certains sont « chauds ». Petit r̂ = très
bursty, grand r̂ = presque Poisson. La hiérarchie des r̂ du recueil est parlante :

| r̂ | mots | lecture |
|---|---|---|
| < 0,5 | zemmour (0,28), gaza (0,32), vaccin (0,35), immigration (0,44), islam (0,46) | mots-événements : silence, puis rafales |
| ≈ 1 | euro, internet, nucléaire, covid, macron, jeux | régime mixte |
| > 2 | guerre (3,87), europe (4,96), milliards (3,84), crise (3,13) | vocabulaire de fond, présent chaque jour |

**Le χ²/ddl est une échelle de lecture, pas un simple verdict.** La colonne χ²/ddl
(NB) du sommaire va de 0,49 à 4,19. Autour de 1 : la NB décrit bien les comptages
jour par jour (8 mots non rejetés : *algérie*, *francs*, *internet*, *covid*,
*vaccin*, *ukraine*, *gaza*, *intelligence artificielle*). Nettement au-dessus de 1 :
la série mélange des **régimes** que la NB unique ne peut pas concilier. Les pires
ajustements sont les noms de présidents observés sur des fenêtres qui enjambent leur
élection — chirac 4,19, mitterrand 3,44, hollande 2,05 — et *attentats* (2,90). Ce
n'est pas la loi qui est mauvaise : c'est l'hypothèse « mêmes paramètres du premier
au dernier jour » qui est fausse. Autrement dit, **le χ²/ddl élevé est déjà un
détecteur de rupture rudimentaire.**

**Attention au piège inverse — c'est le résultat le plus important du recueil.** Le
non-rejet ne prouve *pas* l'absence de rupture. La fiche *macron* 2014–2025 affiche
un χ²/ddl de 1,05, adéquation quasi parfaite… alors que la série contient une rupture
énorme (section 4 : la fréquence triple en mai 2017). Comment est-ce possible ? Parce
qu'un **mélange de deux NB ressemble à une NB** : le test d'adéquation regarde
l'histogramme global des comptages, pas leur ordre dans le temps. Il valide la
*forme* de la distribution, pas sa *stabilité*. Pour détecter un changement, il faut
un modèle qui compare explicitement avant et après. D'où la section suivante.

---

## 2. Le lien avec le mémoire

Notre question : *les rachats de journaux modifient-ils la couverture thématique ?*
Traduite dans le langage des fiches : **après la date du rachat, les paramètres
(μ, r) de certains mots changent-ils ?** Un thème qu'on étouffe, c'est μ qui baisse ;
un thème qu'on pousse, c'est μ qui monte ; une ligne éditoriale qui se « militantise »
peut aussi se voir sur r (couverture continue au lieu de réactive).

C'est exactement un problème de **détection de rupture** (*change point detection*),
un domaine bien balisé : voir la revue de Truong, Oudre & Vayatis (2020) et
l'algorithme PELT (Killick et al., 2012) pour le cas général, et Kulkarni et
al. (2015) pour l'application aux séries de fréquences de mots. Et le résultat
empirique de référence en économie des médias — Cagé et al. sur le rachat de
Canal+/CNews par Bolloré en 2015 — montre deux choses qui calibrent nos attentes :
les effets d'un rachat sont **réels et mesurables** (la part d'invités d'extrême
droite passe de 7 % à ~22 % sur CNews), mais **progressifs** — le basculement s'étale
sur plusieurs années, il ne date pas du jour de la signature. Il nous faut donc les
deux outils : le test à date connue (le rachat) *et* la détection à date inconnue (le
vrai basculement éditorial).

---

## 3. Le modèle testé : la binomiale négative par morceaux

Le modèle le plus simple qui prenne au sérieux à la fois la burstiness (section 1) et
la question du mémoire (section 2) :

$$X_t \sim \text{NB}(\mu_k N_t,\ r_k) \quad \text{sur chaque segment } k$$

même loi que dans les fiches, mais dont les paramètres peuvent changer à des dates de
rupture. Trois situations, de la plus simple à la plus réaliste :

**(A) La date de rupture est connue** — c'est le design « rachat ». On ajuste une NB
sur toute la période (2 paramètres), puis une NB avant et une après la date (4
paramètres), et on compare les log-vraisemblances : $LRT = 2(\ell_{avant} +
\ell_{après} - \ell_{unique})$. Sous l'hypothèse « rien n'a changé », ce LRT suit un
χ² à 2 degrés de liberté : on rejette à 5 % dès que LRT > 5,99. C'est un test simple,
puissant, et qui dit *quoi* a changé (μ ? r ? les deux ?).

**(B) La date est inconnue** — on calcule le LRT pour *toutes* les coupures possibles
(chez nous : chaque début de mois) et on garde le max. Attention, piège classique :
le max de centaines de tests ne suit plus un χ²(2). Prendre 5,99 comme seuil, c'est
s'assurer de « détecter » des ruptures dans du bruit — c'est le problème des **tests
multiples**. La parade : simuler. On génère des séries sous l'hypothèse nulle (NB
unique, avec les paramètres estimés et les *vrais* $N_t$), on refait le scan sur
chacune, et on regarde la distribution du max obtenu. Le quantile 95 % de cette
distribution est le bon seuil. Nos simulations (section 4) le confirment : sous H0 le
max *médian* vaut déjà ~6,5 — au-dessus du seuil naïf de 5,99.

**(C) Plusieurs ruptures** — on coupe au max du scan, puis on recommence dans chaque
moitié (segmentation binaire), en n'acceptant une coupure que si elle « paie » sa
complexité : seuil de type BIC, $3\log n$ (trois paramètres en plus par rupture :
μ, r et la date). Pour un vrai passage à l'échelle (des milliers de séries), on
remplacera la segmentation binaire par PELT via le package `ruptures` — même logique,
optimisation exacte et rapide.

*Note technique : pour rendre les milliers d'ajustements du scan et des simulations
abordables, μ est estimé par quasi-vraisemblance (ΣX/ΣN) et r par profil de
vraisemblance — les valeurs diffèrent donc légèrement des fiches (statsmodels), sans
changer les conclusions.*

---

## 4. Résultats des tests

### (A) Rupture à date connue — *macron*, coupure au 7 mai 2017 (élection)

| | μ̂ (pour 10⁵) | r̂ | χ²/ddl |
|---|---|---|---|
| 2014 → 06/05/2017 | 13,7 | 0,35 | 1,46 |
| 07/05/2017 → 2025 | 39,8 | 2,49 | 1,50 |
| période entière | 32,8 | 0,98 | **0,98** |

**LRT = 2 574** contre un seuil de 5,99 : la rupture est écrasante, p ≈ 0. La
fréquence triple (13,7 → 39,8) et r est multiplié par 7 : avant l'élection, *macron*
apparaît en rafales (candidat = couverture événementielle) ; après, c'est un mot de
fond quotidien (président = couverture institutionnelle). **Et pourtant le χ²/ddl de
la période entière vaut 0,98** — adéquation parfaite. C'est la démonstration chiffrée
du piège de la section 1 : si on avait utilisé le test d'adéquation comme détecteur
de rupture, on aurait conclu « rien à signaler ». Pour le mémoire, la conclusion
méthodologique est nette : **le test avant/après est l'outil, le χ² d'adéquation
n'est qu'un diagnostic de forme.**

### (B) Rupture à date inconnue — scan calibré par simulation

**chirac 1986–2007** (le pire χ²/ddl du recueil, 4,19) : le scan détecte la rupture
au **1er septembre 1994** avec M = 494. Sous H0 (100 simulations) : max médian 6,5,
quantile 95 % = **11,8**. Le signal est 40 fois au-dessus du seuil. La date est
instructive : pas mai 1995 (l'élection) mais la rentrée politique 1994, quand la
candidature Chirac se lance face à Balladur — **la couverture bascule avant
l'événement institutionnel**. Même segmentée, la série garde des χ²/ddl ≈ 3 : vingt
ans de vie politique contiennent plus de deux régimes (une seule coupure ne suffit
pas ; il en faudrait plusieurs, cf. (C)).

**covid 2020–2024** (fiche : χ²/ddl 1,02, NB *non rejetée*, 0 jour anormal) : le
scan détecte une rupture au **1er mars 2022**, avec M = 1 728 contre un quantile
95 % simulé de 10,7. La fréquence s'effondre de 82,6 à 16,7 pour 10⁵ — divisée par
cinq — au moment précis où la fin de la vague Omicron et l'invasion de l'Ukraine
(24 février 2022) chassent l'épidémie de l'agenda. Deuxième démonstration du piège
de la section 1 : la NB unique était statistiquement irréprochable, alors que la
série contient l'un des effondrements de couverture les plus violents du corpus.
**L'adéquation regarde la forme des comptages, le scan regarde leur ordre dans le
temps.**

### (C) Ruptures multiples — *terrorisme* 1970–2024

Segmentation binaire, coupures sur grille trimestrielle, seuil BIC = 3 log n ≈ 29,5.
Sept ruptures sont retenues (toutes avec LRT de 65 à 1 630, très au-dessus du seuil) :

| segment | μ̂ (pour 10⁵) | r̂ | χ²/ddl | lecture historique |
|---|---|---|---|---|
| 1970 → 06/1972 | 1,4 | 1,01 | 1,16 | avant Munich |
| 07/1972 → 09/1977 | 2,4 | 0,67 | 1,29 | Munich 1972, années de plomb |
| 10/1977 → 09/1987 | 6,5 | 0,88 | 1,64 | automne allemand 1977, vague d'attentats de Paris 1985–86 |
| 10/1987 → 06/2001 | 3,2 | 1,17 | 1,41 | reflux des années 1990 |
| 07/2001 → 12/2001 | **31,2** | 0,86 | 0,60 | 11-Septembre : ×10 en six mois |
| 2002 → 09/2006 | 12,6 | 2,13 | 1,31 | après-11-Septembre, Irak |
| 10/2006 → 03/2018 | 6,9 | 1,26 | 1,49 | dont la vague 2015–2016 (Charlie, Bataclan) |
| 04/2018 → 2024 | 4,4 | 1,75 | 1,12 | reflux post-Daech |

La machine ne connaît ni Munich ni le Bataclan : elle ne voit que des comptages, et
retrouve pourtant la chronologie du terrorisme telle que l'écrirait un historien des
médias — y compris le fait que la vague 1977–1987 pèse plus lourd, en couverture de
fond, que les années 1990. Deux réserves de lecture : les dates sont arrondies au
trimestre (grille), et une rupture de *fréquence* peut être un changement du monde
(il y a plus d'attentats) autant qu'un changement de *ligne éditoriale* — sur un seul
journal, rien ne permet de les distinguer. C'est exactement pour cela que le
protocole du mémoire comparera plusieurs journaux (section 5, point 4).

---

## 5. Ce qu'on en retient pour le protocole « rachats »

1. **Le bon objet statistique est le couple (μ, r) par segment**, pas l'adéquation
   globale. Le test central du mémoire sera le LRT avant/après à la date du rachat
   (design (A)), mot par mot.
2. **Compléter par le scan (B)** : Cagé et al. montrent que les effets d'un rachat
   sont progressifs. La date détectée par le scan, comparée à la date du rachat, est
   une information en soi (basculement immédiat ? différé ? antérieur — changement de
   direction avant la vente ?).
3. **Toujours calibrer par simulation.** Nos maxima sous H0 dépassent le seuil naïf
   du χ²(2) : sans calibration, on fabriquerait des découvertes. Et quand on testera
   des centaines de mots × journaux, il faudra en plus une correction de multiplicité
   entre mots (type FDR/Benjamini-Hochberg).
4. **Le point de comparaison, c'est les autres journaux.** Une rupture sur *retraites*
   en 2023 dans un journal racheté ne prouve rien : tout le monde a couvert la
   réforme. Le signal éditorial, c'est une rupture qui apparaît **dans le journal
   racheté et pas chez les témoins** à la même date — un raisonnement en différence
   de différences. Notre corpus à trois journaux (et bientôt plus) est construit pour
   ça.
5. **Limites à garder en tête.** (i) On détecte des ruptures de *fréquence*, pas de
   *sens* : un journal peut parler autant d'immigration en changeant complètement de
   vocabulaire autour — l'étape suivante, ce sont les ruptures dans les
   représentations (embeddings diachroniques, Kulkarni et al. 2015). (ii) La
   polysémie brouille certains mots (*hollande*, *jeux*, *dissolution*). (iii) Les
   graphies OCR sont sommées mais pas parfaites. (iv) $N_t$ change de nature sur 80
   ans (pagination, suppléments) : la normalisation par $N_t$ absorbe le niveau,
   pas les changements de rubriquage — d'où l'intérêt de fenêtres de ±2-3 ans autour
   des rachats plutôt que de très longues périodes.

---

## Références

- Church, K. & Gale, W. (1995). *Poisson mixtures*. Natural Language Engineering,
  1(2), 163–190. — pourquoi Poisson échoue sur les mots à contenu.
  <https://www.cambridge.org/core/journals/natural-language-engineering/article/abs/poisson-mixtures/52E7F9429D0EC03EEC6674E071727B64>
- Katz, S. (1996). *Distribution of content words and phrases in text and language
  modelling*. Natural Language Engineering, 2(1), 15–59. — la burstiness.
- Killick, R., Fearnhead, P. & Eckley, I. (2012). *Optimal detection of changepoints
  with a linear computational cost*. JASA, 107, 1590–1598. — PELT.
  <https://arxiv.org/abs/1101.1438>
- Truong, C., Oudre, L. & Vayatis, N. (2020). *Selective review of offline change
  point detection methods*. Signal Processing, 167. — la revue de référence + le
  package Python `ruptures`. <https://arxiv.org/abs/1801.00718>
- Kulkarni, V., Al-Rfou, R., Perozzi, B. & Skiena, S. (2015). *Statistically
  Significant Detection of Linguistic Change*. WWW 2015. — détection de ruptures sur
  des séries de mots (fréquence, syntaxe, embeddings).
  <https://arxiv.org/abs/1411.3315>
- Cagé, J., Hengel, M., Hervé, N. & Urvoy, C. (2022). *Hosting Media Bias: Evidence
  from the Universe of French Broadcasts, 2002–2020*. — l'effet Bolloré/CNews,
  réel et progressif.
  <https://juliacage.com/wp-content/uploads/2022/02/Hosting-Media-Bias-Cage%CC%81-Hengel-Herve%CC%81-Urvoy-2022_02_16.pdf>
- Azoulay, B. & de Courson, B. (2023). *Gallicagram : les archives de presse sous
  les rotatives de la statistique textuelle*. Corpus, 24. — le cousin de notre API
  ngram. <https://journals.openedition.org/corpus/7944>
