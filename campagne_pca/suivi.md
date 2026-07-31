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

- **Phase** : salve 1 en cours de lancement (31/07 ~18h30).
- **Tmux campagne sur gallica** : `campagne_pca` (balayage 180 configs),
  `campagne_figaro` et `campagne_echos` (chaînes complètes, s3, dont grilles
  3j/7j) — à vérifier au prochain réveil.
- **Configs évaluées** : 0 côté serveur (validation locale : 3).
- **En attente de lancement** : pics_masse lemonde s3, base Mediapart,
  catégories vocab Figaro/Échos (après leurs masse.py), variante vocab
  ≥ 1 000 jours actifs (idée jour 2, cf. to_do « comparaison à faire »).

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
