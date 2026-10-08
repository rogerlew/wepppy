#!/usr/bin/env python3
"""Exploratory forest OpenET bias sensitivity; not a calibrated correction."""
from pathlib import Path

import pandas as pd

import study

HERE=Path(__file__).resolve().parent
months=pd.read_csv(HERE/'wepp-monthly.csv')
obs=pd.read_csv(study.OLD/'openet-monthly.csv',parse_dates=['date'])
obs['month']=obs.date.dt.month
rows=[]
for site,g in months[months.watershed!='Topanga'].groupby('site'):
    reference=obs[(obs.site==site)&(obs.model=='Ensemble')].copy()
    for divisor in [1,1.2,1.25]:
        adjusted=reference.copy()
        adjusted['et']=adjusted.et/divisor
        for arm,data in g.groupby('arm'):
            rows.append(dict(site=site,arm=arm,openet_divisor=divisor,**study.compare(data,adjusted)))
r=pd.DataFrame(rows)
r.to_csv(HERE/'forest-bias-sensitivity.csv',index=False)
p=r.pivot(index=['site','openet_divisor'],columns='arm')
print({metric:int(sum(p[metric].clipped<p[metric].native)) for metric in ['cycle_mae_mm','cycle_rmse_mm','monthly_distribution_distance_mm']})
print('Total',len(p))
