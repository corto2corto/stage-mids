# Interprétation — des 40 fiches au protocole de détection des ruptures éditoriales

*Ce document prolonge `fiches_mots.pdf` (40 mots, Le Monde 1944–2025 : ajustements
Poisson/binomiale négative, tests du χ², jours anormaux). Il fait trois choses :
tirer les leçons statistiques du recueil (§1), passer en revue les familles de
modèles de détection de rupture et motiver un choix (§3), et soumettre ce choix à
une batterie de tests sur nos propres données — y compris les objections qu'un jury
ferait : dépendance temporelle, faux positifs, puissance, facteurs de confusion
(§4–§7). Tous les chiffres cités ont été calculés sur nos propres séries
(Le Monde 1944–2025, Le Figaro 2005–2023) ; les protocoles de calcul sont décrits
en place.*

---

## Résumé en six points

1. Les comptages de mots sont **surdispersés partout** (rafales d'actualité) ; la
   binomiale négative (NB) est le bon modèle *de bruit*, pas la Poisson.
2. Un **test d'adéquation ne détecte pas les ruptures** : sur *macron*, le χ²/ddl
   global vaut 0,98 (« tout va bien ») alors que la fréquence triple en mai 2017
   (LRT = 2 574). L'adéquation valide la forme des comptages, pas leur stabilité.
3. Le bon outil est la **NB segmentée** : test de rapport de vraisemblance (LRT)
   avant/après une date — connue (le rachat) ou inconnue (scan) — avec seuil
   **calibré par simulation**, jamais par la table du χ².
4. **Objection majeure, vérifiée sur nos données** : les résidus sont fortement
   autocorrélés (ACF(1) ≈ 0,6–0,9) parce qu'un sujet d'actualité persiste plusieurs
   jours ou semaines. Un scan quotidien calibré comme si les jours étaient
   indépendants rejette à tort dans 26 à 51 % des cas au lieu de 5 %. L'agrégation
   hebdomadaire et la calibration sous dépendance corrigent l'essentiel.
5. **La solution structurelle, c'est la comparaison entre journaux** : la part d'un
   journal dans le total des occurrences (modèle bêta-binomial) neutralise
   l'actualité commune. Vérifié sur *ukraine* : ruptures marginales énormes dans
   chaque journal en février 2022, part Monde/Figaro quasi inchangée (0,44 → 0,45).
   C'est le design différence-de-différences du mémoire.
6. La **puissance** est au rendez-vous pour des effets réalistes (§7) : avec ±1 à
   ±2 ans de données hebdomadaires, des déplacements de couverture de 20–30 % sur
   des mots de fréquence moyenne sont détectables — c'est l'ordre de grandeur des
   effets documentés dans la littérature sur les rachats (Martin & McCrain 2019 :
   ±25 % ; Cagé et al. 2022 : ×3 sur dix ans).

---

## 1. Ce que les 40 fiches montrent

**La Poisson est rejetée partout, et c'est un fait de langue, pas un artefact.** Si
chaque occurrence était un tirage indépendant parmi les $N_t$ mots du jour, $X_t$
serait Poisson (variance = moyenne). Nos Var/Moy vont de ~2 à plus de 50
(*confinement* : 52). La raison : un mot ne s'utilise pas indépendamment de
lui-même — un attentat, une élection déclenchent des rafales d'articles qui le
répètent. Cette **burstiness** est documentée depuis Church & Gale (1995) et Katz
(1996) : pour les mots « à contenu », il faut un mélange de Poisson, dont la NB
(mélange Poisson-Gamma) est le cas canonique. Nos 80 ans du *Monde* le confirment
mot après mot.

**r̂ mesure la burstiness.** Petit r̂ = rafales ; grand r̂ = présence régulière :
*zemmour* 0,28, *gaza* 0,32, *vaccin* 0,35 (mots-événements) contre *guerre* 3,87,
*europe* 4,96, *milliards* 3,84 (vocabulaire de fond). C'est une statistique
descriptive utile en soi pour caractériser le « régime médiatique » d'un thème.

**Le χ²/ddl est une échelle de lecture.** Autour de 1, la NB décrit correctement
les comptages (8 mots non rejetés : *algérie*, *francs*, *internet*, *covid*,
*vaccin*, *ukraine*, *gaza*, *intelligence artificielle*). Nettement au-dessus,
la fenêtre mélange des **régimes** : les pires cas sont les présidents observés à
cheval sur leur élection (*chirac* 4,19, *mitterrand* 3,44) et *attentats* (2,90).
Un χ²/ddl élevé est donc déjà un indice de rupture — mais un indice seulement.

**Le piège est dans l'autre sens.** *macron* 2014–2025 : χ²/ddl = 0,98, adéquation
parfaite… alors que la série contient l'une des plus grosses ruptures du corpus
(§4). Un mélange de deux NB ressemble à une NB : le test d'adéquation regarde
l'histogramme des comptages, **pas leur ordre temporel**. Retenir : *l'adéquation
est un diagnostic de forme, jamais un test de stabilité.*

---

## 2. La question du mémoire, et ce que la littérature médias fait attendre

Notre question — *les rachats de journaux modifient-ils la couverture ?* — se
formalise ainsi : après un rachat, les paramètres (μ = fréquence moyenne,
r = régularité) de certains mots changent-ils, **au-delà de ce que l'actualité
impose à tous les journaux** ? Trois études de référence calibrent nos attentes :

- **Martin & McCrain (2019, APSR)** : les stations de télé locales rachetées par
  Sinclair augmentent d'environ 25 % leur couverture de politique nationale au
  détriment du local, avec glissement idéologique — mesuré en
  différence-de-différences contre les stations non rachetées des mêmes marchés.
  C'est le design que nous transposerons.
- **Cagé, Hengel, Hervé & Urvoy (2022)** : après le rachat de Canal+/CNews par
  Bolloré (2015), la part d'antenne de l'extrême droite triple — mais l'effet met
  **des années** à se déployer. Il faut donc tester la date du rachat *et*
  rechercher la vraie date de basculement.
- **Garz & Ots (2025, J. of Communication)** : 108 journaux suédois, 2 M
  d'articles ; la consolidation homogénéise le contenu (moins de local, plus de
  contenu partagé) — des effets de *composition* thématique, précisément ce que
  mesurent nos fréquences de mots.

Conclusion d'étape : les effets existent, sont de l'ordre de quelques dizaines de
pourcents sur la composition, sont progressifs, et ne s'identifient proprement que
**par comparaison à des témoins**.

---

## 3. Panorama des modèles de rupture, et choix motivé

Quatre familles dominent la littérature (revue générale : Truong, Oudre & Vayatis
2020).

**3.1 Économétrie des ruptures structurelles.** Le test de Chow (1960) compare
avant/après une date *connue* — c'est notre situation « rachat », et notre LRT en
est la version comptage. Quand la date est *inconnue*, **Andrews (1993)** montre
que le max des statistiques de test sur toutes les dates (sup-Wald/sup-LR) ne suit
plus un χ² mais une loi non standard (fonctionnelle de ponts browniens), tabulée
avec un rognage des bords — d'où, chez nous, la calibration par simulation, qui
joue le même rôle sans asymptotique. **Bai & Perron (1998, 2003)** généralisent aux
ruptures multiples : estimation des dates par programmation dynamique, test
séquentiel « ℓ contre ℓ+1 ruptures ». Notre segmentation binaire en est la version
simple ; leur cadre justifie aussi l'usage d'un critère type BIC.

**3.2 Segmentation en traitement du signal.** Le CUSUM de Page (1954) cumule les
écarts à la moyenne ; la segmentation binaire coupe au max puis récurse ; **WBS**
(Fryzlewicz 2014) et **NOT** (Baranowski et al. 2019) tirent des sous-intervalles
aléatoires pour ne pas rater les ruptures rapprochées ; la **seeded binary
segmentation** (Kovács et al. 2023) rend cela déterministe et rapide ; **PELT**
(Killick et al. 2012) trouve l'optimum global d'un coût pénalisé en temps linéaire.
Tout cela est implémenté dans le package Python `ruptures` — c'est l'outil
industriel quand on passera à des milliers de séries, à condition de lui donner un
**coût adapté aux comptages** (log-vraisemblance NB avec exposition $N_t$), pas un
coût gaussien sur $f_t$.

**3.3 Séries temporelles de comptage.** Notre famille naturelle : les modèles
INGARCH/autorégression Poisson (Fokianos et al.) font dépendre l'intensité du jour
des comptages passés, et la littérature de rupture associée (Franke, Kirch &
Tadjuidje Kamgaing 2012 ; tests CUSUM sur résidus ou scores, QMLE Poisson/NB —
revue : Lee & Kim 2020) teste les changements de paramètres *en tenant compte de la
dépendance*. C'est la réponse « lourde » au problème d'autocorrélation du §5 ; nous
lui préférons d'abord un correctif plus simple (agrégation + calibration sous
dépendance), quitte à y revenir si nécessaire.

**3.4 Bayésien en ligne.** BOCPD (Adams & MacKay 2007) maintient à chaque instant
la loi a posteriori du « temps écoulé depuis la dernière rupture ». Idéal pour du
monitoring en flux (notre pipeline quotidien pourrait l'utiliser un jour pour
alerter), moins pour l'inférence rétrospective contrôlée dont le mémoire a besoin.

**3.5 Et les ruptures *sémantiques* ?** Kulkarni et al. (2015) détectent les
changements d'usage d'un mot en construisant trois séries temporelles — fréquence,
syntaxe, voisinage distributionnel (embeddings) — puis en y appliquant un test de
rupture avec bootstrap. Hamilton et al. (2016) et la campagne SemEval 2020
(Schlechtweg et al.) fournissent lois empiriques et cadre d'évaluation. Nos
fréquences sont donc *la première* des séries de Kulkarni : la machinerie de
rupture qu'on valide ici resservira telle quelle sur des séries d'embeddings.

**Choix pour le mémoire.** Modèle de bruit : NB avec exposition $N_t$ (imposé par
§1). Test : LRT segmenté — à date connue (rachat) puis scanné (date de basculement
réelle) — soit exactement le sup-LR d'Andrews en version comptage ; ruptures
multiples par segmentation binaire aujourd'hui, PELT+coût NB à l'échelle. Seuils :
**toujours par simulation** (asymptotiques non standard + dépendance, §5).
Identification causale : **par comparaison entre journaux** (§6), à la Martin &
McCrain.

---

## 4. Premiers tests sur nos données : le modèle marche

*(Scan sur coupures mensuelles ; seuils = quantile 95 % du max sous H0, simulé ;
estimation μ par quasi-vraisemblance et r par profil — valeurs légèrement
différentes des fiches, conclusions identiques.)*

**(A) Date connue — *macron*, élection du 7 mai 2017.** LRT = **2 574** (seuil χ²(2)
à 5 % : 5,99 ; p ≈ 0). μ passe de 13,7 à 39,8 pour 10⁵ (×3) et r de 0,35 à 2,49
(×7) : le candidat couvert par rafales devient un président couvert en continu. La
rupture porte sur les *deux* paramètres — μ dit « combien », r dit « comment ».

**(B) Date inconnue — scan calibré.** Sur *chirac* 1986–2007 : rupture au
**1ᵉʳ septembre 1994** (M = 494 contre q95 simulé = 11,8) — la rentrée de
pré-campagne, pas l'élection : la couverture bascule avant l'événement
institutionnel. Sur *covid* 2020–2024 (NB « non rejetée » par le χ², 0 jour
anormal) : rupture au **1ᵉʳ mars 2022** (M = 1 728, q95 = 10,7), la fréquence
divisée par 5 quand l'invasion de l'Ukraine chasse l'épidémie de l'agenda —
deuxième démonstration que l'adéquation ne teste pas la stabilité. Détail
instructif : sous H0, le max *médian* du scan vaut déjà ~6,5, au-dessus du seuil
naïf de 5,99 — quiconque scanne sans corriger la multiplicité des dates fabrique
des découvertes.

**(C) Ruptures multiples — *terrorisme* 1970–2024** (segmentation binaire, seuil
BIC ≈ 29,5) : sept ruptures, toutes avec LRT de 65 à 1 630 :

| segment | μ̂ (10⁵) | lecture |
|---|---|---|
| 1970 → 06/1972 | 1,4 | avant Munich |
| 07/1972 → 09/1977 | 2,4 | Munich, années de plomb |
| 10/1977 → 09/1987 | 6,5 | automne allemand, vague de Paris 1985–86 |
| 10/1987 → 06/2001 | 3,2 | reflux des années 1990 |
| 07/2001 → 12/2001 | **31,2** | 11-Septembre (×10) |
| 2002 → 09/2006 | 12,6 | après-11-Septembre, Irak |
| 10/2006 → 03/2018 | 6,9 | dont la vague 2015–2016 |
| 04/2018 → 2024 | 4,4 | reflux post-Daech |

La machine ne connaît ni Munich ni le Bataclan et retrouve pourtant la chronologie
qu'écrirait un historien des médias. Mais attention : sur un seul journal, une
rupture de fréquence peut refléter le *monde* (plus d'attentats) autant que la
*ligne éditoriale*. D'où le §6.

---

## 5. L'objection sérieuse : les jours ne sont pas indépendants

Tout ce qui précède calibre les seuils en simulant des jours **indépendants**. Or
un sujet chaud reste chaud : si *retraites* sature le journal lundi, il le sature
encore mardi. Cette persistance viole l'hypothèse et, si on l'ignore, **gonfle les
faux positifs** — le scan prend une vague d'actualité pour une rupture.

**T1 — mesure du problème.** ACF(1) = corrélation des résidus de Pearson d'un jour
au suivant, sur des segments *sans* rupture détectée :

| segment | ACF(1) jour | ACF(1) hebdo |
|---|---|---|
| macron avant 05/2017 | 0,79 | 0,81 |
| macron après 05/2017 | 0,63 | 0,73 |
| covid avant 03/2022 | 0,79 | 0,92 |
| covid après 03/2022 | 0,50 | 0,83 |
| terrorisme 2006–2018 | 0,50 | 0,64 |
| europe 2010–2019 | 0,21 | 0,49 |
| milliards 2010–2019 | 0,34 | 0,69 |

La dépendance est forte, et sur les mots « à vagues » (covid, macron) elle
**survit à l'agrégation hebdomadaire** : ce ne sont pas des rafales de deux jours
mais des cycles d'agenda de plusieurs semaines. (Cycles que modélisent précisément
les INGARCH du §3.3.)

**T2 — conséquence quantifiée.** On simule des séries *sans aucune rupture* mais
avec une intensité persistante (log-AR(1)), calées sur un mot réel, et on les fait
passer au scan quotidien calibré iid : au lieu de 5 % de fausses détections, on en
obtient **26 %** avec une persistance modérée (ACF(1) ≈ 0,22) et **51 %** avec
ACF(1) ≈ 0,39 — et nos ACF réelles sont *au-dessus*. Verdict sans appel : **le
scan quotidien calibré iid est inutilisable tel quel** ; nos M gigantesques (494,
1 728) y survivent, mais des M de l'ordre de 20–50 ne prouveraient rien.

**T3 — correctifs.** (i) *Agrégation hebdomadaire* : la dépendance courte
s'évanouit — sous persistance quotidienne φ = 0,5, la taille du scan hebdo calibré
iid retombe à **8 %** (contre 51 % en quotidien). Et le signal survit : sur *covid*
hebdo, M = 354 contre q95 = 11,7. (ii) Pour la dépendance *longue* des mots à
vagues, l'agrégation ne suffit pas : il faut calibrer les seuils en simulant une
intensité persistante estimée (comme en T2) ou par bootstrap de blocs (Künsch
1989), les blocs devant couvrir la durée d'un cycle d'agenda (plusieurs semaines).
(iii) La parade la plus robuste est structurelle : passer à la *part* entre
journaux, car la persistance d'agenda est **commune** aux journaux et s'annule
dans la comparaison — §6. Nota : la date estimée peut dépendre du grain (covid :
03/2022 en quotidien, 02/2023 en hebdo) — quand une série contient plusieurs
ruptures, un modèle à une seule coupure choisit le meilleur compromis ; la
segmentation multiple lève l'ambiguïté.

---

## 6. Le design décisif : la part entre journaux (diff-in-diff)

**L'idée.** Conditionnellement au total des occurrences des deux journaux une
semaine donnée ($n_w = x^{Monde}_w + x^{Figaro}_w$), si les deux suivent la même
actualité avec des « appétits » constants, la part du Monde
$x^{Monde}_w \sim$ Binomiale$(n_w, p)$ avec $p$ **constant** — quelle que soit la
violence des vagues d'actualité, qui n'affectent que $n_w$. Une rupture sur $p$
est donc un déplacement **relatif** d'agenda : exactement la signature d'un
changement éditorial, purgée de l'actualité commune. (Surdispersion résiduelle :
bêta-binomiale segmentée, scan LRT calibré par simulation, données hebdomadaires.)
C'est la transposition à nos comptages du design de Martin & McCrain.

**Validation sur un choc d'actualité pur — *ukraine* 2021–2023.** Chaque journal
pris séparément explose en février 2022 (M marginaux : 247 pour Le Monde, 211 pour
Le Figaro). La part, elle, bouge à peine : **0,44 → 0,45**. Le design fait
exactement ce qu'on attend : il **absorbe l'invasion**. (Le scan de la part reste
formellement significatif — M = 51 > q95 = 10,8 — mais pour un déplacement d'un
point : avec des dizaines de milliers d'occurrences, tout est « significatif » ;
c'est l'*ampleur* qui doit porter l'interprétation. Le mémoire rapportera
systématiquement taille d'effet et intervalle, pas seulement la p-valeur.)

**Les cinq tests (part = part du Monde ; « volumes » = part du Monde dans le
total des mots publiés, avant → après la date détectée) :**

| mot, fenêtre | part avant → après | date détectée | M / q95 | volumes |
|---|---|---|---|---|
| ukraine 2021–23 | 0,44 → 0,45 | 26/09/2022 | 51 / 10,8 | 0,43 → 0,41 ✓ |
| retraites 2022–23 | 0,40 → 0,43 | *(2023-02)* | **8 / 8,3 : non significatif** | 0,45 → 0,41 |
| climat 2005–23 (brut) | 0,89 → 0,53 | 06/03/2006 | 675 / 13,7 | **0,91 → 0,43 ⚠** |
| climat 2007–23 (purgé) | 0,52 → 0,57 | 09/08/2021 | 22 / 11,9 | 0,42 → 0,43 ✓ |
| immigration 2007–23 | **0,52 → 0,36** | 04/08/2014 | 125 / 9,7 | 0,43 → 0,42 ✓ |

Quatre enseignements :

1. ***retraites* est le placebo réussi** : pendant la réforme de 2023, chaque
   journal explose (M marginaux 61 et 53) mais la part ne bouge pas
   significativement (M = 8 < q95). Le design absorbe le plus gros choc
   d'actualité sociale de la période — c'est exactement ce qu'on lui demande.
2. ***climat* brut illustre le garde-fou des volumes** : la « rupture » géante de
   mars 2006 (part 0,89 → 0,53) coïncide avec un effondrement de la part de
   *volume* (0,91 → 0,43) : c'est la montée en charge du corpus Figaro, un
   artefact de collecte, pas un fait éditorial. Sans le contrôle, on aurait
   publié un faux résultat. Toute rupture de part devra passer ce filtre.
3. ***climat* purgé (2007–2023)** : petite rupture robuste au **9 août 2021 — le
   jour de la publication du 6ᵉ rapport du GIEC** : Le Monde gagne ~5 points de
   part, volumes stables. Un déplacement relatif d'agenda, modeste mais daté au
   jour près sur un événement identifiable : le niveau de finesse dont le mémoire
   a besoin.
4. ***immigration* est le cas d'école du signal éditorial différentiel** : à
   l'été 2014, la part du Monde passe de 0,52 à **0,36** (−16 points, M = 125,
   volumes stables) — le Figaro investit massivement le thème, en termes
   *relatifs*, avant même la crise migratoire de 2015 (contexte : lancement de
   FigaroVox début 2014). Le quantitatif localise et mesure ; l'attribution
   causale (stratégie éditoriale ? nouveau format opinions ?) relèvera de
   l'histoire des médias — même division du travail pour les rachats.

**Garde-fous du design.** (i) Contrôler que la rupture de part ne coïncide pas
avec un changement de *volume* d'un des journaux (pagination, panne de collecte) —
colonne « volume » ci-dessus : la part des volumes $N^{Monde}/(N^{Monde}+N^{Figaro})$
doit rester stable au voisinage de la date détectée. (ii) Utiliser plusieurs
témoins (Échos aujourd'hui, autres médias demain) plutôt qu'un seul. (iii) Sur des
centaines de mots testés, corriger la multiplicité (Benjamini-Hochberg).

---

## 7. Dimensionner le protocole : la puissance

Simulation du test à date connue (design rachat), données hebdomadaires, rupture
au milieu de la fenêtre, mot de fréquence moyenne (μ = 10/10⁵, soit ~14 occ./jour
dans Le Monde actuel) :

| fenêtre | burstiness hebdo | +10 % | +20 % | +30 % | +50 % |
|---|---|---|---|---|---|
| ±1 an (104 sem.) | forte (r = 3) | 13 % | 30 % | 50 % | 86 % |
| ±1 an (104 sem.) | faible (r = 10) | 25 % | 68 % | 95 % | 100 % |
| ±2 ans (208 sem.) | forte (r = 3) | 14 % | 52 % | 81 % | 100 % |
| ±2 ans (208 sem.) | faible (r = 10) | 42 % | 96 % | 100 % | 100 % |

Trois conclusions de dimensionnement. (i) **Un déplacement de 10 % est hors de
portée** au niveau d'un mot isolé (13–42 % de puissance) : inutile d'espérer
détecter des inflexions subtiles mot par mot. (ii) **Les effets de l'ordre
documenté par la littérature (20–30 %) sont détectables avec ±2 ans de données**,
surtout si la burstiness est modérée (52–100 %). (iii) **La burstiness coûte très
cher** (à +20 % : 96 % de puissance si r = 10, 52 % si r = 3) : d'où l'intérêt
d'agréger les mots en *paniers thématiques* (la somme de comptages de mots liés
lisse les rafales individuelles et augmente la fréquence totale) — c'est ainsi
qu'on gagnera la puissance qui manque aux mots isolés.

---

## 8. Protocole recommandé pour le mémoire

1. **Grain hebdomadaire**, fenêtres de ±1 à ±3 ans autour de chaque rachat
   (compromis puissance / risque d'autres ruptures dans la fenêtre).
2. **Panier de mots par rachat** : mots à enjeu éditorial (politiques, sociétaux)
   + mots de contrôle « neutres » ; fréquence minimale ~2/10⁵ (puissance, §7).
3. **Trois tests par mot**, du plus au moins identifié : (a) rupture de **part**
   vs journaux témoins à la date du rachat (LRT bêta-binomial) — le test principal ;
   (b) scan de la part (date de basculement réel, cf. effets progressifs de Cagé
   et al.) ; (c) NB marginale en appoint descriptif (μ, r par segment).
4. **Seuils par simulation** systématiquement ; sous dépendance résiduelle,
   bootstrap de blocs ; **Benjamini-Hochberg** sur l'ensemble mots × rachats.
5. **Rapporter les ampleurs** (Δ part, Δμ en %, avec intervalles bootstrap), pas
   seulement les p-valeurs.
6. Garde-fous : contrôle des volumes, placebo temporel (fausses dates de rachat
   sur les témoins → taux de détection ≈ taille nominale), placebo lexical (mots
   neutres).
7. À l'échelle (tous les mots du vocabulaire) : PELT avec coût NB/bêta-binomial
   via `ruptures`, puis tri des découvertes par FDR et ampleur.

## 9. Limites et suite

- **Fréquence ≠ sens** : un journal peut parler autant d'un thème en en parlant
  autrement. Étape suivante : les trois séries de Kulkarni et al. (fréquence,
  syntaxe, embeddings) sur nos corpus — la machinerie de test validée ici s'y
  applique inchangée.
- **Polysémie et OCR** : *hollande*, *jeux*, graphies à sommer — le niveau bigramme
  (« réforme des retraites ») réduit l'ambiguïté au prix de la fréquence.
- **$N_t$ change de nature** sur longue période (pagination, suppléments, web) :
  la part entre journaux y est plus robuste que la fréquence marginale, mais le
  contrôle des volumes reste obligatoire.
- **Une rupture n'a pas de cause inscrite dedans** : même en DiD, il faudra
  documenter qualitativement chaque rachat (changement de direction, de
  rédaction en chef) pour l'attribution — le quantitatif localise et mesure,
  l'histoire des médias explique.

---

## Références

**Statistique des ruptures.** Page (1954), *Continuous inspection schemes*,
Biometrika 41 · Chow (1960), Econometrica 28 · Andrews (1993), *Tests for
parameter instability with unknown change point*, Econometrica 61(4)
· Bai & Perron (1998), *Estimating and testing linear models with multiple
structural changes*, Econometrica 66(1) ; (2003) J. Applied Econometrics 18
· Killick, Fearnhead & Eckley (2012), *Optimal detection of changepoints with a
linear computational cost*, JASA 107 — [arXiv:1101.1438](https://arxiv.org/abs/1101.1438)
· Fryzlewicz (2014), *Wild binary segmentation*, Ann. Statist. 42
· Baranowski, Chen & Fryzlewicz (2019), *Narrowest-over-threshold detection*, JRSS-B 81
· Kovács, Bühlmann, Li & Munk (2023), *Seeded binary segmentation*, Biometrika 110 —
[arXiv:2002.06633](https://arxiv.org/abs/2002.06633)
· Truong, Oudre & Vayatis (2020), *Selective review of offline change point
detection methods*, Signal Processing 167 — [arXiv:1801.00718](https://arxiv.org/abs/1801.00718)
· Adams & MacKay (2007), *Bayesian online changepoint detection* —
[arXiv:0710.3742](https://arxiv.org/abs/0710.3742)
· Künsch (1989), *The jackknife and the bootstrap for general stationary
observations*, Ann. Statist. 17.

**Séries de comptage.** Franke, Kirch & Tadjuidje Kamgaing (2012), *Changepoints
in times series of counts*, J. Time Series Analysis 33 · Fokianos et al., modèles
INGARCH/autorégression Poisson · Lee & Kim (2020), *Recent progress in parameter
change test for integer-valued time series models*, J. Korean Statist. Soc. 49 —
[lien](https://link.springer.com/article/10.1007/s42952-020-00102-4)
· Diop & Kengne (2021), *Poisson QMLE for change-point detection in general
integer-valued time series*, Metrika — [arXiv:2007.13858](https://arxiv.org/pdf/2007.13858).

**Statistique textuelle.** Church & Gale (1995), *Poisson mixtures*, Natural
Language Engineering 1(2) —
[lien](https://www.cambridge.org/core/journals/natural-language-engineering/article/abs/poisson-mixtures/52E7F9429D0EC03EEC6674E071727B64)
· Katz (1996), *Distribution of content words and phrases…*, NLE 2(1)
· Kulkarni, Al-Rfou, Perozzi & Skiena (2015), *Statistically significant
detection of linguistic change*, WWW — [arXiv:1411.3315](https://arxiv.org/abs/1411.3315)
· Hamilton, Leskovec & Jurafsky (2016), *Diachronic word embeddings reveal
statistical laws of semantic change*, ACL — [arXiv:1605.09096](https://arxiv.org/abs/1605.09096)
· Schlechtweg et al. (2020), *SemEval-2020 Task 1: Unsupervised lexical semantic
change detection* — [arXiv:2007.11464](https://arxiv.org/abs/2007.11464)
· Azoulay & de Courson (2023), *Gallicagram*, Corpus 24 —
[lien](https://journals.openedition.org/corpus/7944).

**Économie des médias.** Martin & McCrain (2019), *Local news and national
politics*, American Political Science Review 113(2) —
[lien](https://ideas.repec.org/a/cup/apsrev/v113y2019i02p372-384_00.html)
· Cagé, Hengel, Hervé & Urvoy (2022), *Hosting media bias: evidence from the
universe of French broadcasts 2002–2020* —
[PDF](https://juliacage.com/wp-content/uploads/2022/02/Hosting-Media-Bias-Cage%CC%81-Hengel-Herve%CC%81-Urvoy-2022_02_16.pdf)
· Garz & Ots (2025), *Media consolidation and news content quality*, Journal of
Communication 75(3) — [lien](https://academic.oup.com/joc/article/75/3/195/7978978).
