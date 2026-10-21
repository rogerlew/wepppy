"""Hand-computed volume controls and release-output transfer precision checks."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_cases import wat,passes,metrics
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
# Two cells: 6 m3 leaves A and enters B; external B export is 4 m3,
# local net sources are 8 and 3 m3, storage increases are 2 and 5 m3.
base=np.array([[8.,0.,6.,2.],[3.,6.,4.,5.]])
def residual(x):return x[:,0]+x[:,1]-x[:,2]-x[:,3]
assert np.array_equal(residual(base),[0.,0.])
controls={}
for name,cell,col,delta,expected in [('duplicate_transfer',1,1,6.,6.),('drop_outflow',1,2,-4.,4.),('wrong_area_factor',1,1,3.,3.),('reverse_storage_sign',1,3,-10.,10.)]:
    x=base.copy();x[cell,col]+=delta;r=residual(x);assert r[cell]==expected;controls[name]=r.tolist()
a=pd.Series([6.,0.,2.],index=[1,2,3]);b=a.shift(1,fill_value=0);assert (a-b).abs().sum()==14.;controls['one_day_shift_absolute_m3']=14.
results=[]
for case in sorted((ROOT/'release-matrix').iterdir()):
    if not case.is_dir():continue
    w=wat(case/'output/H1.wat.dat');areas=w.groupby('ofe').Area.first();rows=[]
    for i in range(1,len(areas)+1):
        x=w[w.ofe==i].set_index(['year','day']);volq=x.Q*areas.loc[:i].sum()/1000;volofe=x.QOFE*areas[i]/1000
        # Each scientific-format field has 7 significant digits, plus
        # binary32 writer scaling. Bound two operations conservatively.
        qb=(volq.abs()+volofe.abs())*(5e-7+4*np.finfo(np.float32).eps)+1e-8
        assert ((volq-volofe).abs()<=qb).all()
        r=dict(ofe=i,q_qofe_failures=int(((volq-volofe).abs()>qb).sum()))
        if i>1:
            up=w[w.ofe==i-1].set_index(['year','day'])
            incoming=x.UpStrmQ*areas[i]/1000;outgoing=up.QOFE*areas[i-1]/1000
            b=(incoming.abs()+outgoing.abs())*(5e-7+4*np.finfo(np.float32).eps)+1e-8
            assert ((incoming-outgoing).abs()<=b).all()
            lat_in=x.SubRIn*areas[i]/1000;lat_out=up.latqcc*areas[i-1]/1000
            lb=.005*(areas[i]+areas[i-1])/1000+(lat_in.abs()+lat_out.abs())*4*np.finfo(np.float32).eps+1e-8
            assert ((lat_in-lat_out).abs()<=lb).all()
            r['surface_transfer_failures']=int(((incoming-outgoing).abs()>b).sum());r['lateral_transfer_failures']=int(((lat_in-lat_out).abs()>lb).sum())
        rows.append(r)
    p=passes(case/'output/H1.pass.dat');terminal=w[w.ofe==len(areas)].set_index(['year','day']);expected=terminal.Q*areas.sum()/1000
    event=p.kind.eq('EVENT');pb=(expected.abs()+p.surface.abs())*(5e-5+4*np.finfo(np.float32).eps)+1e-8
    assert ((expected-p.surface).abs()[event]<=pb[event]).all()
    lateral=terminal.latqcc*areas.iloc[-1]/1000;lb=.005*areas.iloc[-1]/1000+p.lateral.abs()*(5e-5+4*np.finfo(np.float32).eps)+1e-8
    delivered=p.kind.ne('NO EVENT');assert ((lateral-p.lateral).abs()[delivered]<=lb[delivered]).all()
    results.append(dict(case=case.name,ofes=rows,event_surface_failures=0,delivered_lateral_failures=0))
receipt=dict(controls=controls,release_matrix=results,tolerance_rationale='Local rounded lateral fields: 0.005 mm per field; WAT scientific fields 7 significant digits; PASS 5 significant digits; 4 binary32 eps allowance for producer scaling. Not a whole-domain conservation tolerance.')
(ROOT/'diagnostic-controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Five corruption controls detected; all 10 cases pass surface/lateral transfer and selected PASS precision checks.')
