---
title: Avancement
sidebar_position: 1
---

Où en est le scraping des médias français : part déjà traitée et nombre d'URLs
restant à parcourir, par média. Source : base des URLs (`avancement.csv`).

```sql avancement
select
    coalesce(l.nom, a.media) as nom,
    a.media,
    a.restants,
    a.echecs,
    a.reussis,
    a.reussis + a.echecs as traites,
    a.total,
    round(100.0 * (a.reussis + a.echecs) / nullif(a.total, 0), 1) as pct_traite,
    '/media/' || a.media as lien
from suivi.avancement a
left join suivi.libelles l on a.media = l.media
order by pct_traite desc
```

## Chiffres clés

```sql totaux
select
    sum(total)            as total_urls,
    sum(reussis + echecs) as traites,
    sum(restants)         as restants
from ${avancement}
```

<BigValue data={totaux} value=total_urls title="URLs au total" fmt='#,##0'/>
<BigValue data={totaux} value=traites title="Déjà traitées" fmt='#,##0'/>
<BigValue data={totaux} value=restants title="Restant à scraper" fmt='#,##0'/>

## Progression par média

Clique sur un média pour voir son détail.

<DataTable data={avancement} link=lien rows=all>
    <Column id=nom title="Média"/>
    <Column id=pct_traite title="Avancement" contentType=bar barColor=#236aa4 fmt='0.0"%"'/>
    <Column id=restants title="Restants" fmt='#,##0'/>
    <Column id=traites title="Traités" fmt='#,##0'/>
</DataTable>
