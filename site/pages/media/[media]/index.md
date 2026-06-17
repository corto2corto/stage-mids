---
title: "{params.media}"
---

<a href="/">← Retour au tableau de bord</a>

```sql medias
-- Liste des médias : indique à Evidence quelles pages générer
select distinct media from suivi.suivi_journal
```

```sql infos
-- Joli nom du média courant (repli sur le slug si absent de la table)
select coalesce(l.nom, '${params.media}') as nom
from (select '${params.media}' as media) m
left join suivi.libelles l on m.media = l.media
```

# {infos[0].nom}

Détail du scraping pour **{infos[0].nom}**.

```sql etat_courant
-- Dernier instantané pour ce média
select
    reussis,
    echecs,
    reussis + echecs as traites,
    round(100.0 * reussis / nullif(reussis + echecs, 0), 1) as taux_succes
from suivi.suivi_journal
where media = '${params.media}'
order by horodatage desc
limit 1
```

<BigValue data={etat_courant} value=traites title="Articles traités" fmt='#,##0'/>
<BigValue data={etat_courant} value=reussis title="Réussis" fmt='#,##0'/>
<BigValue data={etat_courant} value=echecs title="Échecs" fmt='#,##0'/>
<BigValue data={etat_courant} value=taux_succes title="Taux de réussite" fmt='0.0"%"'/>

## Progression dans le temps

```sql progression
-- Compteurs cumulés au fil des instantanés
select
    horodatage::timestamp as horodatage,
    reussis,
    echecs,
    reussis + echecs as traites,
    round(100.0 * reussis / nullif(reussis + echecs, 0), 1) as taux_succes
from suivi.suivi_journal
where media = '${params.media}'
order by horodatage
```

<LineChart
    data={progression}
    x=horodatage
    y={["reussis", "echecs"]}
    title="Articles cumulés (réussis vs échecs)"
    yAxisTitle="articles"
/>

## Taux de réussite dans le temps

<LineChart
    data={progression}
    x=horodatage
    y=taux_succes
    title="Taux de réussite (%)"
    yAxisTitle="% de succès"
    yMin=0
    yMax=100
/>
