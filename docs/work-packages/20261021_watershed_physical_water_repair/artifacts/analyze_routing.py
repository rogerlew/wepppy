from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
ROOT=Path('/workdir/watershed-physical-water-repair-20261021')
def metrics(values):
 return {'signed_sum':float(values.sum()),'absolute_sum':float(values.abs().sum()),'max_abs':float(values.abs().max())}
results=[]
for lane in ['wpa01-observed','wpa02-observed','combined-observed']:
 for name in ['daily-upper60','hourly-upper60']:
  on=ROOT/lane/'cases/on'/name;off=ROOT/lane/'cases/off'/name
  differences=[]
  for tree in ['output','runs']:
   for p in (off/tree).iterdir():
    if p.is_file() and p.read_bytes()!=(on/tree/p.name).read_bytes():differences.append(str(p.relative_to(off)))
  assert not differences,differences
  idx=['year','day','element']
  c=pd.read_csv(on/'runs/water_audit_channel.txt',sep=r'\s+',names='year day element channel runon local loss volint sinit sfnl lastStor chvol runvol tmpvol length dt base top lateral'.split()).set_index(idx)
  h=pd.read_csv(on/'runs/water_audit_hydrograph.txt',sep=r'\s+',names='year day element step dt qin qlat qout'.split())
  g=h.groupby(idx)
  assert len(c)==16071 and c.index.is_unique
  assert all(len(x)==145 for _,x in g)
  for k in ['qin','qlat','qout']:
   h[k+'_rect']=np.where(h.step>0,h[k]*h.dt,0.)
   h[k+'_trap']=np.where(h.step>0,(h[k]+g[k].shift())*.5*h.dt,0.)
  a=c.join(h.groupby(idx)[[k+'_'+m for k in ['qin','qlat','qout'] for m in ['rect','trap']]].sum())
  for mode in ['rect','trap']:
   a['input_'+mode]=a['qin_'+mode]+a['qlat_'+mode]*a.length
   a['input_gap_'+mode]=a['input_'+mode]-a.volint
   a['output_gap_'+mode]=a['qout_'+mode]-a.chvol
   a['storage_residual_'+mode]=a['input_'+mode]-a['qout_'+mode]-(a.sfnl-a.sinit)
  result={'lane':lane,'case':name,'days':len(c),'observation_parity':True,'metrics':{key:metrics(a[key]) for key in a if 'gap_' in key or 'residual_' in key},'negative_local_days':int(((a.local-a.loss)<0).sum()),'negative_local_volume':float((a.local-a.loss).clip(upper=0).sum())}
  a.to_csv(on/'channel-ledger.csv')
  (on/'audit.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result);print(json.dumps(result),flush=True)
(ROOT/'routing-accounting.json').write_text(json.dumps(results,indent=2)+'\n')
