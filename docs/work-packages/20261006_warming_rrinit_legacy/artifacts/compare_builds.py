#!/usr/bin/env python3
"""Fresh native interchange and matched original/corrected scientific comparison."""
import hashlib
import json
import argparse
from pathlib import Path
from types import SimpleNamespace
import duckdb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import wepppyo3.wepp_interchange as native
from wepppy.wepp.interchange.totalwatsed3 import run_totalwatsed3
from wepppy.wepp.interchange.versioning import INTERCHANGE_VERSION as version

ROOT = Path('/workdir/warming-rrinit-legacy-20261006')
FIXED = Path('/workdir/warming-rrinit-20261006')
FIXED_TW = Path('/workdir/warming-rrinit-totalwatsed-20261006')
OUT = ROOT/'comparison'
OUT.mkdir(exist_ok=True)
CASES = ['rr10','rr17','rr60']
COLORS = ['#273b54','#128b91','#d76328']
DATES = pd.date_range('1980-01-01','2003-12-31')

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2)+'\n')

def build_interchange(cases=CASES):
    for case in cases:
        raw=ROOT/case/'output'; dest=raw/'interchange'
        dest.mkdir(exist_ok=True)
        for kind in ['pass','wat']:
            paths=sorted(raw.glob('H*.'+kind+'.dat'))
            assert len(paths)==864
            print('Converting',case,kind,flush=True)
            result=getattr(native,'hillslope_'+kind+'_files_to_parquet')(
                [str(p) for p in paths],str(dest/('H.'+kind+'.parquet')),
                version.major,version.minor)
            assert result['rejected_records']==0
            save(case+'-'+kind+'-conversion.json',result)
        run_totalwatsed3(dest,SimpleNamespace(gwstorage=0.,bfcoeff=.04,dscoeff=0.))

def stats(a,b):
    a=np.asarray(a); b=np.asarray(b)
    assert a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all()
    delta=b-a; valid=a>0
    pct=100*(b[valid]/a[valid]-1)
    return dict(n=len(a),reference_sum=float(a.sum()),comparison_sum=float(b.sum()),
        sum_change_percent=float(100*(b.sum()/a.sum()-1)) if a.sum() else None,
        changed=int(np.count_nonzero(delta)),max_abs_difference=float(np.abs(delta).max()),
        lower=int((delta<0).sum()),higher=int((delta>0).sum()),
        positive_reference_n=int(valid.sum()),min_percent=float(pct.min()) if len(pct) else None,
        max_percent=float(pct.max()) if len(pct) else None,
        above_one_percent=int((np.abs(pct)>1).sum()),
        percentiles={str(p):float(np.quantile(pct,p)) for p in [.01,.05,.5,.95,.99]} if len(pct) else {})

def main(convert=True):
    if convert:
        build_interchange()
    con=duckdb.connect()
    con.execute('SET threads=4')
    con.execute("SET memory_limit='4GB'")
    result={'direction':'comparison minus reference; cross-build reference=original and comparison=corrected',
            'cross_build':{},'within_build':{},'totalwatsed':{},'byte_parity':{}}
    outlet={}; tw={}
    for build,root in [('original',ROOT),('corrected',FIXED)]:
        outlet[build]={};tw[build]={}
        for case in CASES:
            d=pd.read_parquet(root/'analysis'/(case+'-daily.parquet'))
            assert d.index.equals(DATES)
            outlet[build][case]=d
            p=(ROOT/case/'output/interchange' if build=='original' else FIXED_TW/case)/'totalwatsed3.parquet'
            w=pd.read_parquet(p)
            dates=pd.DatetimeIndex(pd.to_datetime(dict(year=w.year,month=w.month,day=w.day_of_month)))
            assert dates.equals(DATES)
            assert np.allclose(w.Streamflow,w.Runoff+w['Lateral Flow']+w.Baseflow)
            w.index=dates; tw[build][case]=w
            result['totalwatsed'][build+'_'+case]={'total_m3':float((w.Streamflow*w.Area/1000).sum()),
                'mean_annual_mm':float(w.Streamflow.sum()/24),
                'component_annual_mm':{k:float(w[k].sum()/24) for k in ['Runoff','Lateral Flow','Baseflow']}}
        result['within_build'][build]={c:{k:stats(outlet[build]['rr10'][k],outlet[build][c][k]) for k in ['peak_m3s','volume_m3']} for c in CASES[1:]}
        for case in CASES[1:]:
            basepath=(ROOT/'rr10/output/interchange' if build=='original' else FIXED_TW/'rr10')/'H.pass.parquet'
            casepath=(ROOT/case/'output/interchange' if build=='original' else FIXED_TW/case)/'H.pass.parquet'
            pairs=con.execute(f"SELECT a.peakro AS a,b.peakro AS b FROM read_parquet('{basepath}') a JOIN read_parquet('{casepath}') b USING(wepp_id,year,julian) WHERE a.peakro>0.001").fetchnumpy()
            result['within_build'][build][case]['hillslope_peaks_above_0.001_m3s']=stats(pairs['a'],pairs['b'])
    for case in CASES:
        old=outlet['original'][case]; new=outlet['corrected'][case]
        record={k:stats(old[k],new[k]) for k in ['volume_m3','peak_m3s','printed_hydrograph_integral_m3','sediment_kg']}
        record['totalwatsed']={k:stats(tw['original'][case][k],tw['corrected'][case][k]) for k in ['Runoff','Lateral Flow','Baseflow','Streamflow']}
        matched=old[['volume_m3','peak_m3s']].join(new[['volume_m3','peak_m3s']],rsuffix='_corrected')
        matched['peak_change_percent']=100*(matched.peak_m3s_corrected/matched.peak_m3s-1)
        matched.to_parquet(OUT/(case+'-outlet-paired.parquet'))
        record['largest_outlet_peak_departures']=[]
        for day in matched.peak_change_percent.abs().nlargest(10).index:
            record['largest_outlet_peak_departures'].append({'date':str(day.date()),**{k:float(v) for k,v in matched.loc[day].items()}})
        before=json.loads((ROOT/case/'outputs.json').read_text()); after=json.loads((FIXED/case/'outputs.json').read_text())
        result['byte_parity'][case]={}
        for kind in ['wat','soil','pass','ebe','element','loss']:
            names=[n for n in before if n.startswith('H') and n.endswith('.'+kind+'.dat')]
            assert len(names)==864
            result['byte_parity'][case][kind]={'files':len(names),'identical':sum(before[n]==after[n] for n in names)}
        # Native PASS exposes daily hillslope peaks and volumes in m3/s and m3.
        oldp=ROOT/case/'output/interchange/H.pass.parquet'; newp=FIXED_TW/case/'H.pass.parquet'
        con.execute(f"CREATE OR REPLACE VIEW paired AS SELECT a.wepp_id,a.year,a.julian,a.runvol AS va,b.runvol AS vb,a.peakro AS pa,b.peakro AS pb,a.dur AS da,b.dur AS db FROM read_parquet('{oldp}') a JOIN read_parquet('{newp}') b USING(wepp_id,year,julian)")
        row=con.execute('SELECT count(*),count(*) FILTER(WHERE va<>vb),max(abs(vb-va)),sum(va),sum(vb),count(*) FILTER(WHERE pa<>pb),max(abs(pb-pa)),count(*) FILTER(WHERE da<>db) FROM paired').fetchone()
        assert row[0]==864*8766
        record['hillslope_pass']=dict(zip(['records','volume_changed','max_abs_volume_difference_m3','original_volume_m3','corrected_volume_m3','peak_changed','max_abs_peak_difference_m3s','duration_changed'],row))
        record['hillslope_pass']['peak_below_daily_mean_original']=con.execute('SELECT wepp_id,year,julian,va,pa FROM paired WHERE va>0 AND pa*86400<va*0.999').fetchall()
        record['hillslope_pass']['peak_below_daily_mean_corrected']=con.execute('SELECT wepp_id,year,julian,vb,pb FROM paired WHERE vb>0 AND pb*86400<vb*0.999').fetchall()
        # Retain substantial peaks separately to avoid unstable ratios near zero.
        for threshold in [0.,.001,.01]:
            rows=con.execute(f'SELECT pa,pb FROM paired WHERE pa>{threshold}').fetchnumpy()
            record['hillslope_pass']['peak_reference_above_'+str(threshold)+'_m3s']=stats(rows['pa'],rows['pb'])
        top=con.execute('SELECT *,100*(pb/pa-1) AS peak_change_percent FROM paired WHERE pa>0.001 ORDER BY abs(pb-pa) DESC LIMIT 30').fetchdf()
        top.to_parquet(OUT/(case+'-hillslope-largest-departures.parquet'))
        for direction,order in [('increases','DESC'),('decreases','ASC')]:
            con.execute(f'SELECT *,100*(pb/pa-1) AS peak_change_percent FROM paired WHERE pa>0.001 ORDER BY pb-pa {order} LIMIT 30').fetchdf().to_parquet(OUT/(case+'-hillslope-'+direction+'.parquet'))
        result['cross_build'][case]=record
        print('Compared',case,record['peak_m3s'],flush=True)
    save('summary.json',result)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(15,9),sharey='row',layout='constrained')
    for col,build in enumerate(['original','corrected']):
        for case,color in zip(CASES,COLORS):
            d=outlet[build][case]
            axes[0,col].plot(DATES,d.peak_m3s,color=color,lw=.7,label=case[2:]+' cm')
            if case!='rr10':
                pct=100*(d.peak_m3s/outlet[build]['rr10'].peak_m3s-1)
                axes[1,col].plot(DATES,pct,color=color,lw=.7)
        axes[0,col].set_title(build.capitalize()+' build')
        axes[0,col].legend(ncol=3)
        axes[0,col].set_ylabel('Routed outlet daily peak (m³/s)')
        axes[1,col].set_ylabel('Peak change from 10 cm (%)')
        axes[1,col].axhline(0,color='gray',lw=.6)
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle('Roughness sensitivity | original wepp_260803 versus surface-return correction')
    fig.savefig(OUT/'figure-1-build-roughness.png',dpi=180);plt.close(fig)
    old=outlet['original']['rr10']; new=outlet['corrected']['rr10']
    pct=100*(new.peak_m3s/old.peak_m3s-1)
    fig,axes=plt.subplots(3,1,figsize=(14,10),sharex=True,layout='constrained')
    axes[0].plot(DATES,old.peak_m3s,label='Original 10 cm',color='#273b54',lw=.8)
    axes[0].plot(DATES,new.peak_m3s,label='Corrected 10 cm',color='#d76328',lw=.8,ls='--')
    axes[0].set_ylabel('Outlet daily peak (m³/s)');axes[0].legend()
    axes[1].plot(DATES,pct,color='#d76328',lw=.7);axes[1].set_ylabel('Corrected − original peak (%)')
    axes[2].plot(DATES,new.volume_m3-old.volume_m3,color='#128b91',lw=.7);axes[2].set_ylabel('Outlet daily volume change (m³)')
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('Matched 10 cm comparison | peak response and water accounting')
    fig.savefig(OUT/'figure-2-matched-10cm.png',dpi=180);plt.close(fig)
    # Highest absolute paired outlet peak departures, not selected by direction.
    selected=[]
    for day in (new.peak_m3s-old.peak_m3s).abs().sort_values(ascending=False).index:
        if all(abs((day-s).days)>7 for s in selected):selected.append(day)
        if len(selected)==3:break
    curves={}
    curve_checks={}
    for build,root in [('original',ROOT),('corrected',FIXED)]:
        h=pd.read_csv(root/'rr10/output/chan.out',sep=r'\s+',skiprows=6,header=None,names=['year','julian','element','channel','seconds','q'])
        h['day']=pd.to_datetime(h.year.astype(str),format='%Y')+pd.to_timedelta(h.julian-1,unit='D')
        h['date']=h.day+pd.to_timedelta(h.seconds,unit='s')
        curves[build]=h
        assert len(h)==8766*144 and np.isfinite(h.q).all() and (h.q>=0).all()
        q=h.q.to_numpy()
        bound=float(np.where(q>0,.5*10**(np.floor(np.log10(np.maximum(q,1e-99)))-2),0).sum()*600)
        integral=float(q.sum()*600); ledger=float(outlet[build]['rr10'].volume_m3.sum())
        curve_checks[build]={'printed_integral_m3':integral,'ledger_volume_m3':ledger,
            'integral_minus_ledger_m3':integral-ledger,'printing_rounding_bound_m3':bound,
            'discrepancy_exceeds_printing_bound':abs(integral-ledger)>bound}
    save('hydrograph-volume-check.json',curve_checks)
    event_volumes=[]
    for day in selected:
        record={'selected_peak_day':str(day.date()),'cases':{}}
        start=day-pd.Timedelta(days=2);end=day+pd.Timedelta(days=3)
        for build in curves:
            h=curves[build]
            sub=h[(h.day>=start)&(h.day<end)]
            d=outlet[build]['rr10']; ds=d[(d.index>=start)&(d.index<end)]
            assert len(sub)==5*144 and len(ds)==5
            integral=float(sub.q.sum()*600);ledger=float(ds.volume_m3.sum())
            record['cases'][build]={'printed_integral_m3':integral,'ledger_volume_m3':ledger,
                'integral_minus_ledger_percent':100*(integral/ledger-1)}
        event_volumes.append(record)
    save('selected-event-volume-check.json',event_volumes)
    fig,axes=plt.subplots(3,2,figsize=(15,10),layout='constrained')
    for row,day in enumerate(selected):
        series=[]
        for build,color,style in [('original','#273b54','-'),('corrected','#d76328','--')]:
            h=curves[build]; sub=h[(h.date>=day-pd.Timedelta(days=2))&(h.date<day+pd.Timedelta(days=3))]
            series.append(sub.reset_index(drop=True))
            axes[row,0].plot(sub.date,sub.q,label=build.capitalize(),color=color,ls=style)
        assert series[0].date.equals(series[1].date)
        axes[row,1].plot(series[0].date,series[1].q-series[0].q,color='#d76328')
        axes[row,0].set(title=str(day.date()),ylabel='Printed routed discharge (m³/s)')
        axes[row,1].set(ylabel='Corrected − original (m³/s)')
        axes[row,0].legend()
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle('10 cm hydrographs | three largest absolute outlet peak changes\n600-second samples, three significant digits; not a precision volume ledger')
    fig.savefig(OUT/'figure-3-matched-hydrographs.png',dpi=180);plt.close(fig)
    save('hydrograph-selection.json',[str(d.date()) for d in selected])
    print('COMPARISON COMPLETE',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-case',choices=CASES)
    parser.add_argument('--no-convert',action='store_true')
    args=parser.parse_args()
    if args.prepare_case:
        build_interchange([args.prepare_case])
    else:
        main(convert=not args.no_convert)
