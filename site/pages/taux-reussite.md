---
title: Taux de réussite
sidebar_position: 2
---

Parmi les articles déjà traités, on voit ici combien ont vraiment pu être
récupérés, média par média. Le taux global cumule tout depuis le début : il
bouge peu quand un média décroche. Les colonnes 24h et 72h ne comptent que les
articles traités dans la fenêtre (calculées par différence entre deux relevés
des compteurs) et révèlent tout de suite un décrochage récent. Une case vide
signifie qu'aucun article n'a été traité dans la fenêtre.

```sql dernier_etat
with h as (
    select max(horodatage) as h_max from suivi.suivi_journal
),
dernier as (
    select media,
        max_by(reussis, horodatage) as reussis,
        max_by(echecs, horodatage) as echecs
    from suivi.suivi_journal
    group by media
),
avant_24h as (
    select media,
        max_by(reussis, horodatage) as reussis,
        max_by(echecs, horodatage) as echecs
    from suivi.suivi_journal, h
    where horodatage <= h.h_max - interval 24 hours
    group by media
),
avant_72h as (
    select media,
        max_by(reussis, horodatage) as reussis,
        max_by(echecs, horodatage) as echecs
    from suivi.suivi_journal, h
    where horodatage <= h.h_max - interval 72 hours
    group by media
)
select
    coalesce(l.nom, d.media) as nom,
    d.reussis,
    d.echecs,
    d.reussis + d.echecs as traites,
    round(100.0 * d.reussis / nullif(d.reussis + d.echecs, 0), 1) as taux_succes,
    round(100.0 * (d.reussis - a24.reussis)
        / nullif((d.reussis + d.echecs) - (a24.reussis + a24.echecs), 0), 1) as taux_24h,
    round(100.0 * (d.reussis - a72.reussis)
        / nullif((d.reussis + d.echecs) - (a72.reussis + a72.echecs), 0), 1) as taux_72h,
    '/media/' || d.media as lien
from dernier d
left join avant_24h a24 using (media)
left join avant_72h a72 using (media)
left join suivi.libelles l on d.media = l.media
order by taux_succes desc
```

<DataTable data={dernier_etat} link=lien rows=all>
    <Column id=nom title="Média"/>
    <Column id=traites title="Traités" fmt='#,##0'/>
    <Column id=reussis title="Réussis" fmt='#,##0'/>
    <Column id=echecs title="Échecs" fmt='#,##0'/>
    <Column id=taux_succes title="% succès" contentType=colorscale colorScale=positive/>
    <Column id=taux_24h title="% 24h" contentType=colorscale colorScale=positive/>
    <Column id=taux_72h title="% 72h" contentType=colorscale colorScale=positive/>
</DataTable>

<BarChart
    data={dernier_etat}
    x=nom
    y=taux_succes
    swapXY=true
    title="Taux de réussite par média (%)"
    yAxisTitle="% de succès"
/>
