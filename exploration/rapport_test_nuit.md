# Rapport — nuit de validation scrapping_v2 (06→07/07/2026)

Rédigé par Claude après le run de validation de 2 h et les tests complémentaires de la nuit.
Tout s'est déroulé sur la branche `scrapping_v2`, le clone `/data/elias/stage-mids-v2` et la
base de test isolée `exploration/test_run_grp/` — `main` et la prod n'ont pas été touchés.

## 1. Résumé exécutif

Le pipeline v2 (une boucle indépendante par média, 30 threads) est **fonctionnellement validé** :
run de 2 h sans incident (0 blocage BDD, 0 thread mort, RAM stable), **29 236 articles écrits**
(33 762 URLs traitées sur 48 500), intégrité CSV↔base parfaite, reprise après crash propre.
Débit global observé : **~280 URLs/min soutenus** (~×10 vs la v1 en vagues dans les mêmes
conditions de serveur chargé). Trois dossiers restent ouverts (Libération archives, latribune,
extraction bfmtv/atlantico) — aucun n'est bloquant pour le merge, tous sont documentés ci-dessous
avec recommandation.

## 2. Conditions et chiffres du run de référence

- Démarrage 22:19, scraping effectif 22:24 → 00:24 (plafond 2 h du pipeline).
- 30 médias, 48 500 URLs tirées aléatoirement (2 200/basic, 800/firefox, 600 le_monde,
  300 mediapart — seule source disponible pour lui).
- Réglages testés : politesse basic **1 s**, attente firefox **4 s**, log **3 s**,
  `pageLoadStrategy: eager`, `page_load_timeout` 30 s, WAL + `synchronous=NORMAL`.
- Ouverture des sessions : logs d'abord au calme (**2/2 du premier coup**, 129 s), meute
  firefox+basic ensuite (124 s). Un seul login le_monde/mediapart pour toute la nuit.
- Serveur partagé et chargé pendant tout le run (autre utilisateur : 4 process ~5 cœurs,
  disque de données `vdb` vu à 109 % d'utilisation au pic) : load1 moyen 35,9 (max 65),
  iowait moyen 37 %. C'est l'état « normal » du serveur acté par Corto.

### Bilan par média (extrait — tableau complet dans le dépouillement en annexe du run)

| Média (moteur) | ok | ko | taux | URLs/min | commentaire |
|---|---|---|---|---|---|
| voici, francesoir, le_capital, marianne, bfmtv, jdd, ouest_france (basic) | 1 488-1 529 | 0-2 | ~100 % | ~13 | parfaits |
| la_croix, la_depeche, midilibre, leparisien, gala (basic) | 1 391-1 504 | 3-54 | 97-99 % | 12-13,5 | parfaits |
| challenges, l_opinion, latribune, laprovence (basic) | 1 261-1 425 | 146-750 | 63-90 % | 12-18 | échecs = payants filtrés (+ latribune : cf. §4.2) |
| paris_normandie (basic) | 342 | 298 | 53 % | 5,5 | site lent (~3 s/req) + payants |
| liberation (basic) | 67 | 2 133 | 3 % | — | archives tronquées côté serveur : cf. §4.1 |
| paris_match, valeurs_actuelles, le_telegramme, nice_matin, les_echos (firefox) | 612-757 | 8-61 | 92-99 % | 5,4-6,6 | sains, proches du plafond attente 4 s |
| le_figaro (firefox) | 532 | 81 | 87 % | 5,3 | bon (bypass premium OK à ~87 %) |
| atlantico, sud_ouest (firefox) | 291-380 | 101-124 | 70-79 % | 3,6-4,1 | ~9-21 % de requêtes ≥29 s (anti-bot, cf. §4.4) |
| telerama, le_nouvel_observateur (firefox) | 211-224 | 38-113 | 65-86 % | 2,2-2,8 | 27-41 % de requêtes ≥29 s (anti-bot, cf. §4.4) |
| le_monde (log) | 321 | 60 | 84 % | 3,3 | 26 % de chargements ≥29 s ; 8 rafales d'échecs corrélées à la charge |
| mediapart (log) | 292 | 8 | 97 % | 6,2 | aucune rafale cette nuit ; articles très riches (médiane 9 648 car.) |

### Qualité des données écrites

- **Intégrité parfaite** : pour chaque média, lignes CSV = état=2 en base, **0 doublon d'id**.
- Contenus : médianes de 1 100 à 3 900 caractères (mediapart 9 648) ; **0 % de contenu vide** partout.
- Deux trous d'extraction de métadonnées (pas de contenu manquant) : **bfmtv 18 %** et
  **atlantico 7,9 %** de titre+date vides (corrélés ligne à ligne → gabarits sans json-ld
  complet). Cf. recommandation §5-P4.

### Santé serveur sur 2 h (metriques.csv, 115 points)

- RSS cumulée des Firefox : **plateau 4,2-5,1 Go, aucune dérive** → le déchargement
  `about:blank` fait son travail, pas besoin de le conditionner.
- 0 « database is locked » sur tout le run (WAL + timeout 30 s validés sous 30 écrivains).
- iowait moyen 37 % : le disque `vdb` est le facteur limitant global du serveur (cf. §5-P1).

## 3. Tests complémentaires de la nuit

### 3.1 Reprise après interruption brutale (kill -9 en plein run)
Comportement idéal : états en base tous propres, exactement **1 URL « en vol » par média**
(écrite au CSV, état non commité) → re-scrapée à la relance → au plus **1 doublon par média et
par crash**, que `4_marquer_doublons.py` absorbe. La relance via `lancer_grp.sh` a redémarré
seule sur le reliquat. RàS.

### 3.2 Profils Firefox en RAM (`/dev/shm`) — le gros gain disponible
Mesure comparée (2 Firefox, même article, serveur calme) :

| | ouverture 2 FF | 2 pages | empreinte |
|---|---|---|---|
| profils sur `vdb` (actuel) | 119,4 s | 15,9 s | 271 Mo |
| profils sur `/dev/shm` (RAM) | **34,0 s (×3,5)** | **5,2 s (×3)** | 244 Mo |

~122 Mo/profil → ~1,6 Go pour 13 Firefox, sur 20 Go de `/dev/shm` disponibles. Sort les
profils du disque saturé ET réduit notre propre pression dessus. Recommandation P1.

### 3.3 Les sites « anti-bot » ne sont lents que pour Firefox
telerama, le_figaro et le_nouvel_observateur répondent en **0,2-0,7 s** au moteur basic
(curl_cffi, TLS Chrome), HTTP 200 systématique, articles gratuits complets — alors que les mêmes
sites laissent pendre nos Firefox 10-30 s (throttling d'empreinte navigateur, pas d'IP).
Piste « moteur hybride » : basic d'abord, Firefox seulement si `est_bloque` (payant). §5-P5.

### 3.4 Rappels des A/B de la soirée (déjà commités)
- `pageLoadStrategy: eager` : médiane de chargement firefox 3,4 s → 0,8 s ; soigne 7 médias sur 10.
- Timeout 6/10/14/30 s sur les anti-bot : plus court = moins d'articles (à 6 s : zéro) → 30 s conservé.
- Attente firefox 4 s vs 6 s : 0 bloqué BPC à 4 s, ~2 s/URL gagnées → 4 s adopté.
- Coût BDD : 0,004 ms (lecture indexée) + 2,1 ms (écriture WAL) par URL = 0,04 % du cycle
  → aucun besoin de système de file.

## 4. Dossiers ouverts (diagnostics complets)

### 4.1 Libération — les archives sont tronquées côté serveur
Autopsie sur 40 URLs (1997-2023) : toutes les pages embarquent un blob JSON
(`Fusion.globalContent`, CMS Arc) qui contient le corps de l'article… mais pour les articles
`content_restrictions.content_code = "ferme"` (payants), le blob comme le DOM ne contiennent que
**l'extrait avant-paywall (~240 mots, coupé en plein mot)**. Or **14/14 URLs pré-2013 testées
sont « ferme »** ; les « ouvert » (texte complet) n'apparaissent qu'à partir de ~2015-2016.
S'y ajoutent ~30 % de 404 dans les vieilles URLs du mapping. Conclusion : **aucun moteur sans
abonnement ne peut récupérer les archives Libération en texte intégral** — règle « pas de
tronqués » ⇒ soit compte abonné (moteur log), soit restreindre Libération aux articles
« ouvert » récents, soit l'écarter du corpus historique. Décision Corto requise.

### 4.2 latribune — suspicion de rate-limit à politesse 1 s
Taux d'échec 8,7 % (politesse 3 s) → 13,4 % (1 s), +55 % relatif ; seul basic nettement dégradé
(liberation mise à part, cause différente). Recommandation : `attente: 2` pour lui seul. §5-P2.

### 4.3 bfmtv / atlantico — métadonnées incomplètes
18 % / 7,9 % de lignes sans titre ni date (contenu présent) : certains gabarits n'exposent pas
le json-ld attendu. À corriger par un repli `balises` dans `meta` après examen de 2-3 HTML
concernés. §5-P4.

### 4.4 le_monde — rafales d'échecs corrélées à la charge
8 rafales de 3-6 échecs consécutifs sur 381 URLs, surtout aux heures de forte charge ; mediapart
n'en a eu **aucune** cette nuit (la dégradation observée la veille ne s'est pas reproduite sur
un run unique). L'hypothèse « throttling de compte » recule au profit de « pages lentes sous
charge + timeout 30 s » (26 % des chargements le_monde ≥29 s). À réévaluer après P1 (tmpfs) qui
devrait accélérer tous les rendus. Tests dédiés sur comptes : toujours reportés, avec prudence.

## 5. Recommandations (par priorité, code NON appliqué)

### P1 — Profils Firefox en RAM (gain ×3 mesuré, 1 ligne)
```python
# scraping/config.py — remplacer
TMP_FIREFOX = RACINE / "extensions" / "firefox" / "tmp"
# par
TMP_FIREFOX = Path("/dev/shm/stage-mids-firefox-tmp")
```
Et dans `scripts/lancer.sh` (et `exploration/lancer_grp.sh`), aligner `TMP_DIR` sur ce chemin
(les `pkill -f $TMP_DIR` et `find $TMP_DIR -delete` continuent de fonctionner tels quels).
Vigilance : +~1,6 Go de RAM utilisée par la flotte (large marge : 20 Go dispo) ; nettoyé
d'office au reboot.

### P2 — latribune : politesse 2 s
```python
# scraping/medias.py
"latribune": {"moteur": "basic", "attente": 2, "meta": {...inchangé...}},
```
Puis re-vérifier son taux d'échec au prochain run (attendu : retour ~8-9 %).

### P3 — Libération : décision de corpus
Option A (recommandée si pas de compte) : restreindre le mapping aux articles récents et purger
les 404 — filtrer `liberation_url.csv` sur les années ≥2016, et re-vérifier le taux de « ouvert ».
Option B : passer liberation en moteur `log` avec un compte abonné (couvre les archives).
Option C : écarter du corpus historique (le documenter dans le mémoire).

### P4 — bfmtv/atlantico : repli d'extraction
Examiner 2-3 HTML sans titre (les re-télécharger depuis les URLs des lignes fautives), puis
compléter `meta` avec des sélecteurs `balises` de secours (titre `h1`, date `time[datetime]`)
via la stratégie existante — à valider sur HTML réels avant commit.

### P5 — Moteur hybride pour les sites anti-bot (piste, à prototyper)
telerama/le_figaro/le_nouvel_observateur : tenter la page en basic (~0,5 s) ; si `est_bloque`
(payant), la repasser au Firefox bypass. Esquisse : nouveau moteur `"hybride"` dans
`moteurs.py` qui détient les deux sessions et enchaîne basic → firefox en secours. Gain
potentiel : ×5-10 sur les gratuits de ces médias ; coût : une session de plus par média.
À prototyper sur telerama d'abord (part de gratuits la plus forte).

### P6 — Mineurs
- `exploration/preparer_test_grp.py` et la surveillance sont réutilisables tels quels pour
  les prochains tests de charge.
- La surveillance a besoin que `grp.log` existe à son démarrage (course de quelques secondes
  au premier lancement) : créer le fichier dans `lancer_grp.sh` avant le tmux de surveillance,
  ou tolérer son absence dans le script.
- mediapart n'a pas de CSV d'URLs propre (repêché depuis la base xl) : générer un vrai
  `mediapart_url.csv` au prochain mapping.

## 6. Ce qui est prêt pour la discussion de merge

- Architecture boucles par média : validée (2 h, 30 threads, 0 incident, reprise crash OK).
- Réglages actés et mesurés : eager, timeout 30 s, basic 1 s (sauf latribune → P2), firefox 4 s, log 3 s.
- Gains vs v1 : débit global ×~10 sous serveur chargé ; logins fiabilisés (1 tentative/run).
- À trancher par Corto avant ou après merge : P1 (tmpfs — recommandé avant), P3 (Libération),
  et le lancement du chantier P5 (hybride).
- Le critère fixé (« nouveaux médias + gain de vitesse ») est atteint sur le volet vitesse ;
  le volet nouveaux médias fait l'objet de la prospection lancée en fin de nuit (dossier séparé).
