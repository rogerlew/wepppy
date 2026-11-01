"""Synthetic protocol/assignment controls; not native scientific fixtures."""
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reader',HERE/'review_buffer_coupling_localization_r4.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def panel():
    rows=[]
    def add(tag,ip,ix,v):
        rows.append({'tag':tag,'year':4,'day':233,'ofe':ip,'index':ix,'values':[r.f32(x) for x in v],'line':len(rows)+1})
    for ip in (1,2,3):add('BP_GEOMETRY',ip,0,[1,10,10*ip,0,0,0])
    add('RC_FRICTION_IN',1,0,[.1,.5,.2,10,2,0]);add('RC_FRICTION_OUT',1,0,[.1,.5,.2,10,2,8.4])
    alpha=r.f32(math.sqrt(r.f32(r.f32(r.f32(r.f32(.1)*8)*r.f32(9.80665))/r.f32(8.4))))
    add('RC_ALPHA',1,0,[alpha,.1,9.80665,8.4,10,1.5])
    add('RC_QINF_SHAPE',1,1,[1.5,1,1,alpha,alpha,2]);add('RC_QINF_PRE',1,1,[.01,alpha,10,1e-6,100,1e-5]);add('RC_QINF_POST',1,1,[.009,alpha,10,1e-6,100,1e-5])
    add('RC_FINAL_OWNER',3,2,[1,3,alpha,1.5,2,.005])
    for ip in (1,2,3):
        runoff=.01 if ip<3 else 0
        add('RC_WRITE_PRE',ip,2,[3,1,0,0,runoff,10])
        peak=r.f32(r.f32(r.f32(r.f32(runoff)*10)/(10*ip))/2)
        add('RC_WRITE_POST',ip,2,[3,1,2,peak,runoff,10])
    add('RC_WIDTH_IN',1,0,[.02,.1,.1,.15,1,0]);add('RC_WIDTH_CAND',1,0,[.02,.2,.1,1,0,0]);add('RC_WIDTH_OUT',1,0,[.02,.1,.15,.15,1,0])
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();assert not a.output.exists()
    good=panel();v=r.reconstruct(good);assert len(v['writeback'])==3 and v['writeback'][0]['owner']!=v['writeback'][0]['terminal']
    passed=['Valid owner different from terminal; complete target range and exact assignments accepted']
    controls=[('duration mutation','RC_WRITE_POST',2,3),('peak mutation','RC_WRITE_POST',3,.1),
              ('width cap mutation','RC_WIDTH_OUT',2,.2),('friction mutation','RC_FRICTION_OUT',5,9),
              ('alpha mutation','RC_ALPHA',0,.01),('QINF unexpected argument mutation','RC_QINF_POST',3,.1)]
    for label,tag,index,value in controls:
        bad=copy.deepcopy(good);next(x for x in bad if x['tag']==tag)['values'][index]=value
        try:r.reconstruct(bad)
        except AssertionError:passed.append(label+' rejected')
        else:raise AssertionError(label)
    for label,bad in [('missing width return',good[:-1]),('missing QINF return',[x for x in good if x['tag']!='RC_QINF_POST']),('duplicate writeback',[*good[:12],good[11],*good[12:]])]:
        try:r.reconstruct(bad)
        except AssertionError:passed.append(label+' rejected')
        else:raise AssertionError(label)
    output={'passed':True,'native_runs':0,'scope':'Synthetic validation of readback ownership and exact-assignment checks, not model validation.','controls':passed,
        'bindings':{str(p.resolve()):r.sha(p) for p in [Path(__file__),HERE/'review_buffer_coupling_localization_r4.py']}}
    a.output.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({'passed':True,'controls':len(passed)}))

if __name__=='__main__':main()
