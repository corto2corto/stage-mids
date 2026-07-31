# Campagne PCA 48 h — suivi

## Prompt de reprise (coller tel quel dans une nouvelle session Claude)

> Reprends la campagne PCA 48 h. Lis `campagne_pca/plan.md` puis ce fichier
> (`campagne_pca/suivi.md`) en entier, vérifie l'état des tmux sur gallica
> (`ssh gallica 'tmux ls'`), récolte les résultats
> (`scp gallica:/data/elias/stage-mids/data/campagne/resultats.csv campagne_pca/`),
> consigne ici, puis continue le programme du plan en réarmant la boucle de
> réveils (~20-30 min). Autorisation 48 h donnée le 31/07/2026 : jobs serveur
> en tmux dédié + git en autonomie, fin le 02/08 ~18h (Paris). Surveiller la
> charge serveur (pause de la file si load > 16).

## État courant (mis à jour à chaque réveil)

- **Phase** : salve 2 en cours (31/07 ~18h45) — re-balayage complet avec
  témoin nul, 660 configs (lemonde s4-6, lefigaro/lesechos s3-6, 3 grilles
  chacun) dans `campagne_pca2` ; pics s3 lemonde dans `campagne_s3` ;
  base + chaîne Mediapart dans `campagne_mediapart`.
- **Fait** : salve 1 récoltée et analysée (voir journal) ; chaînes Figaro et
  Échos terminées (grilles + pics s3, 1-2 min par pics_masse : leurs grilles
  font 6 764 et 10 381 jours) ; vocabulaires Figaro/Échos classés (+2 861
  mots) ; témoin nul ajouté au runner.
- **À faire au prochain réveil** : récolter salves 3b+4 et chaîne 40k puis
  **lancer salve 5** (`campagne_pca/salve5_40k_log.sh`, prête et déployée :
  balayage 40k plein n + n apparié, 288 configs ~2-3 h à cause du npz de
  4,2 Go, plus 24 configs de jauge --log). Vocab 40k classé et committé
  (+25 697 mots, 4 298 noms propres ; audit de 1 889 cas non arbitré —
  queue de vocabulaire quasi entièrement commune, biais mineur accepté sur
  le filtre noms_propres 40k). Ensuite : analyse à n apparié de salve 4
  (le comparatif d'axes propre).
- **Idées en réserve (jour 2)** : variante log (« PCA avec le log » des
  notes d'appel — fenêtres en log(f_t+ε) avant z-score, à ajouter au
  runner) ; inspection des composantes des configs gagnantes (figures) ;
  kernel PCA si le temps le permet ; synthèse finale en PDF.

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
  336 autres → `campagne_pca/vocab_categories.csv` (committé, lu par le
  serveur).
- **Fait notable** : le top-10k par jours actifs (coupe 7 121 j) exclut les
  mots récents — macron, covid, trump n'y sont pas. Le filtre noms_propres
  ne contient que des noms installés dans la durée. La variante ≥ 1 000
  jours actifs (39 316 mots, déjà notée au to_do) lèverait ça — candidate
  pour la nuit 2.
- **Teaser** (validation locale) : filtre noms_propres seul → cum6 41,5 %
  (gain6 2,08) contre 33,3 % (1,66) en référence — mais 9 647 fenêtres
  contre 121 805. À confirmer/croiser en salve 1.
- Données lemonde rapatriées en local (`campagne_pca/data_local/`, hors git)
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
