#!/usr/bin/env python3
"""Daily yield and routed-discharge comparison; no fitted or shifted series."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.signal import find_peaks

ROOT = Path('/workdir/warming-combined-release-20261007')
CASES = ['legacy10', 'combined10', 'legacy17']
LABELS = ['260803 · 10 cm (baseline)', '261007 · 10 cm (combined)', '260803 · 17 cm']
COLOURS = ['#263b53', '#da6527', '#148578']
STYLES = ['-', '--', ':']
DATES = pd.date_range('1980-01-01', '2003-12-31')


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def refresh_manifest():
    out=ROOT/'analysis'
    save(out/'analysis-manifest.json',{p.name:sha(p) for p in sorted(out.iterdir())
        if p.is_file() and p.name!='analysis-manifest.json' and p.suffix!='.log'})


def metrics(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    if x.ndim != 1 or x.shape != y.shape or len(x) < 2:
        raise ValueError('Expected equal one-dimensional series with at least two rows')
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Non-finite metric inputs')
    d = y-x; sx = float(x.std()); sy = float(y.std()); mx = float(x.mean())
    r = float(np.clip(np.corrcoef(x,y)[0,1], -1, 1)) if sx and sy else None
    alpha = sy/sx if sx else None
    beta = float(y.mean()/mx) if mx else None
    nse = float(1-np.sum(d*d)/np.sum((x-mx)**2)) if sx else None
    kge = float(1-np.sqrt((r-1)**2+(alpha-1)**2+(beta-1)**2)) if r is not None and beta is not None else None
    valid = x > 0
    pct = 100*d[valid]/x[valid]
    return dict(n=len(x), NSE=nse, KGE2009=kge, R2=r*r if r is not None else None,
        r=r, alpha=alpha, beta=beta, bias_percent=100*(beta-1) if beta is not None else None,
        RMSE=float(np.sqrt(np.mean(d*d))), MAE=float(np.abs(d).mean()),
        max_abs_difference=float(np.abs(d).max()), reference_mean=mx,
        comparison_mean=float(y.mean()), positive_reference_n=int(valid.sum()),
        percent_change_min=float(pct.min()) if len(pct) else None,
        percent_change_max=float(pct.max()) if len(pct) else None,
        records_above_1_percent=int((np.abs(pct)>1).sum()),
        absolute_difference_quantiles={str(q):float(np.quantile(np.abs(d),q)) for q in [.5,.9,.95,.99,1.]})


def check_dates(index):
    if not index.equals(DATES):
        raise ValueError('Dates must equal the unique ordered complete 1980–2003 record')


def convert(cases=CASES):
    import wepppyo3.wepp_interchange as native
    from wepppy.wepp.interchange.totalwatsed3 import run_totalwatsed3
    from wepppy.wepp.interchange.versioning import INTERCHANGE_VERSION as version
    for lane in cases:
        assert json.loads((ROOT/lane/'watershed.json').read_text())['success']
        assert (ROOT/lane/'outputs.json').exists()
        raw = ROOT/lane/'output'; dest = raw/'interchange'
        dest.mkdir(exist_ok=False)
        conversions = {}
        for kind in ['pass','wat']:
            paths = sorted(raw.glob('H*.'+kind+'.dat'))
            assert len(paths) == 864
            result = getattr(native,'hillslope_'+kind+'_files_to_parquet')(
                [str(p) for p in paths], str(dest/('H.'+kind+'.parquet')), version.major, version.minor)
            assert result['rejected_records'] == 0, result
            expected = 864*8766 if kind == 'pass' else 1904*8766
            assert result['rows_written'] == result['accepted_records'] == expected, result
            conversions[kind] = result
            print('CONVERTED', lane, kind, result, flush=True)
        run_totalwatsed3(dest, SimpleNamespace(gwstorage=0.,bfcoeff=.04,dscoeff=0.))
        save(ROOT/'analysis'/(lane+'-conversion.json'), conversions)


def numeric(path, count):
    rows=[]
    with path.open() as f:
        for line in f:
            tokens=line.split()
            if len(tokens) != count:
                continue
            try:
                rows.append([float(t) for t in tokens])
            except ValueError:
                continue
    a=np.array(rows)
    assert a.ndim == 2 and np.isfinite(a).all(), path
    return a


def read_lane(lane):
    raw=ROOT/lane/'output'
    tw=pd.read_parquet(raw/'interchange/totalwatsed3.parquet')
    tw.index=pd.DatetimeIndex(pd.to_datetime(dict(year=tw.year, month=tw.month, day=tw.day_of_month)))
    check_dates(tw.index)
    assert np.isfinite(tw[['Streamflow','Area','Runoff','Lateral Flow','Baseflow']]).all().all()
    assert (tw.Streamflow >= 0).all()
    # Summed binary floating-point areas differ from decimal text by ~4e-9 m².
    assert tw.Area.nunique() == 1 and np.allclose(tw.Area,19258143.09,rtol=0,atol=1e-6)
    assert np.allclose(tw.Streamflow,tw.Runoff+tw['Lateral Flow']+tw.Baseflow,rtol=1e-12,atol=1e-12)
    daily=pd.DataFrame(index=DATES)
    daily['totalwatsed_m3s']=tw.Streamflow*tw.Area/1000/86400
    for k in ['Runoff','Lateral Flow','Baseflow']:
        daily[k+'_mm']=tw[k]
    a=numeric(raw/'chan.out',6)
    assert (a[:,2] == 1235).all() and (a[:,3] == 371).all()
    days=pd.DatetimeIndex(pd.to_datetime(a[:,0].astype(int).astype(str),format='%Y')+pd.to_timedelta(a[:,1]-1,unit='D'))
    h=pd.DataFrame(dict(day=days, seconds=a[:,4], q=a[:,5]))
    assert not h.duplicated(['day','seconds']).any() and (h.q >= 0).all()
    groups=h.groupby('day',sort=True); counts=groups.size()
    check_dates(counts.index)
    assert counts.isin([1,144]).all()
    full=h[h.day.isin(counts[counts == 144].index)]
    assert (full.seconds.to_numpy().reshape(-1,144) == np.arange(600,86401,600)).all()
    sparse=h[h.day.isin(counts[counts == 1].index)]
    assert (sparse.seconds == 86400).all()
    h['weight_s']=np.where(h.day.isin(counts[counts == 1].index),86400.,600.)
    h['volume']=h.q*h.weight_s
    # chan.out's E-format discharge has three significant digits. This bounds
    # decimal rounding of samples, not routing quadrature error.
    h['rounding_volume']=np.where(h.q>0,.5*10**(np.floor(np.log10(np.maximum(h.q,1e-99)))-2),0)*h.weight_s
    daily['channel_m3s']=h.groupby('day').volume.sum()/86400
    daily['sampled_peak_m3s']=groups.q.max()
    daily['first_peak_second']=h.loc[groups.q.idxmax()].set_index('day').seconds
    daily['rounding_bound_m3']=h.groupby('day').rounding_volume.sum()
    a=numeric(raw/'chanwb.out',10)
    wbdates=pd.DatetimeIndex(pd.to_datetime(a[:,0].astype(int).astype(str),format='%Y')+pd.to_timedelta(a[:,1]-1,unit='D'))
    check_dates(wbdates)
    assert (a[:,2] == 1235).all() and (a[:,3] == 371).all()
    daily['ledger_m3']=a[:,5]
    e=numeric(raw/'ebe_pw0.txt',11)
    assert (e[:,-1] == 1235).all()
    e_dates=pd.DatetimeIndex(pd.to_datetime(dict(year=e[:,2].astype(int)+1979,month=e[:,1].astype(int),day=e[:,0].astype(int))))
    assert e_dates.is_unique
    ebe=pd.Series(e[:,4],index=e_dates)
    assert np.allclose(ebe,daily.loc[e_dates,'ledger_m3'],atol=.021,rtol=0)
    assert (daily.loc[~daily.index.isin(e_dates),'ledger_m3'] <= .01).all()
    daily['ebe_peak_m3s']=pd.Series(e[:,5],index=e_dates)
    daily['integral_minus_ledger_m3']=daily.channel_m3s*86400-daily.ledger_m3
    # Sparse days are published daily averages. Expand only for explicitly
    # labelled equal-weight 600-second comparison, retaining the source count.
    grid=pd.MultiIndex.from_product([DATES,np.arange(600,86401,600)],names=['day','seconds'])
    dense=h.set_index(['day','seconds']).q.reindex(grid).unstack('seconds')
    if len(sparse):
        dense.loc[sparse.day] = np.repeat(sparse.q.to_numpy()[:,None],144,axis=1)
    assert np.isfinite(dense.to_numpy()).all()
    dense.index.name='day'
    q=dense.to_numpy().ravel()
    timestamps=pd.DatetimeIndex(np.repeat(DATES.values,144))+pd.to_timedelta(np.tile(np.arange(600,86401,600),len(DATES)),unit='s')
    series=pd.Series(q,index=timestamps,name=lane)
    audit=dict(days=len(daily), area_m2=float(tw.Area.iloc[0]), raw_hydrograph_rows=len(h), sparse_daily_average_days=len(sparse),
        totalwatsed_m3=float(daily.totalwatsed_m3s.sum()*86400),
        channel_integral_m3=float(daily.channel_m3s.sum()*86400), ledger_m3=float(daily.ledger_m3.sum()),
        integral_minus_ledger_m3=float(daily.integral_minus_ledger_m3.sum()),
        integral_minus_ledger_percent=float(100*daily.integral_minus_ledger_m3.sum()/daily.ledger_m3.sum()),
        sample_printing_bound_m3=float(daily.rounding_bound_m3.sum()),
        component_mean_annual_mm={k:float(tw[k].sum()/24) for k in ['Runoff','Lateral Flow','Baseflow']})
    audit['extrema']={field:dict(minimum=float(daily[field].min()),maximum=float(daily[field].max()),
                               maximum_date=str(daily[field].idxmax().date()))
                      for field in ['totalwatsed_m3s','channel_m3s','sampled_peak_m3s']}
    return daily, series, audit


def choose_events(data, field):
    base=data['legacy10'][field]
    peaks,_=find_peaks(base.to_numpy(),distance=7,prominence=.1)
    assert len(peaks) >= 4
    threshold=float(base.iloc[peaks].median())
    departures=pd.concat([(data[c][field]-base).abs()/base.replace(0,np.nan) for c in CASES[1:]],axis=1).max(axis=1)
    small=[int(p) for p in peaks if base.iloc[p] <= threshold]
    picked=[]
    for p in sorted(small,key=lambda p:departures.iloc[max(0,p-3):p+4].max(),reverse=True):
        if all(abs(p-j)>10 for j in picked):
            picked.append(p)
        if len(picked)==3:
            break
    extreme=int(np.argmax(base.to_numpy()))
    return [extreme]+picked, dict(peak_count=len(peaks), small_count=len(small),small_threshold_m3s=threshold,
        selection='Baseline maximum plus three non-overlapping lower-half baseline local peaks ranked by largest relative departure of either comparison within ±3 days; distance 7 days, prominence 0.1 m³/s.',
        dates=[str(base.index[p].date()) for p in [extreme]+picked])


def plots(data, subdaily, out, summary):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fields=['totalwatsed_m3s','channel_m3s']
    titles=['Totalwatsed daily streamflow','Routed outlet daily mean discharge']
    fig,ax=plt.subplots(2,2,figsize=(15,8),sharex=True)
    for j,(field,title) in enumerate(zip(fields,titles)):
        for c,label,col,style in zip(CASES,LABELS,COLOURS,STYLES):
            y=data[c][field]
            ax[0,j].plot(DATES,y,color=col,ls=style,lw=.7,label=label)
            if c != 'legacy10':
                ax[1,j].plot(DATES,y-data['legacy10'][field],color=col,ls=style,lw=.7,label=label)
        ax[0,j].set(title=title,ylabel='Daily mean flow (m³/s)')
        ax[1,j].set(ylabel='Comparison − baseline (m³/s)')
        ax[0,j].legend(fontsize=8)
    for a in ax.flat:a.grid(alpha=.2)
    fig.suptitle('Warming-championship | full 1980–2003 comparison')
    fig.tight_layout();fig.savefig(out/'figure-1-daily-hydrographs.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(2,2,figsize=(13,10))
    for j,(field,title) in enumerate(zip(fields,titles)):
        x=data['legacy10'][field]
        lim=max(data[c][field].max() for c in CASES)
        ax[0,j].plot([0,lim],[0,lim],color='grey',lw=1,label='1:1')
        for c,label,col in zip(CASES[1:],LABELS[1:],COLOURS[1:]):
            ax[0,j].scatter(x,data[c][field],s=5,alpha=.35,color=col,label=label)
        ax[0,j].set(title=title,xlabel='Baseline (m³/s)',ylabel='Comparison (m³/s)')
        ax[0,j].legend(fontsize=8)
        for c,label,col,style in zip(CASES,LABELS,COLOURS,STYLES):
            ax[1,j].plot(100*(np.arange(len(DATES))+.5)/len(DATES),np.sort(data[c][field])[::-1],color=col,ls=style,label=label)
        ax[1,j].set(xlabel='Exceedance (%)',ylabel='Daily mean flow (m³/s)',yscale='log')
        ax[1,j].legend(fontsize=8)
    for a in ax.flat:a.grid(alpha=.2)
    fig.suptitle('Agreement and flow-duration curves | no fitting or time shift')
    fig.tight_layout();fig.savefig(out/'figure-2-fit-flow-duration.png',dpi=180);plt.close(fig)
    selections={}
    for field,number in [('totalwatsed_m3s',3),('sampled_peak_m3s',4)]:
        events,selection=choose_events(data,field); selections[field]=selection
        fig,axes=plt.subplots(4,2,figsize=(15,13))
        event_records=[]
        for row,p in enumerate(events):
            day=DATES[p]; lo=day-pd.Timedelta(days=3); hi=day+pd.Timedelta(days=4)
            curves={c:(data[c].loc[(DATES>=lo)&(DATES<hi),field] if number==3 else subdaily[c].loc[(subdaily[c].index>lo)&(subdaily[c].index<=hi)]) for c in CASES}
            plotted=pd.DataFrame(curves)
            saved=out/f'figure-{number}-event-{day:%Y%m%d}.parquet'
            plotted.to_parquet(saved)
            assert pd.read_parquet(saved).equals(plotted)
            for c,label,col,style in zip(CASES,LABELS,COLOURS,STYLES):
                axes[row,0].plot(curves[c].index,curves[c],color=col,ls=style,label=label,lw=1.3)
                if c!='legacy10':axes[row,1].plot(curves[c].index,curves[c]-curves['legacy10'],color=col,ls=style,label=label)
            axes[row,0].set(title=f'{day:%Y-%m-%d} | '+('baseline maximum' if row==0 else 'sensitivity-selected smaller event'),ylabel='Flow (m³/s)')
            axes[row,1].set(ylabel='Comparison − baseline (m³/s)')
            record={'date':str(day.date()),'cases':{}}
            for c in CASES:
                q=curves[c]
                record['cases'][c]=dict(peak=float(q.max()),first_peak=str(q.idxmax()),
                    volume_m3=float(q.sum()*(86400 if number==3 else 600)),
                    metrics_vs_baseline=metrics(curves['legacy10'],q))
            event_records.append(record)
            for a in axes[row]:
                a.grid(alpha=.2);a.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            if row==0:axes[row,0].legend(fontsize=8)
        selection['events']=event_records
        fig.suptitle('Totalwatsed daily events' if number==3 else 'Routed outlet 600-second event hydrographs',fontsize=15)
        fig.text(.06,.012,'Smaller-event examples deliberately target departures; they are not a random or typical-event sample.',fontsize=10)
        fig.tight_layout(rect=[0,.025,1,.97]);fig.savefig(out/f'figure-{number}-events.png',dpi=180);plt.close(fig)
    save(out/'event-selection.json',selections)
    fig,ax=plt.subplots(2,1,figsize=(14,8),sharex=True)
    for c,label,col,style in zip(CASES,LABELS,COLOURS,STYLES):
        d=data[c]
        ax[0].plot(DATES,d.integral_minus_ledger_m3.cumsum()/1e6,label=label,color=col,ls=style)
        ax[1].plot(DATES,d.integral_minus_ledger_m3,label=label,color=col,ls=style,lw=.7)
    ax[0].set(ylabel='Cumulative discrepancy (million m³)',title='Sampled outlet integral minus channel volume ledger')
    ax[1].set(ylabel='Daily discrepancy (m³)')
    for a in ax:a.grid(alpha=.2)
    ax[0].legend();fig.tight_layout();fig.savefig(out/'figure-5-channel-ledger.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(15,10))
    sentinels=[]
    for row,date in enumerate(['1994-10-27','1992-11-21','1996-02-06']):
        day=pd.Timestamp(date);lo=day-pd.Timedelta(days=2);hi=day+pd.Timedelta(days=3)
        curves={c:subdaily[c].loc[(subdaily[c].index>lo)&(subdaily[c].index<=hi)] for c in CASES}
        pd.DataFrame(curves).to_parquet(out/f'sentinel-{date}.parquet')
        records={}
        for c,label,col,style in zip(CASES,LABELS,COLOURS,STYLES):
            q=curves[c];d=data[c].loc[(DATES>=lo)&(DATES<hi)]
            integral=float(q.sum()*600);ledger=float(d.ledger_m3.sum())
            records[c]=dict(integral_m3=integral,ledger_m3=ledger,
                integral_minus_ledger_percent=100*(integral/ledger-1),
                sample_printing_bound_m3=float(d.rounding_bound_m3.sum()),
                sampled_peak_m3s=float(q.max()),first_peak=str(q.idxmax()),
                metrics_vs_baseline=metrics(curves['legacy10'],q))
            axes[row,0].plot(q.index,q,color=col,ls=style,label=label)
            if c!='legacy10':axes[row,1].plot(q.index,q-curves['legacy10'],color=col,ls=style)
        sentinels.append(dict(centre=date,start=str(lo.date()),end_exclusive=str(hi.date()),cases=records))
        axes[row,0].set(title=f'{date} | retained diagnostic window',ylabel='Outlet discharge (m³/s)')
        axes[row,1].set(ylabel='Comparison − baseline (m³/s)')
        for a in axes[row]:a.grid(alpha=.2);a.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    axes[0,0].legend(fontsize=8)
    fig.suptitle('Routed hydrographs | three windows retained from the earlier investigation')
    fig.tight_layout();fig.savefig(out/'figure-6-retained-windows.png',dpi=180);plt.close(fig)
    save(out/'retained-window-assessment.json',sentinels)


def main(do_convert):
    out=ROOT/'analysis';out.mkdir(exist_ok=True)
    assert all((ROOT/c/'outputs.json').exists() and
               json.loads((ROOT/c/'watershed.json').read_text())['success'] for c in CASES), 'All physical cases must complete first'
    if do_convert:convert()
    data={};subdaily={};summary={'baseline':'legacy10','cases':{},'fits':{},'provisional_screen':{}}
    for lane in CASES:
        data[lane],subdaily[lane],summary['cases'][lane]=read_lane(lane)
        data[lane].to_parquet(out/(lane+'-daily.parquet'))
        assert pd.read_parquet(out/(lane+'-daily.parquet')).equals(data[lane])
    for c in CASES[1:]:
        assert summary['cases'][c]['area_m2'] == summary['cases']['legacy10']['area_m2']
        summary['fits'][c]={field:metrics(data['legacy10'][field],data[c][field]) for field in ['totalwatsed_m3s','channel_m3s','sampled_peak_m3s']}
        summary['fits'][c]['channel_600s_m3s']=metrics(subdaily['legacy10'],subdaily[c])
        for field in ['totalwatsed_m3s','channel_m3s']:
            m=summary['fits'][c][field]
            summary['provisional_screen'][c+'_'+field]=abs(m['bias_percent'])<=.1 and m['NSE']>=.999 and m['KGE2009']>=.999 and m['R2']>=.999
        summary['fits'][c]['annual']={field:{str(y):metrics(data['legacy10'].loc[str(y),field],data[c].loc[str(y),field]) for y in range(1980,2004)} for field in ['totalwatsed_m3s','channel_m3s']}
        summary['fits'][c]['largest_daily_departures']={}
        summary['fits'][c]['baseline_flow_quartiles']={}
        for field in ['totalwatsed_m3s','channel_m3s']:
            x=data['legacy10'][field]; y=data[c][field]
            edges=np.quantile(x,[0,.25,.5,.75,1])
            bins={}
            for j in range(4):
                mask=(x>=edges[j]) & ((x<edges[j+1]) if j<3 else (x<=edges[j+1]))
                bins[str(j+1)]={'lower_m3s':float(edges[j]),'upper_m3s':float(edges[j+1]),
                                'metrics':metrics(x[mask],y[mask])}
            summary['fits'][c]['baseline_flow_quartiles'][field]=bins
        for field in ['totalwatsed_m3s','channel_m3s','sampled_peak_m3s']:
            delta=data[c][field]-data['legacy10'][field]
            summary['fits'][c]['largest_daily_departures'][field]=[
                dict(date=str(day.date()),baseline=float(data['legacy10'].loc[day,field]),
                     comparison=float(data[c].loc[day,field]),difference=float(delta.loc[day]))
                for day in delta.abs().nlargest(10).index]
    paired=pd.concat({c:data[c] for c in CASES},axis=1)
    paired.to_parquet(out/'paired-daily.parquet')
    save(out/'metrics.json',summary)
    plots(data,subdaily,out,summary)
    refresh_manifest()
    print(json.dumps({c:{k:v for k,v in fits.items() if k!='annual'} for c,fits in summary['fits'].items()},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--skip-conversion',action='store_true')
    parser.add_argument('--convert-lane',choices=CASES)
    args=parser.parse_args()
    if args.convert_lane:
        (ROOT/'analysis').mkdir(exist_ok=True)
        convert([args.convert_lane])
    else:
        main(not args.skip_conversion)
