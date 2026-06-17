---
title: Suivi du scraping
---

Vue d'ensemble du scraping des médias français. Les chiffres proviennent du
journal de bord (`suivi_journal.csv`) : un instantané régulier des compteurs
réussis / échecs par média.

```sql dernier_etat
-- Dernier instantané connu pour chaque média (compteurs cumulés)
with derniers as (
    select
        media,
        max(horodatage) as horodatage_max
    from suivi.suivi_journal
    group by media
)
select
    coalesce(l.nom, j.media) as nom,
    j.reussis,
    j.echecs,
    j.reussis + j.echecs as traites,
    round(100.0 * j.reussis / nullif(j.reussis + j.echecs, 0), 1) as taux_succes,
    '/media/' || j.media as lien
from suivi.suivi_journal j
inner join derniers d
    on j.media = d.media and j.horodatage = d.horodatage_max
left join suivi.libelles l on j.media = l.media
order by taux_succes desc
```

## Chiffres clés

```sql totaux
-- Totaux tous médias confondus, calculés directement en SQL
select
    sum(traites) as total_traites,
    count(*)     as nb_medias
from ${dernier_etat}
```

<BigValue
    data={totaux}
    value=total_traites
    title="Articles traités (tous médias)"
    fmt='#,##0'
/>

<BigValue
    data={totaux}
    value=nb_medias
    title="Médias suivis"
/>

## Par média

Clique sur un média pour voir le détail.

<DataTable data={dernier_etat} link=lien rows=all>
    <Column id=nom title="Média"/>
    <Column id=traites title="Traités" fmt='#,##0'/>
    <Column id=reussis title="Réussis" fmt='#,##0'/>
    <Column id=echecs title="Échecs" fmt='#,##0'/>
    <Column id=taux_succes title="% succès" contentType=colorscale colorScale=positive/>
</DataTable>

## Taux de réussite comparé

```sql classement
select nom, taux_succes from ${dernier_etat} order by taux_succes desc
```

<BarChart
    data={classement}
    x=nom
    y=taux_succes
    swapXY=true
    title="Taux de réussite par média (%)"
    yAxisTitle="% de succès"
/>
