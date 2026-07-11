---
title: Collecte des sitemaps
sidebar_position: 4
---

Deux fois par jour (5h40 et 17h40 UTC), le pipeline lit la sitemap news de
chaque média et ajoute à la file de scraping les URLs d'articles qu'on ne
connaissait pas encore. On suit ici combien de nouvelles URLs chaque journée
apporte.

```sql par_jour
select
    cast(horodatage::timestamp as date) as jour,
    sum(ajoutees) as ajoutees
from suivi.sitemaps_journal
group by jour
order by jour
```

<BarChart
    data={par_jour}
    x=jour
    y=ajoutees
    fillColor=#236aa4
    title="Nouvelles URLs trouvées par jour"
    yAxisTitle="URLs ajoutées"
/>

## Détail des passages

Chaque ligne est un passage du cron : le nombre d'URLs vues dans l'ensemble
des sitemaps news, et combien étaient nouvelles.

```sql passages
select
    horodatage::timestamp as horodatage,
    sum(dans_sitemap) as dans_sitemap,
    sum(ajoutees) as ajoutees
from suivi.sitemaps_journal
group by horodatage
order by horodatage desc
```

<DataTable data={passages}>
    <Column id=horodatage title="Passage" fmt='yyyy-mm-dd HH:MM'/>
    <Column id=dans_sitemap title="URLs dans les sitemaps" fmt='#,##0'/>
    <Column id=ajoutees title="Nouvelles" fmt='#,##0'/>
</DataTable>
