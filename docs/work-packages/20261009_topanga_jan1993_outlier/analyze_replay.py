#!/usr/bin/env python3
"""Summarize the observed outlet series; do not adjudicate an outlier's cause."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from output_replay import ROOT, SUFFIX, lane, sha, save

HERE = Path(__file__).resolve().parent
OUT = HERE/'artifacts/output-replay'


def read_channel(path):
    with path.open() as stream:
        for line_number,line in enumerate(stream,1):
            if 'Year' in line and 'Time(s)' in line:
                skip = line_number
                break
        else:
            raise ValueError(f'No channel table header: {path}')
    frame = pd.read_csv(path,sep=r'\s+',skiprows=skip,header=None,
                        names=['raw_year','julian','topaz_id','channel_id','seconds','discharge_m3s'])
    frame['year'] = np.where(frame.raw_year.lt(1000),frame.raw_year+1979,frame.raw_year)
    assert set(frame.year)==set(range(1980,2025))
    assert set(frame.topaz_id)=={412} and set(frame.channel_id)=={128}
    assert np.isfinite(frame.discharge_m3s).all()
    return frame


def main():
    receipts = json.loads((ROOT/'watershed-receipts.json').read_text())
    assert len(receipts)==2 and all(not r['observer_differences'] for r in receipts)
    OUT.mkdir(parents=True,exist_ok=False)
    series=[];diagnostics=[]
    for scenario in SUFFIX:
        full=read_channel(lane('series',scenario)/'output/chan.out')
        control=read_channel(lane('control',scenario)/'output/chan.out')
        maximum=full.groupby(['year','julian']).discharge_m3s.max()
        expected=control.set_index(['year','julian']).discharge_m3s
        assert maximum.index.equals(expected.sort_index().index)
        assert np.array_equal(maximum.values,expected.sort_index().values)
        window=full.loc[full.year.eq(1993)&full.julian.between(10,24)].copy()
        window.insert(0,'scenario',scenario)
        series.append(window)
        day=window.loc[window.julian.eq(18)]
        q=day.discharge_m3s.to_numpy();t=day.seconds.to_numpy()
        print('\n',scenario,day.loc[day.seconds.le(7200),['seconds','discharge_m3s']].to_string(index=False))
        diagnostics.append(dict(scenario=scenario,full_series_rows=len(full),
            days_compared=len(maximum),printed_daily_maxima_match_control=True,
            january18_samples=len(day),maximum_printed_m3s=float(q.max()),
            peak_sample_seconds=day.loc[day.discharge_m3s.eq(q.max()),'seconds'].tolist(),
            preceding_sample_m3s=float(q[q.argmax()-1]) if q.argmax()>0 else None,
            following_sample_m3s=float(q[q.argmax()+1]) if q.argmax()+1<len(q) else None,
            minimum_printed_m3s=float(q.min()),negative_samples=int((q<0).sum()),
            discharge_first_12_samples=q[:12].tolist(),
            note='Printed series uses three significant digits; time is the model daily routing frame. No causal classification.'))
    frame=pd.concat(series,ignore_index=True)
    frame.to_csv(OUT/'outlet-january10-24.csv',index=False)
    save(OUT/'summary.json',diagnostics)
    fig,axes=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for scenario,color in [('burned','#b54930'),('undisturbed','#16748c')]:
        f=frame.loc[frame.scenario.eq(scenario)&frame.julian.eq(18)]
        axes[0].plot(f.seconds/3600,f.discharge_m3s,'o-',markersize=3,lw=1.2,color=color,label=scenario)
        f=frame.loc[frame.scenario.eq(scenario)&frame.julian.between(16,20)]
        axes[1].plot((f.julian-16)*24+f.seconds/3600,f.discharge_m3s,lw=1,color=color,label=scenario)
    axes[0].set_xlim(0,3);axes[0].set_title('January 18, 1993: first three routing hours')
    axes[0].set_xlabel('Hours in model daily routing frame (not observed storm clock)')
    axes[1].set_title('January 16-20: consecutive model daily routing frames')
    axes[1].set_xlabel('Hours from start of January 16 routing frame')
    for ax in axes:
        ax.set_ylabel('Outlet discharge (m3/s)');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Topanga GridMET, WEPP 261009: output-only capture, 600 s routing',fontsize=12)
    fig.savefig(OUT/'outlet-capture.png',dpi=170)
    plt.close(fig)
    for name in ['hills-receipts.json','staged-inputs.json','watershed-receipts.json','burned-control.json','undisturbed-control.json']:
        (OUT/name).write_bytes((ROOT/name).read_bytes())
    save(OUT/'manifest.json',{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':
    main()
