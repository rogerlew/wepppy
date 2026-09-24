"""Rebuild epoch comparisons from retained station extracts and run climate snapshots."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent

def main():
    station = pd.read_csv(HERE/'station_daily.csv', parse_dates=['date'])
    climate = pd.read_csv(HERE/'run_precipitation_daily.csv', parse_dates=['date'])
    paired = station.merge(climate, on='date', validate='many_to_one')
    paired['epoch'] = np.where(paired.date < '2023-08-01', 'before', 'after')
    paired.to_csv(HERE/'paired_daily.csv', index=False)
    results=[]
    for (site, epoch), all_rows in paired.groupby(['station','epoch']):
        rows=all_rows.dropna(subset=['station_mm'])
        for forcing in ['gridmet_mm','wepp_cli_mm','wepp_hillslope_area_weighted_mm']:
            obs=rows.station_mm; model=rows[forcing]
            results.append(dict(station=site,epoch=epoch,forcing=forcing,
                first_date=str(rows.date.min().date()),last_date=str(rows.date.max().date()),
                valid_days=len(rows),candidate_days=len(all_rows),
                station_mm=obs.sum(),forcing_mm=model.sum(),bias_pct=100*(model.sum()/obs.sum()-1),
                daily_r=model.corr(obs),daily_rmse_mm=np.sqrt(((model-obs)**2).mean())))
    summary=pd.DataFrame(results);summary.to_csv(HERE/'epoch_summary.csv',index=False)
    # Equal pre/post seasonal window, avoiding unequal season weighting.
    windows={'before':('2020-08-01','2022-12-31'),'after':('2023-08-01','2025-12-31')}
    matched=[]
    for site, df in paired.groupby('station'):
        for label,(start,end) in windows.items():
            r=df[df.date.between(start,end)].dropna(subset=['station_mm'])
            matched.append(dict(station=site,epoch=label,start=start,end=end,valid_days=len(r),
                station_mm=r.station_mm.sum(),gridmet_mm=r.gridmet_mm.sum(),
                bias_pct=100*(r.gridmet_mm.sum()/r.station_mm.sum()-1)))
    pd.DataFrame(matched).to_csv(HERE/'equal_season_window_summary.csv',index=False)
    monthly=[]
    for site,df in paired.groupby('station'):
        for month,r in df.groupby(df.date.dt.to_period('M')):
            valid=r.dropna(subset=['station_mm'])
            monthly.append(dict(station=site,month=str(month),valid_days=len(valid),
                expected_days=month.days_in_month,station_mm=valid.station_mm.sum(),
                gridmet_mm=valid.gridmet_mm.sum(),wepp_cli_mm=valid.wepp_cli_mm.sum(),wepp_hillslope_area_weighted_mm=valid.wepp_hillslope_area_weighted_mm.sum()))
    monthly=pd.DataFrame(monthly);monthly.to_csv(HERE/'monthly_paired_totals.csv',index=False)
    # Calendar-month bias supports seasonally resolved interpretation.
    seas=paired.dropna(subset=['station_mm']).copy();seas['month']=seas.date.dt.month
    seas=seas.groupby(['station','epoch','month'])[['station_mm','gridmet_mm']].sum()
    seas['bias_pct']=100*(seas.gridmet_mm/seas.station_mm-1)
    seas.to_csv(HERE/'calendar_month_bias.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharey=True)
    for ax,(site,df) in zip(axes.flat,monthly.groupby('station')):
        df=df[df.month>='2019-01'].copy()
        incomplete=df.valid_days/df.expected_days < 0.8
        df.loc[incomplete,['station_mm','wepp_hillslope_area_weighted_mm']]=np.nan
        df['date']=pd.to_datetime(df.month)
        ax.plot(df.date,df.station_mm,label='Station',color='black',lw=1)
        ax.plot(df.date,df.wepp_hillslope_area_weighted_mm,label='WEPP area-weighted forcing',color='#2077b4',lw=1)
        ax.axvline(pd.Timestamp('2023-08-01'),color='#b64a35',ls='--')
        ax.set_title(site);ax.set_ylabel('Precipitation on paired days (mm/month)');ax.grid(alpha=.2)
    axes[0,0].legend();fig.suptitle('Lookout precipitation: matched-day totals, months with ≥80% usable days\nStation points versus area-weighted WEPP precipitation; split at August 1, 2023')
    fig.tight_layout();fig.savefig(HERE/'precipitation_comparison.png',dpi=160)
    print(summary[summary.forcing=='wepp_hillslope_area_weighted_mm'].to_string(index=False))

if __name__=='__main__': main()
