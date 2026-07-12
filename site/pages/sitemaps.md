---
title: Collecte des sitemaps
sidebar_position: 4
---

Deux fois par jour (5h40 le matin, 17h40 l'après-midi, heures UTC), le pipeline
lit la sitemap news de chaque média et ajoute à la file de scraping les URLs
d'articles qu'on ne connaissait pas encore. On suit ici combien de nouvelles
URLs chaque journée apporte : une barre par jour, découpée entre les deux
passages.

```sql par_jour
select
    strftime(cast(horodatage::timestamp as date), '%d/%m') as jour,
    case when extract(hour from horodatage::timestamp) < 12
         then 'Matin (5h40)' else 'Après-midi (17h40)' end as passage,
    sum(ajoutees) as ajoutees
from suivi.sitemaps_journal
group by cast(horodatage::timestamp as date), passage
order by cast(horodatage::timestamp as date)
```

<BarChart
    data={par_jour}
    x=jour
    y=ajoutees
    series=passage
    type=stacked
    sort=false
    seriesColors={{"Matin (5h40)": "#236aa4", "Après-midi (17h40)": "#d0782c"}}
    title="Nouvelles URLs trouvées par jour"
    yAxisTitle="URLs ajoutées"
/>

## Détail des passages

Une sitemap news liste **tous** les articles récents du média (fenêtre
glissante d'environ 48 h) : d'un passage à l'autre, la plupart des URLs y
figurent donc encore. « URLs listées » compte tout ce que les sitemaps
affichaient à ce passage ; « Nouvelles » ne garde que les URLs jamais vues,
celles qui rejoignent réellement la file de scraping. C'est cette dernière
colonne que reprend le graphique.

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
    <Column id=dans_sitemap title="URLs listées" fmt='#,##0'/>
    <Column id=ajoutees title="Nouvelles" fmt='#,##0'/>
</DataTable>
