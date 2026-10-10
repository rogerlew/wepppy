#!/usr/bin/env python3
"""Separate Cedar hillslope yield, channel ledger and sampled hydrograph volume."""
import importlib.util
import argparse
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from run_cedar_candidate import ROOT, HERE, HELPERS, runner

spec = importlib.util.spec_from_file_location('cedar_deep', HELPERS/'deep_candidate_comparison.py')
deep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deep)
OUT = HERE/'artifacts/cedar'
DATES = deep.DATES
LABELS = {'baseline': 'wepp_260803', 'release': 'wepp_261009', 'candidate': 'CHRQIN candidate'}


def delta(a, b):
    return dict(reference=float(a), candidate=float(b), delta=float(b-a),
                percent=float(100*(b/a-1)) if a else None)


def main():
    assert (ROOT/'hillslope-parity.json').exists(), 'Wait for both complete runs and conversions'
    OUT.mkdir(parents=True, exist_ok=False)
    historical = deep.BASE.parent.parent
    for name in ('historical-parity.json', 'observer-parity.json'):
        record = json.loads((historical/name).read_text())
        assert record['exact'] and not record['different']
        shutil.copy2(historical/name, OUT/f'baseline-{name}')
    runner.save(OUT/'analysis-provenance.json', dict(
        runner_sha256=runner.sha(Path(__file__)),
        helpers={name: runner.sha(HELPERS/name) for name in
                 ('deep_candidate_comparison.py', 'audit_bounded_watershed.py', 'audit_reproduction.py')},
        integration='Sum of the 144 printed positive-time discharge samples times 600 seconds; unchanged reference convention'))
    folders = {'baseline': deep.BASE, 'release': ROOT/'release/off/output',
               'candidate': ROOT/'candidate/off/output'}
    yields = {'baseline': deep.BASE_TABLES/'totalwatsed3.parquet',
              **{lane: ROOT/lane/'yield-optimized/totalwatsed3.parquet' for lane in ('release', 'candidate')}}
    tables, flows, totals, provenance = {}, {}, {}, {}
    for lane in folders:
        folder = folders[lane]
        eb = deep.parse_ebe(folder/'ebe_pw0.txt')
        data = np.loadtxt(folder/'chan.out', skiprows=6)
        assert data.shape == (8766*144, 6) and np.isfinite(data).all()
        assert (data[:, 2:4] == [1235, 371]).all()
        assert (data[:, 4].reshape(-1, 144) == np.arange(600, 86401, 600)).all()
        dates = [pd.Timestamp(int(y), 1, 1)+pd.Timedelta(days=int(d)-1)
                 for y, d in data[::144, :2]]
        assert dates == list(DATES)
        q = data[:, 5].reshape(-1, 144)
        assert (q >= 0).all()
        tw = pd.read_parquet(yields[lane])
        stamps = pd.to_datetime(dict(year=tw.year, month=tw.month, day=tw.day_of_month))
        assert list(stamps) == list(DATES)
        eb['hill_stream_m3'] = (tw.Streamflow*tw.Area/1000).to_numpy()
        for name, field in [('hill_surface_m3', 'Runoff'), ('hill_lateral_m3', 'Lateral Flow'),
                            ('hill_baseflow_m3', 'Baseflow')]:
            eb[name] = (tw[field]*tw.Area/1000).to_numpy()
        eb['sampled_volume_m3'] = q.sum(axis=1)*600
        eb['sampled_peak_m3s'] = q.max(axis=1)
        eb['first_peak_second'] = (q.argmax(axis=1)+1)*600
        eb['integral_minus_ledger_m3'] = eb.sampled_volume_m3-eb.water_m3
        eb['ledger_minus_hill_m3'] = eb.water_m3-eb.hill_stream_m3
        eb['sampled_minus_hill_m3'] = eb.sampled_volume_m3-eb.hill_stream_m3
        assert np.isfinite(eb.to_numpy()).all()
        eb.to_csv(OUT/f'{lane}-daily.csv', index_label='date')
        tables[lane], flows[lane] = eb, q
        totals[lane] = {name: float(eb[name].sum()) for name in
                       ['hill_stream_m3', 'hill_surface_m3', 'hill_lateral_m3', 'hill_baseflow_m3',
                        'water_m3', 'sampled_volume_m3', 'integral_minus_ledger_m3',
                        'ledger_minus_hill_m3', 'sampled_minus_hill_m3']}
        totals[lane].update(abs_daily_integral_ledger_gap_m3=float(eb.integral_minus_ledger_m3.abs().sum()),
                            maximum_sampled_peak_m3s=float(q.max()),
                            maximum_reported_peak_m3s=float(eb.peak_m3s.max()))
        provenance[lane] = {str(p): runner.sha(p) for p in [folder/'chan.out', folder/'ebe_pw0.txt', yields[lane]]}
        shutil.copy2(yields[lane], OUT/f'{lane}-totalwatsed3.parquet')
    assert np.array_equal(tables['baseline'].precipitation_mm, tables['candidate'].precipitation_mm)
    assert np.array_equal(tables['release'].precipitation_mm, tables['candidate'].precipitation_mm)
    annual = []
    for lane, table in tables.items():
        for year, g in table.groupby(table.index.year):
            annual.append(dict(lane=lane, year=year, **{k: float(g[k].sum()) for k in
                ['hill_stream_m3', 'water_m3', 'sampled_volume_m3', 'integral_minus_ledger_m3']},
                abs_daily_gap_m3=float(g.integral_minus_ledger_m3.abs().sum()),
                peak_m3s=float(g.sampled_peak_m3s.max())))
    pd.DataFrame(annual).to_csv(OUT/'annual.csv', index=False)
    peaks, _ = find_peaks(tables['baseline'].sampled_volume_m3.to_numpy()/86400,
                         distance=7, prominence=.1)
    fixed = [('1994-10-25', '1994-10-30'), ('1992-11-19', '1992-11-23'),
             ('1996-02-04', '1996-02-08'), ('1990-10-18', '1990-10-24'),
             ('1991-10-22', '1991-10-28'), ('1998-09-15', '1998-09-21')]
    windows = [('screen', max(0, i-3), min(len(DATES), i+4)) for i in peaks]
    windows += [('retained', DATES.get_loc(a), DATES.get_loc(b)+1) for a, b in fixed]
    events, departures, impacts = [], [], {}
    dry = set(json.loads((ROOT/'candidate/yield-optimized/summary.json').read_text())['dry_dates'])
    dry_ids = np.array([str(d.date()) in dry for d in DATES])
    for ref in ('baseline', 'release'):
        a, b = tables[ref], tables['candidate']
        impact = dict(totals={name: delta(totals[ref][name], value) for name, value in totals['candidate'].items()},
                      daily_fit={field: deep.audit.fit(a[field].to_numpy(), b[field].to_numpy())
                                 for field in ['hill_stream_m3', 'water_m3', 'sampled_volume_m3', 'sampled_peak_m3s']},
                      subdaily_fit=deep.audit.fit(flows[ref].ravel(), flows['candidate'].ravel()),
                      changed_sample_days=int(np.any(flows[ref] != flows['candidate'], axis=1).sum()),
                      increased_peak_days=int((b.sampled_peak_m3s > a.sampled_peak_m3s).sum()),
                      decreased_peak_days=int((b.sampled_peak_m3s < a.sampled_peak_m3s).sum()),
                      new_positive_samples=int(((flows[ref] == 0) & (flows['candidate'] > 0)).sum()),
                      dry_days=int(dry_ids.sum()),
                      dry_sampled_volume_delta_m3=float((b.sampled_volume_m3-a.sampled_volume_m3).to_numpy()[dry_ids].sum()),
                      max_daily_hill_yield_delta_m3=float((b.hill_stream_m3-a.hill_stream_m3).abs().max()))
        changes = pd.DataFrame(index=DATES)
        for field in ['hill_stream_m3', 'water_m3', 'sampled_volume_m3', 'sampled_peak_m3s',
                      'integral_minus_ledger_m3']:
            changes[field+'_delta'] = b[field]-a[field]
        changes['peak_time_shift_minutes'] = (b.first_peak_second-a.first_peak_second)/60
        changes.to_csv(OUT/f'changes-vs-{ref}.csv', index_label='date')
        for field in ['sampled_volume_m3', 'sampled_peak_m3s', 'integral_minus_ledger_m3']:
            for date in changes[field+'_delta'].abs().nlargest(15).index:
                departures.append(dict(reference=ref, ranked_by=field, date=str(date.date()),
                    reference_value=float(a.loc[date, field]), candidate_value=float(b.loc[date, field]),
                    change=float(changes.loc[date, field+'_delta'])))
        for kind, i, j in windows:
            event = deep.audit.pair_event(flows[ref], flows['candidate'], i, j,
                                          [str(d.date()) for d in DATES])
            row = dict(reference=ref, kind=kind, first=event['first'], last=event['last'],
                       volume_change_m3=event['volume_change_m3'], volume_change_percent=event['volume_change_percent'],
                       reference_peak_m3s=event['baseline']['peak_m3s'], candidate_peak_m3s=event['candidate']['peak_m3s'],
                       peak_time_shift_minutes=event['first_peak_hour_shift']*60,
                       centroid_shift_minutes=event['centroid_hour_shift']*60,
                       reference_gap_m3=float(a.integral_minus_ledger_m3.iloc[i:j].sum()),
                       candidate_gap_m3=float(b.integral_minus_ledger_m3.iloc[i:j].sum()))
            events.append(row)
        impacts[ref] = impact
    pd.DataFrame(events).to_csv(OUT/'events.csv', index=False)
    pd.DataFrame(departures).to_csv(OUT/'largest-daily-departures.csv', index=False)
    for name in ('hillslope-parity.json', 'source-manifest.json', 'helpers.json'):
        shutil.copy2(ROOT/name, OUT/name)
    for lane in ('candidate', 'release'):
        for name, path in [('hills', ROOT/lane/'off/hillslopes.json'), ('watershed', ROOT/lane/'off/watershed.json'),
                           ('conversion', ROOT/lane/'yield-optimized/summary.json'), ('build', ROOT/lane/'build.json'),
                           ('pass-provenance', ROOT/lane/'off/pass-provenance.json')]:
            shutil.copy2(path, OUT/f'{lane}-{name}.json')
    summary = dict(project='warming-championship; Cedar Creek', years=[1980, 2003], days=len(DATES),
                   hills=864, channels=371, timestep_s=600, rrinit_cm=10,
                   totals=totals, candidate_versus=impacts,
                   event_screen=dict(count=len(peaks), selection='260803 daily mean peaks; distance 7 days, prominence 0.1 m3/s; +/-3 days; no baseflow subtraction'),
                   provenance=provenance)
    runner.save(OUT/'summary.json', summary)
    colors = {'baseline': '#777777', 'release': '#b3432c', 'candidate': '#087a91'}
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), layout='constrained')
    for lane, table in tables.items():
        axes[0].plot(DATES, table.hill_stream_m3/86400, label=LABELS[lane], color=colors[lane], lw=.7)
        axes[1].plot(DATES, table.sampled_volume_m3/86400, label=LABELS[lane], color=colors[lane], lw=.7)
        annual_lane = pd.DataFrame(annual).query('lane == @lane')
        axes[2].plot(annual_lane.year, annual_lane.integral_minus_ledger_m3/1e6,
                     label=LABELS[lane], color=colors[lane])
    for ax, title, unit in zip(axes, ['Hillslope streamflow: totalwatsed', 'Outlet discharge: sampled daily mean',
                                    'Annual sampled integral minus channel ledger'], ['m3/s', 'm3/s', 'million m3']):
        ax.set(title=title, ylabel=unit); ax.legend(); ax.grid(alpha=.2)
    fig.suptitle('Cedar Creek: full 1980-2003 record, unchanged 10 cm RRINIT')
    fig.savefig(OUT/'full-record.png', dpi=150); plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(13, 10), layout='constrained')
    for ax, (first, last) in zip(axes.flat, fixed):
        i, j = DATES.get_loc(first), DATES.get_loc(last)+1
        times = (np.arange((j-i)*144)+1)/144
        for lane, q in flows.items():
            ax.plot(times, q[i:j].ravel(), label=LABELS[lane], color=colors[lane], lw=1)
        ax.set(title=f'{first} to {last}', xlabel='Days from window start', ylabel='Outlet m3/s')
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.savefig(OUT/'event-windows.png', dpi=150); plt.close(fig)
    runner.save(OUT/'manifest.json', {p.name: runner.sha(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps(dict(totals=totals, candidate_versus=impacts), indent=2), flush=True)


def timing_audit():
    folders = {'baseline': deep.BASE, 'release': ROOT/'release/off/output',
               'candidate': ROOT/'candidate/off/output'}
    flows = {lane: np.loadtxt(folder/'chan.out', skiprows=6, usecols=5).reshape(8766, 144)
             for lane, folder in folders.items()}
    events = pd.read_csv(OUT/'events.csv')
    screen = events.loc[events.kind.eq('screen')].copy()
    screen['absolute_shift'] = screen.peak_time_shift_minutes.abs()
    selections = screen.sort_values('absolute_shift', ascending=False).groupby('reference').head(3)
    selections = pd.concat([selections, events.loc[events.kind.eq('retained') & events['first'].eq('1996-02-04')]])
    rows = []
    for row in selections.to_dict('records'):
        i, j = DATES.get_loc(row['first']), DATES.get_loc(row['last'])+1
        values = {}
        for lane in (row['reference'], 'candidate'):
            q = flows[lane][i:j].ravel()
            maxima = np.flatnonzero(q == q.max())
            values[lane] = dict(**deep.audit.moments(q),
                first_maximum=str(DATES[i]+pd.Timedelta(seconds=int(maxima[0]+1)*600)),
                last_equal_maximum=str(DATES[i]+pd.Timedelta(seconds=int(maxima[-1]+1)*600)))
        rows.append(dict(reference=row['reference'], first=row['first'], last=row['last'],
                         peak_time_shift_minutes=row['peak_time_shift_minutes'],
                         centroid_shift_minutes=row['centroid_shift_minutes'], values=values))
    difference = flows['candidate']-flows['release']
    runner.save(OUT/'timing-audit.json', dict(windows=rows,
        candidate_vs_release=dict(increased_samples=int((difference > 0).sum()),
                                  decreased_samples=int((difference < 0).sum()),
                                  maximum_added_flow_m3s=float(difference.max()),
                                  maximum_reduction_m3s=float(difference.min()))))
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), layout='constrained')
    for ax, (first, last) in zip(axes, [('1984-11-25', '1984-12-01'),
                                      ('1996-02-04', '1996-02-10'), ('1994-02-21', '1994-02-27')]):
        i, j = DATES.get_loc(first), DATES.get_loc(last)+1
        for lane, color in [('baseline', '#777777'), ('release', '#b3432c'), ('candidate', '#087a91')]:
            q = flows[lane][i:j].ravel()
            t = (np.arange(len(q))+1)/144
            ax.plot(t, q, label=LABELS[lane], color=color, lw=1)
            ax.plot(t[q.argmax()], q.max(), marker='o', fillstyle='none', color=color, ms=8)
        ax.set(title=f'{first} to {last}', xlabel='Days from window start', ylabel='Outlet m3/s')
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle('Cedar timing audit: markers identify the first printed maximum')
    fig.savefig(OUT/'timing-windows.png', dpi=150); plt.close(fig)
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timing-audit', action='store_true')
    args = parser.parse_args()
    timing_audit() if args.timing_audit else main()
