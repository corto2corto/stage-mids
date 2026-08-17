# Prospection nouveaux médias — candidats (nuit du 06→07/07/2026)

Objectif : enrichir le registre MEDIAS en priorisant le moteur « basic » (requête HTTP simple).
Règle absolue : jamais d'articles tronqués en base — un média part en « basic complet »,
« gratuits seuls » (filtre free) ou est écarté. Rien n'est branché sans validation de Corto.

## Priorités (pertinence mémoire × probabilité basic)

| # | Média | Propriétaire / rachat | Intérêt mémoire | Accès pressenti | Statut |
|---|---|---|---|---|---|
| 1 | cnews.fr | Bolloré (Canal+) | ★★★ cas d'école ligne éditoriale | gratuit | ✅ **branché en prod** (15/07/2026, fiche `cnews` dans `mapping/catalogue.py` + `scraping/medias.py`) |
| 2 | 20minutes.fr | Rossel + Ouest-France | ★★ | gratuit intégral | ✅ **branché en prod** (15/07/2026, fiche `20minutes` dans `mapping/catalogue.py` + `scraping/medias.py`) |
| 3 | leprogres.fr | EBRA (Crédit Mutuel, rachats 2007-2010) | ★★★ | freemium | candidat potentiel — validé basic « gratuits seuls » en 07/2026, fiche `leprogres` prête dans `mapping/catalogue.py`, non branché ; part de gratuit par époque à sonder avant branchement |
| 4 | closermag.fr | Reworld Media (rachat Mondadori 2019) | ★★★ machine à rachats | gratuit | candidat potentiel — validé basic sous réserve en 07/2026, fiche `closermag` prête dans `mapping/catalogue.py`, non branché ; frontière du re-templating Reworld (mai 2023) à sonder avant branchement |
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
   si ajoutable, fait préparer la fiche du média dans `mapping/catalogue.py`
   (mapping) + l'entrée `scraping/medias.py` (scrapping) SANS brancher.

Les anciens dossiers détaillés par média (cnews.md, 20minutes.md, leprogres.md,
closermag.md) ont été supprimés une fois leurs conclusions reprises ci-dessus
et dans `journal.md` (§ Prospection de nouveaux médias) ; le détail technique
(smoke-tests, motifs regex) reste consultable via `git log -- exploration/prospection/`.
