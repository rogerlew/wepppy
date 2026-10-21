from pathlib import Path
import json,calendar,sys,hashlib
import numpy as np
import pandas as pd
sys.path.insert(0,'/workdir/wepppy/docs/work-packages/20261021_watershed_physical_water_audit/artifacts')
from audit_cases import wat,passes,audit
ROOT=Path('/workdir/watershed-physical-water-repair-20261021')
results=[]
for receipt in sorted((ROOT/'mc-guard-replays').glob('*/*/execution.json')):
 case=receipt.parent;meta=json.loads(receipt.read_text())
 if not all(r['success'] for r in meta['records']):continue
 years=400 if meta['group']=='calendar' else (2 if meta['group']=='portable' else 44)
 expected=pd.MultiIndex.from_tuples([(y,d) for y in range(1980,1980+years) for d in range(1,366+calendar.isleap(y))],names=['year','day'])
 records=[]
 for path in sorted((case/'output').glob('H*.wat.dat')):
  w=wat(path);assert np.isfinite(w.to_numpy()).all()
  assert not w.duplicated(['year','day','ofe']).any()
  for _,ofe in w.groupby('ofe'):
   assert pd.MultiIndex.from_frame(ofe[['year','day']]).equals(expected)
  p=passes(path.with_suffix('.dat').with_name(path.name.replace('.wat.','.pass.')))
  assert p.index.equals(expected)
  assert np.isfinite(p.select_dtypes('number').to_numpy()).all()
  area=w.groupby('ofe').Area.first();qerrors=[];surface=[];lateral=[]
  for k in sorted(area.index):
   a=w[w.ofe==k].set_index(['year','day']);qgap=(a.QOFE*a.Area-a.Q*area.loc[:k].sum())/1000
   bound=(abs(a.QOFE*a.Area)+abs(a.Q*area.loc[:k].sum()))*2e-6/1000+1e-9
   assert (abs(qgap)<=bound).all()
   qerrors.append(float(abs(qgap).max()))
   if k>1:
    prev=w[w.ofe==k-1].set_index(['year','day'])
    sgap=(a.UpStrmQ*a.Area-prev.QOFE*prev.Area)/1000
    sbound=(abs(a.UpStrmQ*a.Area)+abs(prev.QOFE*prev.Area))*2e-6/1000+1e-9
    assert (abs(sgap)<=sbound).all()
    lgap=(a.SubRIn*a.Area-prev.latqcc*prev.Area)/1000
    lbound=(a.Area+prev.Area)*.005/1000+1e-8
    assert (abs(lgap)<=lbound).all()
    surface.append(float(abs(sgap).max()));lateral.append(float(abs(lgap).max()))
  records.append({'hill':path.stem,'days':len(p),'ofes':len(area),'first':list(map(int,p.index[0])),'last':list(map(int,p.index[-1])),'q_qofe_max_m3':max(qerrors),'surface_transfer_max_m3':max(surface,default=0),'lateral_transfer_max_m3':max(lateral,default=0)})
 path=case/'runs/chanwb.out';lines=path.read_text().splitlines();start=next(i for i,s in enumerate(lines) if len(s.split())==10 and s.split()[0].isdigit())
 ch=pd.read_csv(path,sep=r'\s+',skiprows=start,header=None)
 assert np.isfinite(ch.to_numpy()).all()
 for _,channel in ch.groupby(2):assert pd.MultiIndex.from_arrays([channel[0],channel[1]],names=['year','day']).equals(expected)
 result={'group':meta['group'],'case':case.name,'configured_years':years,'hills':records,'channel_days':len(ch),'full_period':True}
 if meta['group']=='release-matrix':result['accounting']=audit(case)
 (case/'validation.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
 print(meta['group'],case.name,years,len(expected),'PASS',flush=True)
(ROOT/'mc-guard-validation.json').write_text(json.dumps(results,indent=2)+'\n')
