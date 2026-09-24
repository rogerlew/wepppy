"""Rebuild daily stations from retained precipitation extracts and the archived ZIP."""
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
r=pd.read_parquet(HERE/'station_five_minute_precipitation.parquet')
assert not r.duplicated(['station','timestamp']).any()
r['date']=(r.timestamp-pd.Timedelta(nanoseconds=1)).dt.normalize()
r['valid']=r.flag.fillna('').eq('') & np.isfinite(r.precip_mm) & r.precip_mm.ge(0)
r['accepted']=r.precip_mm.where(r.valid)
d=r.groupby(['station','date']).agg(intervals=('timestamp','size'),valid_intervals=('valid','sum'),station_mm=('accepted',lambda x:x.sum(min_count=288))).reset_index()
d.loc[(d.intervals!=288)|(d.valid_intervals!=288),'station_mm']=np.nan
d['source']='provisional_5min';d['flag']=''
d.loc[d.station_mm.isna(),'flag']='incomplete_or_flagged'
bad=r[r.flag.fillna('').eq('') & r.precip_mm.gt(50)][['station','date']].drop_duplicates()
bad=pd.concat([bad,d[d.station_mm.gt(500)][['station','date']]]).drop_duplicates();bad['physical_screen']=True
d=d.merge(bad,on=['station','date'],how='left')
excluded=d[d.physical_screen.eq(True)&d.station_mm.notna()].copy()
d.loc[d.physical_screen.eq(True),'station_mm']=np.nan
d.loc[d.physical_screen.eq(True),'flag']='implausible_interval_or_daily_total'
a=pd.read_csv(HERE/'MS00103_v8.zip',parse_dates=['DATE'])
a=a[a.PROBE_CODE.isin(['PPTPRI01','PPTUPL01','PPTCEN01','PPTVAR02']) & a.DATE.ge('1986-01-01')].copy()
a['station']=a.SITECODE;a['date']=a.DATE
a['station_mm']=a.PRECIP_TOT_DAY.where(a.PRECIP_TOT_FLAG.eq('A') & a.PRECIP_TOT_DAY.ge(0))
a['source']='MS00103_v8';a['flag']=a.PRECIP_TOT_FLAG
for site,group in a.groupby('station'):
    d=d[~((d.station==site)&d.date.le(group.date.max()))]
    excluded=excluded[~((excluded.station==site)&excluded.date.le(group.date.max()))]
d=pd.concat([d,a[['station','date','station_mm','source','flag']]],ignore_index=True).sort_values(['station','date'])
d=d[d.date.between('1986-01-01','2025-12-31')]
assert not d.duplicated(['station','date']).any()
d.to_csv(HERE/'station_daily.csv',index=False)

excluded.to_csv(HERE/'excluded_unflagged_artifacts.csv',index=False)
