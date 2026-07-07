# Prospection nouveaux médias — candidats (nuit du 06→07/07/2026)

Objectif : enrichir le registre MEDIAS en priorisant le moteur « basic » (requête HTTP simple).
Règle absolue : jamais d'articles tronqués en base — un média part en « basic complet »,
« gratuits seuls » (filtre free) ou est écarté. Rien n'est branché sans validation de Corto.

## Priorités (pertinence mémoire × probabilité basic)

| # | Média | Propriétaire / rachat | Intérêt mémoire | Accès pressenti | Statut |
|---|---|---|---|---|---|
| 1 | cnews.fr | Bolloré (Canal+) | ★★★ cas d'école ligne éditoriale | gratuit | ✅ **basic complet** (dossier cnews.md) |
| 2 | 20minutes.fr | Rossel + Ouest-France | ★★ | gratuit intégral | ✅ **basic complet** (20minutes.md) |
| 3 | leprogres.fr | EBRA (Crédit Mutuel, rachats 2007-2010) | ★★★ | freemium | ✅ **gratuits seuls, filtre free** (leprogres.md) — part de gratuit par époque à sonder |
| 4 | closermag.fr | Reworld Media (rachat Mondadori 2019) | ★★★ machine à rachats | gratuit | ⚠️ **basic complet SOUS RÉSERVE** (closermag.md) — archives ≤2009+ vidées par Reworld, frontière à sonder |
| 5 | actu.fr | Publihebdos (Ouest-France) | ★★ | gratuit | réserve |
| 6 | lavoixdunord.fr | Rossel | ★★ | freemium | réserve |
| 7 | europe1.fr | Lagardère → Vivendi/Bolloré (2021) | ★★★ | gratuit | réserve |
| 8 | huffingtonpost.fr | groupe Le Monde | ★ | gratuit | réserve |
| 9 | slate.fr | indépendant | ★ (témoin) | gratuit | réserve |
| 10 | franceinfo.fr | service public | ★ (témoin/contrôle) | gratuit | réserve |

Déjà écartés par le passé : lexpress (pas de corps json-ld exploitable), lepoint (rendu JS).

## Méthode par candidat (équipe d'agents)

1. **mapping** : source d'URLs (sitemap/archives/pagination), profondeur historique, échantillon
   de ~10 URLs variées (époques + rubriques, gratuits ET payants).
2. **scrapper** : HTML de l'échantillon via le moteur basic, sur gallica uniquement ; verdict
   par URL : complet / tronqué / vide.
3. **explorateur** : localisation de titre/auteur/date/corps (json_ld en priorité, sinon balises).
4. **manager** : croise les trois rapports → ajoutable basic complet / gratuits seuls / écarté ;
   si ajoutable, fait préparer mapping_<media>.py + l'entrée medias.py SANS brancher.

Les dossiers individuels sont dans ce même dossier : `<media>.md`.
