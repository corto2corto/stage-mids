---
title: Évolution du taux de réussite
sidebar_position: 3
---

Évolution du taux de réussite du scraping au fil du temps, média par média.
Une courbe qui plonge signale un bypass paywall qui décroche à un moment donné.
Source : journal de bord (`suivi_journal.csv`).

```sql medias
select
    coalesce(l.nom, j.media) as nom,
    j.media
from suivi.suivi_journal j
left join suivi.libelles l on j.media = l.media
group by j.media, l.nom
order by nom
```

**Choisis un ou plusieurs médias pour afficher leur courbe :**

<Dropdown
    data={medias}
    name=medias_choisis
    value=media
    label=nom
    title="Médias"
    multiple=true
    noDefault=true
/>

```sql evolution
select
    horodatage::timestamp as horodatage,
    coalesce(l.nom, j.media) as nom,
    round(100.0 * j.reussis / nullif(j.reussis + j.echecs, 0), 1) as taux_succes
from suivi.suivi_journal j
left join suivi.libelles l on j.media = l.media
where j.media in ${inputs.medias_choisis.value}
order by horodatage
```

<LineChart
    data={evolution}
    x=horodatage
    y=taux_succes
    series=nom
    title="Taux de réussite au fil du temps"
    yAxisTitle="% de succès"
    yMin=0
    yMax=100
    chartAreaHeight=480
/>
