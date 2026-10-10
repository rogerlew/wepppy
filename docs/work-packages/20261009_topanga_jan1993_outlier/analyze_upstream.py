#!/usr/bin/env python3
"""Retain the selected lower-network series and compare existing observations."""
import io
import json
from pathlib import Path
import shutil
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from output_replay import ROOT, SUFFIX, lane, save, sha

HERE=Path(__file__).resolve().parent
OUT=HERE/'artifacts/upstream-trace'


def read_selected(path, pattern, names):
    text=subprocess.check_output(['rg',pattern,str(path)],text=True)
    frame=pd.read_csv(io.StringIO(text),sep=r'\s+',header=None,names=names)
    return frame


def main():
    audits=json.loads((ROOT/'upstream-audit.json').read_text())
    assert len(audits)==2 and all(not x['differences'] for x in audits)
    OUT.mkdir(parents=True,exist_ok=False)
    selection=json.loads((ROOT/'upstream-selection.json').read_text())
    streams=[];daily=[];ledgers=[];sources={}
    for scenario in SUFFIX:
        output=lane('upstream',scenario)/'output'
        data=read_selected(output/'chan.out',r'^\s+1993\s+(?:1[0-9]|2[0-4])\s+',
            ['year','julian','wepp_id','channel_ordinal','seconds','discharge_m3s'])
        assert len(data)==9*15*144
        data.insert(0,'scenario',scenario);streams.append(data)
        ebe=read_selected(output/'ebe_pw0.txt',r'^\s+(?:1[0-9]|2[0-4])\s+1\s+14\s+',
            ['day','month','simulation_year','precip_mm','volume_m3','peak_m3s','sediment_kg','soluble_p','particulate_p','total_p','wepp_id'])
        assert len(ebe)==9*15
        ebe.insert(0,'scenario',scenario);daily.append(ebe)
        ledger=read_selected(output/'chanwb.out',r'^\s+1993\s+(?:1[0-9]|2[0-4])\s+',
            ['year','julian','wepp_id','channel_ordinal','inflow_m3','outflow_m3','storage_m3','baseflow_m3','loss_m3','balance_m3'])
        assert len(ledger)==9*15
        ledger.insert(0,'scenario',scenario);ledgers.append(ledger)
        for name in ('chan.out','chanwb.out','ebe_pw0.txt'):
            sources[f'{scenario}/{name}']=sha(output/name)
    streams=pd.concat(streams);daily=pd.concat(daily);ledgers=pd.concat(ledgers)
    streams.to_csv(OUT/'channel-series-january10-24.csv',index=False)
    daily.to_csv(OUT/'channel-events-january10-24.csv',index=False)
    ledgers.to_csv(OUT/'channel-ledgers-january10-24.csv',index=False)
    peaks=daily.loc[daily.day.eq(18)].merge(pd.DataFrame(selection['mapping']),on='wepp_id',validate='many_to_one')
    peaks.to_csv(OUT/'january18-peaks.csv',index=False)
    print(peaks[['scenario','wepp_id','topaz_id','peak_m3s','volume_m3','length']].to_string(index=False))
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True,layout='constrained')
    for ax,wepp_id in zip(axes.flat,[406,409,411,412]):
        for scenario,color in [('burned','#b54930'),('undisturbed','#16748c')]:
            f=streams.loc[streams.scenario.eq(scenario)&streams.wepp_id.eq(wepp_id)&streams.julian.eq(18)]
            ax.plot(f.seconds/3600,f.discharge_m3s,'o-',markersize=2.5,lw=1,color=color,label=scenario)
        mapped=next(r for r in selection['mapping'] if r['wepp_id']==wepp_id)
        ax.set_title(f'WEPP {wepp_id} / Topaz {mapped["topaz_id"]}')
        ax.set_xlim(0,3);ax.grid(alpha=.2);ax.legend()
        ax.set_xlabel('Hours in model daily routing frame');ax.set_ylabel('Discharge (m3/s)')
    fig.suptitle('January 18, 1993: lower-trunk progression, unchanged 600 s routing')
    fig.savefig(OUT/'lower-trunk.png',dpi=170);plt.close(fig)
    for name in ['upstream-selection.json','upstream-audit.json','upstream_runner.py']:
        shutil.copy2(ROOT/name,OUT/name)
    save(OUT/'source-hashes.json',sources)
    save(OUT/'manifest.json',{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})


if __name__=='__main__':
    main()
