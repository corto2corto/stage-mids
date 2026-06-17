---
title: Taux de réussite
sidebar_position: 2
---

Parmi les articles déjà traités, on voit ici combien ont vraiment pu être
récupérés, média par média. Le graphique permet de comparer les médias d'un coup
d'œil.

```sql dernier_etat
with derniers as (
    select media, max(horodatage) as horodatage_max
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

<DataTable data={dernier_etat} link=lien rows=all>
    <Column id=nom title="Média"/>
    <Column id=traites title="Traités" fmt='#,##0'/>
    <Column id=reussis title="Réussis" fmt='#,##0'/>
    <Column id=echecs title="Échecs" fmt='#,##0'/>
    <Column id=taux_succes title="% succès" contentType=colorscale colorScale=positive/>
</DataTable>

<BarChart
    data={dernier_etat}
    x=nom
    y=taux_succes
    swapXY=true
    title="Taux de réussite par média (%)"
    yAxisTitle="% de succès"
/>
