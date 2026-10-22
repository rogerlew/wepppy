#!/usr/bin/env python3
"""Compare full-record Cedar outlet artifacts, retaining distinct volume definitions."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

HERE = Path(__file__).resolve().parent
ROOT = Path('/workdir/cedar-physical-water-comparison-20261021')
OUT = HERE/'artifacts/cedar-comparison'
DATES = pd.date_range('1980-01-01', '2003-12-31')
LABELS = {'release': 'wepp_261010', 'candidate': 'Repair d354e3c99'}


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def numeric(path, width):
    rows = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if fields and fields[0].isdigit():
            assert len(fields) == width, (path, fields)
            rows.append(list(map(float, fields)))
    result = np.array(rows)
    assert np.isfinite(result).all(), path
    return result


def main():
    assert (ROOT/'hillslope-parity.json').exists(), 'Both complete runs required'
    OUT.mkdir(exist_ok=False)
    tables, flows, summary, annual = {}, {}, {}, []
    hashes = {}
    for lane in LABELS:
        folder = ROOT/lane/'off/output'
        data = np.loadtxt(folder/'chan.out', skiprows=6)
        assert data.shape == (len(DATES)*144, 6)
        assert np.isfinite(data).all() and (data[:, 5] >= 0).all()
        assert (data[:, 2:4] == [1235, 371]).all()
        assert np.array_equal(data[:, 4].reshape(-1,144), np.tile(np.arange(600,86401,600),(len(DATES),1)))
        expected = np.c_[DATES.year, DATES.dayofyear]
        assert np.array_equal(data[:,:2], np.repeat(expected,144,axis=0))
        q = data[:,5].reshape(-1,144)
        # chan.out prints three significant figures (E format). Half a printed
        # unit bounds each sample's rounding; sum absolute bounds conservatively.
        rounding = .005*np.power(10.,np.floor(np.log10(np.maximum(q,1e-300))))
        rounding[q == 0] = 0.0
        wb = numeric(folder/'chanwb.out',10)
        assert wb.shape == (len(DATES),10) and np.array_equal(wb[:,:2],expected)
        assert (wb[:,2:4] == [1235,371]).all()
        ebe = numeric(folder/'ebe_pw0.txt',11)
        assert ebe.shape == (len(DATES),11)
        assert np.array_equal(ebe[:,:3],np.c_[DATES.day,DATES.month,DATES.year-1979])
        assert (ebe[:,-1] == 1235).all()
        assert np.max(np.abs(wb[:,5]-ebe[:,4])) < .02
        table = pd.DataFrame(index=DATES, data={
            'sampled_volume_m3':q.sum(axis=1)*600,
            'published_volume_m3':wb[:,5], 'sampled_peak_m3s':q.max(axis=1),
            'reported_peak_m3s':ebe[:,5], 'precipitation_mm':ebe[:,3],
            'first_peak_second':(q.argmax(axis=1)+1)*600,
            'inflow_m3':wb[:,4], 'loss_m3':wb[:,8], 'reported_balance_m3':wb[:,9]})
        # q(0) is absent from chan.out. Following days use the preceding endpoint;
        # day one is left unknown rather than silently assuming its initial rate.
        q0 = np.r_[np.nan,q[:-1,-1]]
        table['reconstructed_trapezoid_m3'] = table.sampled_volume_m3+300*(q0-q[:,-1])
        table['printed_volume_rounding_bound_m3'] = rounding.sum(axis=1)*600
        table['sampled_minus_published_m3'] = table.sampled_volume_m3-table.published_volume_m3
        yield_file = ROOT/lane/'yield-optimized/totalwatsed3.parquet'
        tw = pd.read_parquet(yield_file)
        assert list(pd.to_datetime(dict(year=tw.year,month=tw.month,day=tw.day_of_month))) == list(DATES)
        for field, name in [('Streamflow','hill_stream'),('Runoff','hill_surface'),('Lateral Flow','hill_lateral'),('Baseflow','hill_baseflow')]:
            table[name+'_m3'] = (tw[field]*tw.Area/1000).to_numpy()
        assert np.isfinite(table.drop(columns=['reconstructed_trapezoid_m3']).to_numpy()).all()
        table.to_csv(OUT/f'{lane}-daily.csv',index_label='date')
        tables[lane],flows[lane] = table,q
        summary[lane] = {key:float(table[key].sum()) for key in ['sampled_volume_m3','published_volume_m3','hill_stream_m3','hill_surface_m3','hill_lateral_m3','hill_baseflow_m3','sampled_minus_published_m3']}
        peakidx = np.unravel_index(q.argmax(),q.shape)
        summary[lane]['printed_volume_rounding_bound_m3'] = float(rounding.sum()*600)
        trap_gap=(table.reconstructed_trapezoid_m3-table.published_volume_m3).to_numpy()[1:]
        trap_bound=(rounding.sum(axis=1)*600)[1:]+300*(rounding[:-1,-1]+rounding[1:,-1])+.005
        summary[lane]['trapezoid_publication_check_days2on'] = {
            'signed_gap_m3':float(trap_gap.sum()),
            'absolute_daily_gaps_m3':float(np.abs(trap_gap).sum()),
            'days_outside_conservative_printing_bound':int((np.abs(trap_gap)>trap_bound).sum()),
            'maximum_daily_gap_m3':float(np.abs(trap_gap).max()),
            'note':'Only discharge-publication consistency; not a physical water budget.'}
        summary[lane]['q0_peak_diagnostic'] = {
            'maximum_reported_minus_positive_time_peak_m3s':float((ebe[:,5]-q.max(axis=1)).max()),
            'days_q0_exceeds_positive_time_max':int((q0[1:]>q[1:].max(axis=1)).sum()),
            'max_reported_minus_reconstructed_peak_abs_m3s_days2on':float(np.abs(ebe[1:,5]-np.maximum(q0[1:],q[1:].max(axis=1))).max()),
            'note':'Printed positive-time max can omit q0; both printed quantities have rounding. First q0 unknown.'}
        summary[lane]['discharge_exceedance_m3s'] = {str(percent):float(np.percentile(q,100-percent)) for percent in (1,5,10,50,90,95,99)}
        summary[lane].update(mean_sampled_discharge_m3s=float(q.mean()),maximum_sampled_peak_m3s=float(q.max()),maximum_reported_peak_m3s=float(ebe[:,5].max()),maximum_sampled_peak_time=str(DATES[peakidx[0]]+pd.Timedelta(seconds=(peakidx[1]+1)*600)),sum_absolute_daily_sampled_published_gap_m3=float(table.sampled_minus_published_m3.abs().sum()))
        for year,g in table.groupby(table.index.year):
            annual.append(dict(lane=lane,year=int(year),sampled_volume_m3=float(g.sampled_volume_m3.sum()),published_volume_m3=float(g.published_volume_m3.sum()),sampled_peak_m3s=float(g.sampled_peak_m3s.max()),reported_peak_m3s=float(g.reported_peak_m3s.max()),peak_day=str(g.sampled_peak_m3s.idxmax().date())))
        for name in ['chan.out','chanwb.out','ebe_pw0.txt']:
            hashes[str(folder/name)] = sha(folder/name)
        hashes[str(yield_file)] = sha(yield_file)
    a,b = tables['release'],tables['candidate']
    assert np.array_equal(a.precipitation_mm,b.precipitation_mm)
    annual = pd.DataFrame(annual); annual.to_csv(OUT/'annual.csv',index=False)
    delta = pd.DataFrame(index=DATES)
    for field in ['sampled_volume_m3','published_volume_m3','sampled_peak_m3s','reported_peak_m3s','hill_stream_m3']:
        delta[field] = b[field]-a[field]
    delta.to_csv(OUT/'daily-differences.csv',index_label='date')
    summary['changes'] = {k:{'absolute':summary['candidate'][k]-v,'percent':100*(summary['candidate'][k]/v-1) if v else None} for k,v in summary['release'].items() if isinstance(v,float)}
    summary['changes'].update(increased_daily_peaks=int((b.sampled_peak_m3s>a.sampled_peak_m3s).sum()),decreased_daily_peaks=int((b.sampled_peak_m3s<a.sampled_peak_m3s).sum()),max_daily_hillslope_yield_change_m3=float(delta.hill_stream_m3.abs().max()))
    # Symmetric 7-day screens; these are not independent storms or fitted floods.
    peaks,_=find_peaks(a.sampled_peak_m3s.to_numpy(),distance=7,prominence=.1)
    candidate_peaks,_=find_peaks(b.sampled_peak_m3s.to_numpy(),distance=7,prominence=.1)
    top_changes=np.argsort(np.abs(b.sampled_peak_m3s.to_numpy()-a.sampled_peak_m3s.to_numpy()))[-10:]
    selected=sorted(set(peaks)|set(candidate_peaks)|set(top_changes))
    events=[]
    for i in selected:
        lo,hi=max(0,i-3),min(len(DATES),i+4)
        event={'start':str(DATES[lo].date()),'end':str(DATES[hi-1].date()),'reference_selected':bool(i in peaks),'candidate_selected':bool(i in candidate_peaks),'top_peak_change_selected':bool(i in top_changes)}
        for lane,q in flows.items():
            window=q[lo:hi].ravel();maxids=np.flatnonzero(window==window.max());seconds=(np.arange(len(window))+1)*600
            event.update({lane+'_volume_m3':float(window.sum()*600),lane+'_peak_m3s':float(window.max()),lane+'_first_peak':str(DATES[lo]+pd.Timedelta(seconds=int(seconds[maxids[0]]))),lane+'_tied_peak_samples':len(maxids),lane+'_centroid_seconds':float(np.dot(window,seconds)/window.sum())})
        event['peak_change_percent']=100*(event['candidate_peak_m3s']/event['release_peak_m3s']-1)
        event['volume_change_percent']=100*(event['candidate_volume_m3']/event['release_volume_m3']-1)
        event['centroid_shift_minutes']=(event['candidate_centroid_seconds']-event['release_centroid_seconds'])/60
        events.append(event)
    events=pd.DataFrame(events).sort_values('release_peak_m3s',ascending=False);events.to_csv(OUT/'events.csv',index=False)
    summary['largest_reference_events']=events[events.reference_selected].head(10).to_dict('records')
    summary['largest_candidate_events']=events[events.candidate_selected].sort_values('candidate_peak_m3s',ascending=False).head(10).to_dict('records')
    yr_a=annual[annual.lane=='release'].set_index('year')
    yr_b=annual[annual.lane=='candidate'].set_index('year')
    yr_change=100*(yr_b[['sampled_volume_m3','sampled_peak_m3s','reported_peak_m3s']]/yr_a[['sampled_volume_m3','sampled_peak_m3s','reported_peak_m3s']]-1)
    yr_change.to_csv(OUT/'annual-percent-changes.csv')
    summary['annual_change_ranges_percent']={c:{'minimum':float(yr_change[c].min()),'maximum':float(yr_change[c].max()),'minimum_year':int(yr_change[c].idxmin()),'maximum_year':int(yr_change[c].idxmax())} for c in yr_change}
    summary['event_screen_ranges']={c:{'minimum':float(events[c].min()),'maximum':float(events[c].max())} for c in ['volume_change_percent','peak_change_percent','centroid_shift_minutes']}
    summary['event_screen_count']=len(events)
    summary['largest_daily_volume_changes']=[{'date':str(day.date()),'release':float(a.loc[day,'sampled_volume_m3']),'candidate':float(b.loc[day,'sampled_volume_m3']),'delta':float(delta.loc[day,'sampled_volume_m3'])} for day in delta.sampled_volume_m3.abs().nlargest(10).index]
    summary['definitions']={'sampled_volume':'600 times sum of printed positive-time discharge samples; right-endpoint quadrature, matching prior Cedar comparison','reported_volume':'chanwb Outflow, checked against EBE; release balance publication differs from candidate accepted-flux publication','trapezoid':'Daily q0 reconstructed from previous endpoint; first day unknown; printed precision prevents exact solver closure','event_selection':'Union of reference and candidate daily peaks (prominence0.1m3/s, spacing7days) and ten largest daily peak changes; plus/minus3day overlapping descriptive windows, not independent storms','source':'Frozen Cedar 10cm RRINIT, 1980–2003,864 hills,371 channels; MC4 at600seconds','candidate':'Unreleased native d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b','reference':'wepp_261010 (user typed wepp_2601010)'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fig,ax=plt.subplots(3,1,figsize=(12,10),layout='constrained')
    for lane in LABELS:
        yr=annual[annual.lane==lane]
        ax[0].plot(yr.year,yr.sampled_volume_m3/1e6,label=LABELS[lane]);ax[1].plot(yr.year,yr.reported_peak_m3s,label=LABELS[lane])
        x=np.sort(yr.reported_peak_m3s)[::-1];ax[2].plot((len(x)+1)/np.arange(1,len(x)+1),x,'o-',label=LABELS[lane])
    ax[0].set_ylabel('Sampled outlet volume (million m³)');ax[1].set_ylabel('Reported annual maximum (m³/s)');ax[2].set_ylabel('Reported annual maximum (m³/s)');ax[2].set_xlabel('Empirical plotting-position return period (years; no fitted extrapolation)');ax[2].set_xscale('log')
    for x in ax:x.grid(alpha=.25);x.legend()
    fig.savefig(OUT/'annual-discharge-peaks.png',dpi=160);plt.close(fig)
    windows=[(str(x.start),str(x.end)) for x in events[events.reference_selected].head(3).itertuples()]
    windows.append(('1991-10-22','1991-10-28'))
    fig,axes=plt.subplots(4,1,figsize=(12,12),layout='constrained')
    for ax,(start,end) in zip(axes,windows):
        lo=DATES.get_loc(start);hi=DATES.get_loc(end)+1
        ts=pd.date_range(DATES[lo]+pd.Timedelta(minutes=10),periods=(hi-lo)*144,freq='10min')
        for lane in LABELS:ax.plot(ts,flows[lane][lo:hi].ravel(),label=LABELS[lane],alpha=.85)
        ax.set_title(start+' to '+end);ax.set_ylabel('Outlet Q (m³/s)');ax.grid(alpha=.25);ax.legend()
    fig.savefig(OUT/'event-hydrographs.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(12,9),layout='constrained')
    for ax,row in zip(axes,events.nlargest(3,'peak_change_percent').itertuples()):
        lo=DATES.get_loc(row.start);hi=DATES.get_loc(row.end)+1
        ts=pd.date_range(DATES[lo]+pd.Timedelta(minutes=10),periods=(hi-lo)*144,freq='10min')
        for lane in LABELS:ax.plot(ts,flows[lane][lo:hi].ravel(),label=LABELS[lane],alpha=.85)
        ax.set_title(f'{row.start} to {row.end}: sampled peak +{row.peak_change_percent:.2f}%')
        ax.set_ylabel('Outlet Q (m³/s)');ax.grid(alpha=.25);ax.legend()
    fig.savefig(OUT/'small-event-hydrographs.png',dpi=160);plt.close(fig)
    hashes[str(Path(__file__))]=sha(Path(__file__))
    hashes.update({str(f):sha(f) for f in OUT.iterdir() if f.is_file()})
    (OUT/'manifest.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps(summary['changes'],indent=2))


if __name__=='__main__':
    main()
