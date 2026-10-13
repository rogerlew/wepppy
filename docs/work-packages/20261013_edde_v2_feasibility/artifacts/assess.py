"""Summarize matched-period climate statistics and independent Daymet bias.

Daily simulated sequences are not synchronized forecasts. We compare distributions
and climatologies, never daily model/observation correlation as forecast skill.
"""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from wepppy.climates.edde.client import sha256,write_json

HERE=Path(__file__).resolve().parent
WINDOWS=[('WRF-MPI','Historical',1995,2014),('WRF-Nor','Historical',1995,2014),
         ('WRF-MPI','SSP2-4.5',2060,2079),('WRF-Nor','SSP2-4.5',2060,2079),
         ('WRF-MPI','SSP2-4.5',2080,2099),('WRF-MPI','SSP3-7.0',2080,2099)]


def longest(mask,dates):
    best=current=0
    previous=None
    for flag,date in zip(mask,dates):
        if previous is not None and date-previous!=pd.Timedelta(days=1):current=0
        current=current+1 if flag else 0
        best=max(best,current);previous=date
    return best


def metrics(frame):
    years=frame.index.year.nunique()
    wet=frame.prday>=1.
    annualmax=frame.prday.groupby(frame.index.year).max()
    return dict(days=len(frame),annual_p_mm=float(frame.prday.sum()/years),
                mean_tmax_c=float(frame.tmax.mean()),mean_tmin_c=float(frame.tmin.mean()),
                wet_fraction_1mm=float(wet.mean()),max_dry_spell_days=longest(~wet,frame.index),
                max_wet_spell_days=longest(wet,frame.index),
                wet_p95_mm=float(frame.loc[wet,'prday'].quantile(.95)),
                daily_p99_mm=float(frame.prday.quantile(.99)),
                mean_annual_max_p_mm=float(annualmax.mean()),
                maximum_p_mm=float(frame.prday.max()))


def reference(point):
    path=HERE/'reference'/f'{point}.csv'
    text=path.read_text();lines=text.splitlines()
    skip=next(i for i,line in enumerate(lines) if line.startswith('year,yday'))
    frame=pd.read_csv(io.StringIO('\n'.join(lines[skip:])))
    dates=pd.to_datetime(frame.year.astype(int).astype(str))+pd.to_timedelta(frame.yday-1,unit='D')
    result=pd.DataFrame(dict(prday=frame['prcp (mm/day)'].to_numpy(),
                             tmax=frame['tmax (deg c)'].to_numpy(),tmin=frame['tmin (deg c)'].to_numpy()),
                        index=pd.DatetimeIndex(dates))
    if not np.isfinite(result.to_numpy()).all() or (result.prday<0).any():raise ValueError('Invalid reference')
    return result


def main():
    summary=[];monthly=[];bias=[];quality=[];acquisition=[];series={}
    for model,scenario,first,last in WINDOWS:
        tables=[]
        for year in range(first,last+1):
            root=HERE/'queries'/model/scenario
            meta=json.loads((root/f'{year}.json').read_text());csv=root/f'{year}.csv'
            if meta['status']!='complete' or sha256(csv)!=meta['daily_sha256']:raise ValueError('Unverified query')
            tables.append(pd.read_csv(csv,parse_dates=['date']))
            acquisition.append(dict(model=model,scenario=scenario,year=year,
                                    source_bytes=meta['source_bytes'],transferred_bytes=meta['transferred_bytes'],
                                    seconds=meta['wall_seconds'],peak_rss_kib=meta['process_peak_rss_kib']))
        allpoints=pd.concat(tables,ignore_index=True)
        for point,data in allpoints.groupby('point'):
            frame=data.set_index('date').sort_index()
            frame['tmax']=frame.tsmax-273.15;frame['tmin']=frame.tsmin-273.15
            identity=dict(model=model,scenario=scenario,first=first,last=last,point=point)
            invalid=dict(missing=int(frame[['prday','tsmax','tsmin']].isna().sum().sum()),
                         negative_p=int((frame.prday<0).sum()),inverted_temperature=int((frame.tsmin>frame.tsmax).sum()),
                         continuous_dates=frame.index.equals(pd.date_range(f'{first}-01-01',f'{last}-12-31')))
            quality.append(dict(**identity,**invalid))
            if invalid['missing'] or invalid['negative_p'] or invalid['inverted_temperature'] or not invalid['continuous_dates']:
                raise ValueError(f'Invalid daily source: {identity}')
            summary.append(dict(**identity,**metrics(frame)))
            for month,group in frame.groupby(frame.index.month):
                monthly.append(dict(**identity,month=month,monthly_p_mm=float(group.prday.sum()/(last-first+1)),
                                    tmax_c=float(group.tmax.mean()),tmin_c=float(group.tmin.mean())))
            series[(model,scenario,first,point)]=frame
            if scenario=='Historical':
                ref=reference(point);common=frame.index.intersection(ref.index)
                left,right=metrics(frame.loc[common]),metrics(ref.loc[common])
                bias.append(dict(**identity,matched_days=len(common),
                                 p_bias_percent=100*(left['annual_p_mm']/right['annual_p_mm']-1),
                                 tmax_bias_c=left['mean_tmax_c']-right['mean_tmax_c'],
                                 tmin_bias_c=left['mean_tmin_c']-right['mean_tmin_c'],
                                 wet_fraction_bias=left['wet_fraction_1mm']-right['wet_fraction_1mm'],
                                 p99_bias_mm=left['daily_p99_mm']-right['daily_p99_mm'],
                                 reference_annual_p_mm=right['annual_p_mm'],
                                 reference_mean_tmax_c=right['mean_tmax_c'],reference_mean_tmin_c=right['mean_tmin_c']))
    s=pd.DataFrame(summary);s.to_csv(HERE/'climate-summary.csv',index=False)
    pd.DataFrame(monthly).to_csv(HERE/'monthly-climate.csv',index=False)
    b=pd.DataFrame(bias);b.to_csv(HERE/'historical-daymet-bias.csv',index=False)
    pd.DataFrame(acquisition).to_csv(HERE/'acquisition-benchmarks.csv',index=False)
    write_json(HERE/'source-quality.json',quality)
    future=[]
    for row in summary:
        if row['scenario']=='Historical':continue
        historical=next(r for r in summary if r['model']==row['model'] and r['scenario']=='Historical' and r['point']==row['point'])
        future.append(dict(model=row['model'],scenario=row['scenario'],first=row['first'],last=row['last'],point=row['point'],
                           annual_p_change_percent=100*(row['annual_p_mm']/historical['annual_p_mm']-1),
                           tmax_change_c=row['mean_tmax_c']-historical['mean_tmax_c'],
                           tmin_change_c=row['mean_tmin_c']-historical['mean_tmin_c'],
                           wet_fraction_change=row['wet_fraction_1mm']-historical['wet_fraction_1mm'],
                           p99_change_mm=row['daily_p99_mm']-historical['daily_p99_mm']))
    pd.DataFrame(future).to_csv(HERE/'future-changes.csv',index=False)
    write_json(HERE/'assessment-conventions.json',dict(historical='1995-2014',common_future='2060-2079 SSP2-4.5',
        mpi_late_century='2080-2099 SSP2-4.5 and SSP3-7.0',wet_day_mm=1,
        reference='Public ORNL Daymet single-pixel; observed-data interpolation, not independent station measurements',
        calendar='Daymet has 365 days per year; comparisons use intersecting calendar dates, omit Dec 31 in leap years',
        baseline_comparison='Climate distributions; daily sequences are not date-matched weather forecasts',
        acceptance='No nonfinite, missing, negative precipitation, inverted extrema, or calendar gaps. Bias reported without correction or invented suitability thresholds.',
        utc_boundary='EDDE daily equals same-labeled UTC hourly sum; Daymet observation-day conventions differ',
        uncertainty='20 years and two driving models do not establish full ensemble or future impact uncertainty'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    for model,color in [('WRF-MPI','#1673a5'),('WRF-Nor','#a04d21')]:
        part=b[b.model==model].sort_values('point');y=np.arange(len(part))
        axes[0].scatter(part.p_bias_percent,y,label=model,color=color)
        axes[1].scatter(part.tmax_bias_c,y,label=model,color=color)
    for ax in axes:
        ax.set_yticks(y,part.point);ax.axvline(0,color='gray',linewidth=.7);ax.grid(axis='x',alpha=.2)
    axes[0].set_xlabel('Annual precipitation bias relative to Daymet (%)')
    axes[1].set_xlabel('Mean daily maximum temperature bias (°C)')
    axes[1].set_yticklabels([]);axes[0].legend()
    fig.suptitle('EDDE historical screening · 1995–2014 · common calendar days')
    fig.tight_layout();fig.savefig(HERE/'historical-bias.png',dpi=160);plt.close(fig)
    print(b.groupby('model')[['p_bias_percent','tmax_bias_c','tmin_bias_c']].agg(['min','max']).to_string())


if __name__=='__main__':main()
