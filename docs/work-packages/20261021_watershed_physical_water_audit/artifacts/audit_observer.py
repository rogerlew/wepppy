"""Integrate native channel rates independently of published balance identities."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_cases import metrics,passes
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
p=argparse.ArgumentParser();p.add_argument('--group',default='observer-v2');p.add_argument('--source-group',default='release-matrix');p.add_argument('--cases',nargs='+',default=['daily-upper60','hourly-upper60']);args=p.parse_args()
results=[]
for name in args.cases:
    root=ROOT/args.group/'on'/name
    parity=json.loads((root/'parity.json').read_text())
    assert parity['success'] and not parity['differences']
    cols='year day element channel runon local loss volint sinit sfnl lastStor chvol runvol tmpvol length dt base top lateral'.split()
    c=pd.read_csv(root/'runs/water_audit_channel.txt',sep=r'\s+',names=cols).set_index(['year','day','element'])
    h=pd.read_csv(root/'runs/water_audit_hydrograph.txt',sep=r'\s+',names='year day element step dt qin qlat qout'.split())
    idx=['year','day','element'];g=h.groupby(idx)
    for k in ['qin','qlat','qout']:
        h[k+'_rect']=np.where(h.step>0,h[k]*h.dt,0.)
        h[k+'_trap']=np.where(h.step>0,(h[k]+g[k].shift())*.5*h.dt,0.)
    integ=h.groupby(idx)[[k+'_'+m for k in ['qin','qlat','qout'] for m in ['rect','trap']]].sum()
    a=c.join(integ)
    for m in ['rect','trap']:
        a['integrated_in_'+m]=a['qin_'+m]+a['qlat_'+m]*a.length
        a['in_gap_'+m]=a['integrated_in_'+m]-a.volint
        a['out_gap_'+m]=a['qout_'+m]-a.chvol
        a['physical_residual_'+m]=a['integrated_in_'+m]-a['qout_'+m]-(a.sfnl-a.sinit)
    frames=[passes(path)[['surface','lateral','baseflow']] for path in sorted((ROOT/args.source_group/name/'output').glob('H*.pass.dat'))]
    p=pd.concat(frames).groupby(['year','day']).sum()
    dates=a.index.droplevel('element')
    first=int(a.index.get_level_values('element').min())
    a['surface']=p.surface.reindex(dates).to_numpy()
    a['lateral_pass']=p.lateral.reindex(dates).to_numpy()
    a['baseflow']=p.baseflow.reindex(dates).to_numpy()
    a['upstream_channel']=0.
    for element in sorted(a.index.get_level_values('element').unique()):
        if element!=first:
            mask=a.index.get_level_values('element')==element
            a.loc[mask,['surface','lateral_pass','baseflow']]=0.
            prev=a.xs(element-1,level='element').chvol
            a.loc[mask,'upstream_channel']=prev.reindex(a.index[mask].droplevel('element')).to_numpy()
    a['pass_to_runon_gap']=a.runon-a.surface-a.lateral_pass-a.baseflow-a.upstream_channel
    a['volume_bookkeeping_gap']=a.runon+a.local-a.loss-a.chvol-(a.sfnl-a.lastStor)
    out=dict(case=name,days=len(a),totals={k:float(a[k].sum()) for k in ['surface','lateral_pass','baseflow','runon','local','loss','volint','chvol','qin_rect','qin_trap','qout_rect','qout_trap']},metrics={k:metrics(a[k]) for k in ['pass_to_runon_gap','volume_bookkeeping_gap','in_gap_rect','in_gap_trap','out_gap_rect','out_gap_trap','physical_residual_rect','physical_residual_trap']})
    worst=a.out_gap_trap.abs().idxmax();out['worst_trapezoid_outflow_day']={str(k):float(v) for k,v in a.loc[worst].items()};out['worst_date']=list(map(int,worst))
    a.to_csv(root/'channel-ledger.csv')
    (root/'audit.json').write_text(json.dumps(out,indent=2)+'\n');results.append(out)
    print(name,json.dumps(out['metrics'],indent=2),flush=True)
(ROOT/args.group/'audit.json').write_text(json.dumps(results,indent=2)+'\n')
