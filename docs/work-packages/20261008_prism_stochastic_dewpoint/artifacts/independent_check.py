#!/usr/bin/env python3
"""Independent saved-table metric calculations and closed-evidence checks."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cdf_distance(a, b):
    a, b = np.sort(a), np.sort(b)
    support = np.unique(np.r_[a, b])
    return np.sum(np.diff(support) * np.abs(np.searchsorted(a, support[:-1], side='right')/len(a)-np.searchsorted(b, support[:-1], side='right')/len(b)))


def main():
    checked = {}
    for name in ['20261008_dewpoint_openet', '20261008_stochastic_dewpoint']:
        parent=HERE.parents[1]/name/'artifacts'
        entries=json.loads((parent/'artifact-index.json').read_text())
        for filename, info in entries.items():
            assert digest(parent/filename) == info['sha256'], filename
        checked[name]=len(entries)
    months=pd.read_csv(HERE/'wepp-monthly.csv',parse_dates=['date'])
    obs=pd.read_csv(HERE.parents[1]/'20261008_dewpoint_openet/artifacts/openet-monthly.csv',parse_dates=['date'])
    obs['month']=obs.date.dt.month
    metrics=pd.read_csv(HERE/'comparison-metrics.csv')
    errors=[]
    for row in metrics.itertuples():
        a=months[(months.site==row.site)&(months.arm==row.arm)]
        if row.seed!='pooled':
            a=a[a.seed==int(row.seed)]
        b=obs[(obs.site==row.site)&(obs.model==row.model)]
        monthly_errors=[];dist=[]
        for month in range(1,13):
            x=a[a.month==month].et.to_numpy();y=b[b.month==month].et.to_numpy()
            monthly_errors.append(x.mean()-y.mean());dist.append(cdf_distance(x,y))
        actual=np.array([np.mean(np.abs(monthly_errors)),np.sqrt(np.mean(np.square(monthly_errors))),np.mean(dist)])
        expected=np.array([row.cycle_mae_mm,row.cycle_rmse_mm,row.monthly_distribution_distance_mm])
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-10)
        errors.append(float(np.max(abs(actual-expected))))
    precipitation=pd.read_csv(HERE/'precipitation-comparison.csv').set_index('site')
    for site, group in months.groupby('site'):
        np.testing.assert_allclose(group.p.sum()/2/10/7,precipitation.loc[site,'assessment_generated_p_mm'],atol=.03,rtol=0)
    result=dict(prior_artifact_hashes_verified=checked,metric_rows_independently_verified=len(metrics),max_metric_error=max(errors),precipitation_output_vs_generated_verified=True,method='explicit monthly means and empirical-CDF integral, independent of scipy wasserstein_distance')
    (HERE/'independent-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':
    main()
