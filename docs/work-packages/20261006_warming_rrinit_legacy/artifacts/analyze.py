#!/usr/bin/env python3
"""Fresh-output analysis for the bounded warming-championship experiment."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1])
OUT = ROOT/'analysis'
OUT.mkdir(exist_ok=True)
LANES = ['rr10', 'rr17', 'rr60']
COLORS = ['#263b53', '#15947a', '#d35a28']
LABELS = ['10 cm (baseline)', '17 cm', '60 cm']
DATES = pd.date_range('1980-01-01', '2003-12-31', freq='D')


def numeric(path, count):
    records = []
    for line in path.read_text().splitlines():
        t = line.split()
        if len(t) != count:
            continue
        try:
            records.append([float(v) for v in t])
        except ValueError:
            continue
    a = np.array(records)
    assert a.ndim == 2 and np.isfinite(a).all(), path
    return a


def read_case(lane):
    out = ROOT/lane/'output'
    a = numeric(out/'ebe_pw0.txt', 11)
    assert (a[:,-1] == 1235).all()
    dates = pd.to_datetime({'year':a[:,2].astype(int)+1979,
                            'month':a[:,1].astype(int), 'day':a[:,0].astype(int)})
    e = pd.DataFrame({'volume_m3':a[:,4], 'peak_m3s':a[:,5],
                      'sediment_kg':a[:,6]}, index=pd.DatetimeIndex(dates))
    assert e.index.is_unique
    # Missing EBE rows mean below the report's 0.005 m3 threshold, not necessarily
    # zero. Do not synthesize volumes for them.
    a = numeric(out/'chan.out', 6)
    assert (a[:,2] == 1235).all() and (a[:,3] == 371).all()
    days = pd.DatetimeIndex(pd.to_datetime(a[:,0].astype(int).astype(str), format='%Y') + pd.to_timedelta(a[:,1]-1, unit='D'))
    h = pd.DataFrame({'day': days, 'time_s':a[:,4], 'q_m3s':a[:,5]})
    assert np.array_equal(h.day.drop_duplicates().values, DATES.values)
    assert not h.duplicated(['day','time_s']).any()
    assert (h.q_m3s >= 0).all()
    groups = h.groupby('day', sort=True)
    counts = groups.size()
    assert counts.isin([1,144]).all(), counts.value_counts()
    full = h[h.day.isin(counts[counts == 144].index)]
    assert (full.time_s.to_numpy().reshape(-1,144) == np.arange(600,86401,600)).all()
    sparse = h[h.day.isin(counts[counts == 1].index)]
    assert (sparse.time_s == 86400).all()
    # Peaks in chan.out have three significant digits; preserve plateau ambiguity.
    idx = groups.q_m3s.idxmax()
    d = h.loc[idx, ['day','time_s','q_m3s']].set_index('day')
    d.columns = ['first_printed_peak_time_s','printed_peak_m3s']
    d['peak_plateau_samples'] = groups.q_m3s.apply(lambda x: int((x == x.max()).sum()))
    d = d.join(e)
    assert d.index.equals(DATES)
    matched = d.dropna()
    assert np.allclose(matched.printed_peak_m3s, matched.peak_m3s, rtol=.006, atol=.00001)
    wb=numeric(out/'chanwb.out',10)
    wbdates=pd.DatetimeIndex(pd.to_datetime(wb[:,0].astype(int).astype(str),format='%Y')+pd.to_timedelta(wb[:,1]-1,unit='D'))
    assert wbdates.equals(DATES)
    assert (wb[:,2]==1235).all() and (wb[:,3]==371).all()
    d['channel_wb_outflow_m3']=wb[:,5]
    d['printed_hydrograph_integral_m3']=groups.q_m3s.sum()*600
    d.loc[counts==1,'printed_hydrograph_integral_m3']=groups.q_m3s.sum()[counts==1]*86400
    omitted=d[d.volume_m3.isna()]
    assert (omitted.channel_wb_outflow_m3<=.01).all(), 'Missing non-negligible EBE rows'
    readback=d.dropna(subset=['volume_m3'])
    assert np.allclose(readback.volume_m3,readback.channel_wb_outflow_m3,rtol=0,atol=.021)
    h['datetime'] = h.day + pd.to_timedelta(h.time_s, unit='s')
    return d, h, {'days':len(d), 'ebe_days':len(e), 'hydrograph_rows':len(h),
                  'single_sample_days':len(sparse), 'missing_ebe_days':int(d.volume_m3.isna().sum()),
                  'max_abs_printed_channel_balance_m3':float(np.abs(wb[:,-1]).max()),
                  'hydrograph_integral_vs_reported_volume_pct':float(100*(d.printed_hydrograph_integral_m3.sum()/d.volume_m3.sum()-1)),
                  'ebe_channel_volume_readback_max_abs_m3':float(np.abs(readback.volume_m3-readback.channel_wb_outflow_m3).max())}


if len(sys.argv)>2:
    d,h,v=read_case(sys.argv[2])
    print(json.dumps(v,indent=2))
    print('volume_m3',d.volume_m3.sum(),'peak_m3s',d.peak_m3s.max())
    sys.exit(0)

daily, hydro, validation = {}, {}, {}
for lane in LANES:
    daily[lane], hydro[lane], validation[lane] = read_case(lane)
    daily[lane].to_parquet(OUT/f'{lane}-daily.parquet')

base = daily['rr10']
summary = {'scope':'Original wepp_260803 build; only initial 10 cm records changed.',
           'validation':validation, 'cases':{}}
for lane in LANES:
    d = daily[lane]
    paired = d[['volume_m3','peak_m3s']].join(base[['volume_m3','peak_m3s']], rsuffix='_base').dropna()
    valid = paired[paired.peak_m3s_base > .01]
    ratio = valid.peak_m3s / valid.peak_m3s_base
    shift = (d.first_printed_peak_time_s-base.first_printed_peak_time_s)/3600
    # Daily peak timing is ambiguous when the printed discharge plateau is tied.
    unique = (d.peak_plateau_samples == 1) & (base.peak_plateau_samples == 1) & (base.peak_m3s > .01)
    summary['cases'][lane] = dict(total_reported_volume_m3=float(d.volume_m3.sum()),
        volume_change_pct=float(100*(d.volume_m3.sum()/base.volume_m3.sum()-1)),
        maximum_daily_peak_m3s=float(d.peak_m3s.max()),
        maximum_peak_date=str(d.peak_m3s.idxmax().date()),
        peak_ratio_threshold_m3s=.01, peak_ratio_count=len(ratio),
        peak_ratio_quantiles={str(q):float(ratio.quantile(q)) for q in [.05,.25,.5,.75,.95]},
        peak_ratio_min=float(ratio.min()),peak_ratio_max=float(ratio.max()),
        days_peak_change_over_one_percent=int((np.abs(ratio-1)>.01).sum()),
        maximum_paired_peak_increase_m3s=float((paired.peak_m3s-paired.peak_m3s_base).max()),
        maximum_paired_peak_decrease_m3s=float((paired.peak_m3s-paired.peak_m3s_base).min()),
        paired_higher_peak_days=int((paired.peak_m3s>paired.peak_m3s_base).sum()),
        paired_lower_peak_days=int((paired.peak_m3s<paired.peak_m3s_base).sum()),
        unique_printed_peak_timing_days=int(unique.sum()),
        median_unique_peak_shift_hours=float(shift[unique].median()) if unique.any() else None)

plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False,
                     'figure.dpi':150, 'savefig.dpi':180})
fig, axes = plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
for lane,color,label in zip(LANES,COLORS,LABELS):
    d=daily[lane]
    axes[0].plot(d.index,d.peak_m3s,color=color,lw=.65,label=label,alpha=.8)
    axes[1].plot(d.index,d.volume_m3.cumsum()/1e6,color=color,label=label)
axes[0].set(ylabel='Daily peak (m³/s)',title='1 · Outlet response across the full 1980–2003 simulation')
axes[0].legend(ncol=3)
axes[1].set(ylabel='Cumulative reported runoff (million m³)',xlabel='Calendar year')
fig.savefig(OUT/'figure-1.png'); plt.close(fig)

# Select three highest baseline peaks separated by at least seven days.
selected=[]
for date in base.peak_m3s.sort_values(ascending=False).index:
    if all(abs((date-other).days)>7 for other in selected):
        selected.append(date)
    if len(selected)==3:
        break
summary['hydrograph_selection'] = [str(d.date()) for d in selected]
summary['selected_events'] = []
for date in selected:
    event = {'baseline_peak_day':str(date.date()), 'cases':{}}
    start = date-pd.Timedelta(days=2)
    end = date+pd.Timedelta(days=3)
    for lane in LANES:
        h=hydro[lane]
        sub=h[(h.day>=start)&(h.day<end)]
        assert len(sub)==5*144, 'Selected event must have full timestep output'
        weights=sub.q_m3s.to_numpy()*600
        hours=(sub.datetime-start).dt.total_seconds().to_numpy()/3600
        peak=sub.q_m3s.max()
        ties=sub[sub.q_m3s==peak]
        centroid=float(np.average(hours,weights=weights))
        q=sub.q_m3s.to_numpy()
        eps=np.where(q>0,.5*10.0**(np.floor(np.log10(np.maximum(q,1e-99)))-2),0)
        rounding_bound=float(np.sum(eps*np.abs(hours-centroid))/(q.sum()-eps.sum()))
        event['cases'][lane] = dict(printed_peak_m3s=float(peak),
            first_printed_peak=str(ties.datetime.min()),
            last_printed_peak=str(ties.datetime.max()),
            printed_peak_tied_samples=len(ties),
            hydrograph_integral_m3=float(weights.sum()),
            discharge_centroid_hours_from_window_start=centroid,
            centroid_rounding_bound_minutes=60*rounding_bound)
    summary['selected_events'].append(event)
fig, axes=plt.subplots(3,2,figsize=(14,9),layout='constrained')
for (ax,delta),date in zip(axes,selected):
    reference=None
    for lane,color,label in zip(LANES,COLORS,LABELS):
        h=hydro[lane]
        subset=h[(h.datetime>=date-pd.Timedelta(days=2)) & (h.datetime<=date+pd.Timedelta(days=3))]
        ax.plot(subset.datetime,subset.q_m3s,color=color,label=label,lw=1.1)
        if reference is None:
            reference=subset.q_m3s.to_numpy()
        else:
            assert len(subset)==len(reference)
            delta.plot(subset.datetime,subset.q_m3s.to_numpy()-reference,color=color,label=label,lw=1)
    ax.set(ylabel='Discharge (m³/s)',title=f'Baseline peak day: {date:%Y-%m-%d}')
    delta.axhline(0,color='gray',lw=.7)
    delta.set(ylabel='Δ discharge (m³/s)',title='Scenario minus 10 cm (rounded hydrograph output)')
axes[0,0].legend(loc='upper right',frameon=False)
fig.suptitle('2 · Ten-minute outlet hydrographs around the three largest separated baseline peaks')
fig.savefig(OUT/'figure-2.png'); plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
for lane,color,label in zip(LANES[1:],COLORS[1:],LABELS[1:]):
    d=daily[lane]
    axes[0].scatter(base.peak_m3s,d.peak_m3s,s=5,alpha=.25,color=color,label=label)
    valid=(base.peak_m3s>.01)&d.peak_m3s.notna()
    ratios=np.sort((d.peak_m3s[valid]/base.peak_m3s[valid]).to_numpy())
    axes[1].plot(ratios,np.arange(1,len(ratios)+1)/len(ratios),color=color,label=label)
    annual=d.volume_m3.groupby(d.index.year).sum()/base.volume_m3.groupby(base.index.year).sum()
    axes[2].plot(annual.index,100*(annual-1),color=color,label=label)
maxpeak=max(d.peak_m3s.max() for d in daily.values())
axes[0].plot([0,maxpeak],[0,maxpeak],ls='--',color='gray',lw=1)
axes[0].set(xlabel='Baseline daily peak (m³/s)',ylabel='Scenario daily peak (m³/s)',title='Daily peaks')
legend=axes[0].legend()
for handle in legend.legend_handles:
    handle.set_alpha(1)
axes[1].axvline(1,color='gray',ls='--',lw=1)
axes[1].set(xlabel='Scenario / baseline peak',ylabel='Cumulative fraction of days',title='Baseline peak > 0.01 m³/s')
axes[2].axhline(0,color='gray',ls='--',lw=1)
axes[2].set(xlabel='Calendar year',ylabel='Runoff-volume change (%)',title='Annual reported outlet runoff')
fig.suptitle('3 · Peak distribution and runoff-volume departures from 10 cm')
fig.savefig(OUT/'figure-3.png'); plt.close(fig)
summary['limitations'] = [
    'chan.out discharge has three significant digits; tied printed peaks make timing ambiguous.',
    'Centroid and hydrograph integrals use the printed 600-second samples; they are window statistics, not travel times.',
    'Runoff volume and daily peaks use EBE report precision, not rounded hydrograph samples.',
    'This tests initial rrinit; roughness evolution, infiltration, and rill-width feedback remain active.',
    'Only current 10 cm OFEs are changed. This is not a burned-versus-unburned experiment or physical calibration.'
]
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
