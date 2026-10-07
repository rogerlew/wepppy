"""Paired 10 cm hydrographs for objectively selected smaller baseline events."""
import json
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from compare_builds import ROOT,FIXED,OUT

old=pd.read_parquet(ROOT/'analysis/rr10-daily.parquet')
new=pd.read_parquet(FIXED/'analysis/rr10-daily.parquet')
peaks,_=find_peaks(old.peak_m3s.to_numpy(),distance=7,prominence=.1)
threshold=float(np.median(old.peak_m3s.iloc[peaks]))
small=peaks[old.peak_m3s.iloc[peaks].to_numpy()<=threshold]
pct=100*(new.peak_m3s/old.peak_m3s-1)
chosen=[]
for p in sorted(small,key=lambda p:abs(pct.iloc[p]),reverse=True):
    if all(abs(int(p)-other)>10 for other in chosen):chosen.append(int(p))
    if len(chosen)==3:break
curves={}
for label,root in [('Original',ROOT),('Corrected',FIXED)]:
    h=pd.read_csv(root/'rr10/output/chan.out',sep=r'\s+',skiprows=6,header=None,names=['year','julian','element','channel','seconds','q'])
    h['time']=pd.to_datetime(h.year.astype(str),format='%Y')+pd.to_timedelta(h.julian-1,unit='D')+pd.to_timedelta(h.seconds,unit='s')
    curves[label]=h
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(3,2,figsize=(15,10))
records=[]
for row,p in enumerate(chosen):
    day=old.index[p];series=[]
    for label,color,style in [('Original','#273b54','-'),('Corrected','#d76328','--')]:
        h=curves[label];sub=h[(h.time>=day-pd.Timedelta(days=2))&(h.time<day+pd.Timedelta(days=3))].reset_index(drop=True)
        series.append(sub)
        axes[row,0].plot(sub.time,sub.q,label=label,color=color,ls=style)
    assert series[0].time.equals(series[1].time)
    axes[row,1].plot(series[0].time,series[1].q-series[0].q,color='#d76328')
    axes[row,0].set(title=f'{day:%Y-%m-%d} | daily peak change {pct.iloc[p]:+.1f}%',ylabel='Printed routed discharge (m³/s)')
    axes[row,1].set_ylabel('Corrected − original (m³/s)')
    axes[row,0].legend()
    records.append({'date':str(day.date()),'original_daily_peak_m3s':float(old.peak_m3s.iloc[p]),'corrected_daily_peak_m3s':float(new.peak_m3s.iloc[p]),'peak_change_percent':float(pct.iloc[p])})
for ax in axes.flat:
    ax.grid(alpha=.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
fig.suptitle('Smaller events | original versus corrected 10 cm hydrographs',fontsize=15)
fig.text(.07,.02,f'Original outlet local peaks: ≥7 days apart, prominence ≥0.1 m³/s. Smaller = lower half (≤{threshold:.3f} m³/s).\nThree largest absolute relative peak changes selected; examples are sensitivity-focused, not typical. Hydrograph volume discrepancy remains unresolved.',fontsize=10)
fig.tight_layout(rect=[0,.075,1,.95])
fig.savefig(OUT/'figure-4-smaller-events.png',dpi=180)
(OUT/'smaller-event-selection.json').write_text(json.dumps({'definition':'lower half of original daily outlet local peaks; distance>=7d and prominence>=0.1m3/s','threshold_m3s':threshold,'events':records},indent=2)+'\n')
print(records)
