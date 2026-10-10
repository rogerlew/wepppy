#!/usr/bin/env python3
"""Describe the bounded candidate against both released baselines, without gates."""
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from wepppyo3 import wepp_interchange as native

from candidate_replay import ROOT, SITES, SUFFIX, HERE
from output_replay import sha, save

OUT=HERE/'artifacts/candidate'
SNAPSHOT=HERE.parents[1]/'investigations/2026-10-09-watershed-return-period-comparisons/artifacts/snapshot'
OLD_LIVE={'topanga':Path('/wc1/runs/ei/eighty-five-synthetic'),
          'rattlesnake':Path('/wc1/runs/as/ascending-mourner')}


def reference(site,scenario,version):
    if site=='topanga' and version=='260803':
        return HERE/'artifacts/260803-comparison'/f'260803-{scenario}-ebe.parquet'
    prefix='topanga_gridmet' if site=='topanga' else 'rattlesnake'
    return SNAPSHOT/f'{prefix}_{version}_{scenario}.parquet'


def pct(new,old):
    return 100*(new/old-1) if old else np.nan


def fit(new,old):
    r=float(np.corrcoef(new,old)[0,1])
    return dict(nse=1-float(np.square(new-old).sum()/np.square(old-old.mean()).sum()),
                kge=1-float(np.sqrt((r-1)**2+(new.std()/old.std()-1)**2+(new.mean()/old.mean()-1)**2)),
                r_squared=r*r)


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    comparisons=[];annual=[];extremes=[];windows=[];timings=[];losses=[];identities={}
    for site,cfg in SITES.items():
        for scenario,suffix in SUFFIX.items():
            name=f'{site}-{scenario}'
            receipt=json.loads((ROOT/f'{name}-receipt.json').read_text());assert receipt['completed']
            case=ROOT/site/suffix/'wepp'
            candidate=pd.read_parquet(ROOT/f'{name}-ebe.parquet')
            assert np.isfinite(candidate[['runoff_volume','peak_runoff','sediment_yield']]).all().all()
            aux=ROOT/f'{name}-analysis';aux.mkdir(exist_ok=False)
            native.watershed_loss_to_parquet(str(case/'output/loss_pw0.txt'),str(aux),1,0)
            native.watershed_chan_peak_to_parquet(str(case/'output/chan.out'),str(aux/'peaks.parquet'),1,0,
                cli_calendar_path=str(ROOT/site/'calendar.parquet'),start_year=cfg['start_year'])
            cand_peaks=pd.read_parquet(aux/'peaks.parquet')
            for label,root in [('candidate',aux),('261009',cfg['live']/suffix/'wepp/output/interchange'),
                               ('260803',OLD_LIVE[site]/suffix/'wepp/output/interchange')]:
                data=pd.read_parquet(root/'loss_pw0.out.parquet');data.insert(0,'version',label)
                data.insert(0,'scenario',scenario);data.insert(0,'site',site);losses.append(data)
                identities[str(root/'loss_pw0.out.parquet')]=sha(root/'loss_pw0.out.parquet')
            for version in ['260803','261009']:
                path=reference(site,scenario,version);baseline=pd.read_parquet(path)
                assert len(candidate)==len(baseline)
                for column in ['year','month','day_of_month']:
                    assert np.array_equal(candidate[column],baseline[column]),column
                identities[str(path)]=sha(path)
                record=dict(site=site,scenario=scenario,baseline=version,days=len(candidate))
                for metric in ['runoff_volume','peak_runoff','sediment_yield']:
                    a=candidate[metric].to_numpy();b=baseline[metric].to_numpy();delta=a-b
                    for label,values in [('candidate',a),('baseline',b)]:
                        record[f'{metric}_{label}_total']=float(values.sum())
                        record[f'{metric}_{label}_max']=float(values.max())
                    record[f'{metric}_total_pct']=pct(a.sum(),b.sum())
                    record[f'{metric}_changed_days']=int((delta!=0).sum())
                    record[f'{metric}_new_positive_days']=int(((a>0)&(b==0)).sum())
                    record[f'{metric}_lost_positive_days']=int(((a==0)&(b>0)).sum())
                    for direction,indices in [('increase',np.argsort(delta)[-10:]),('decrease',np.argsort(delta)[:10])]:
                        for i in indices:
                            row=candidate.iloc[i]
                            extremes.append(dict(site=site,scenario=scenario,baseline_version=version,metric=metric,
                                direction=direction,year=int(row.year),month=int(row.month),day=int(row.day_of_month),
                                baseline=float(b[i]),candidate=float(a[i]),delta=float(delta[i])))
                    if metric=='runoff_volume':record.update(fit(a,b))
                comparisons.append(record)
                yearly=candidate.groupby('year')[['runoff_volume','sediment_yield']].sum()
                original=baseline.groupby('year')[['runoff_volume','sediment_yield']].sum()
                for year in yearly.index:
                    row=dict(site=site,scenario=scenario,baseline=version,year=int(year))
                    for metric in ['runoff_volume','sediment_yield']:
                        row[metric+'_baseline']=float(original.loc[year,metric]);row[metric+'_candidate']=float(yearly.loc[year,metric])
                        row[metric+'_pct']=pct(yearly.loc[year,metric],original.loc[year,metric])
                    annual.append(row)
                oldroot=(cfg['live'] if version=='261009' else OLD_LIVE[site])/suffix/'wepp/output/interchange'
                original_peaks=pd.read_parquet(oldroot/'chan.out.parquet')
                assert len(cand_peaks)==len(original_peaks)==len(candidate)
                shift=cand_peaks['Time (s)'].to_numpy()-original_peaks['Time (s)'].to_numpy()
                timings.append(dict(site=site,scenario=scenario,baseline=version,changed_days=int((shift!=0).sum()),
                    max_absolute_shift_seconds=float(np.abs(shift).max()),median_absolute_shift_seconds=float(np.median(np.abs(shift)))))
                if site=='topanga':
                    for label,frame in [(version,baseline),('candidate',candidate)]:
                        w=frame.loc[frame.year.eq(1993)&frame.month.eq(1)&frame.day_of_month.between(10,24)].copy()
                        w.insert(0,'version',label);w.insert(0,'scenario',scenario);windows.append(w)
            shutil.copy2(ROOT/f'{name}-receipt.json',OUT/f'{name}-receipt.json')
            shutil.copy2(ROOT/f'{name}-hills.json',OUT/f'{name}-hills.json')
    pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False)
    pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False)
    pd.DataFrame(extremes).to_csv(OUT/'largest-event-changes.csv',index=False)
    pd.DataFrame(timings).to_csv(OUT/'timing.csv',index=False)
    pd.concat(losses).to_csv(OUT/'loss-summaries.csv',index=False)
    window=pd.concat(windows).drop_duplicates(['scenario','version','year','month','day_of_month'])
    window.to_csv(OUT/'january10-24.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for ax,scenario in zip(axes,['burned','undisturbed']):
        for version,color in [('260803','#777777'),('261009','#b54930'),('candidate','#16748c')]:
            f=window.loc[window.scenario.eq(scenario)&window.version.eq(version)&window.day_of_month.between(16,20)]
            ax.plot(f.day_of_month,f.peak_runoff,'o-',label=version,color=color)
        ax.set_title(scenario.title());ax.set_xlabel('January 1993 day');ax.set_ylabel('Daily maximum outlet peak (m3/s)')
        ax.set_xticks(range(16,21));ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Topanga: daily peak comparison, not a time-step hydrograph')
    fig.savefig(OUT/'january-peaks.png',dpi=170);plt.close(fig)
    save(OUT/'reference-hashes.json',identities)
    shutil.copy2(ROOT/'build.json',OUT/'build.json')
    save(OUT/'manifest.json',{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    print(pd.DataFrame(comparisons)[['site','scenario','baseline','runoff_volume_total_pct','sediment_yield_total_pct','peak_runoff_candidate_max','peak_runoff_baseline_max']].to_string(index=False))


if __name__=='__main__':
    main()
