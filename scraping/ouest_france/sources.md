# Titres du groupe dans l'index `articles`

Le champ `source` sépare les 8 titres du groupe SIPA-Ouest-France. Chacun sort
dans son propre CSV, comme les autres médias du pipeline.

| Code | Titre | Volume | CSV |
|---|---|---|---|
| `of` | Ouest-France | 32,8 M | `ouest_france2.csv` |
| `co` | Courrier de l'Ouest | 2,95 M | `le_courrier_de_l_ouest.csv` |
| `po` | Presse Océan | 1,83 M | `presse_ocean.csv` |
| `ml` | Le Maine Libre | 1,48 M | `le_maine_libre.csv` |
| `im` | Le Marin | 84 k | `le_marin.csv` |
| `api` | Agence API | 78 k | `agence_api.csv` |
| `vv` | Voiles et Voiliers | 27 k | `voiles_et_voiliers.csv` |
| `fl` | desk faits divers / insolite | 3,5 k | `ouest_france_fil.csv` |

`ouest_france2` et non `ouest_france` : ce dernier nom est déjà pris par l'autre
chaîne de scraping d'Ouest-France, à ne pas écraser.

`fl` n'a pas de nom public : ses articles paraissent sur ouest-france.fr
(faits divers, insolite) et tous datent de 2026. Gardé à part — on peut toujours
le fusionner avec `ouest_france2` ensuite, l'inverse est plus pénible.

Filtrage : `"filters": "source:co"`.
