"""Classify retained isolation failure; never executes native code or accepts it."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('independent_reader',HERE/'review_buffer_roughness_runtime_r4_v2.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    assert not args.output.exists();root=args.root.resolve();d=r.read(root/'execution-declaration.json')
    off,on=d['tasks'][2:4];assert off['lane']==on['lane']=='modern' and off['mode']==0 and on['mode']==1
    paths=[Path(t['folder']) for t in (off,on)];counts=Counter();first={};maximum={};bindings={}
    for t,p in zip((off,on),paths):
        rec=r.read(p/'record.json');assert rec['completed'] and rec['physical_pass']
        for name,h in rec['outputs'].items():assert r.sha(p/'output'/name)==h
        for name,h in rec['observer_files'].items():assert r.sha(p/'observations'/name)==h
        for file in [p/'record.json',p/'observations/roughness-contract.txt']:
            bindings[str(file.resolve())]=r.sha(file)
    for (key,a),(other,b) in zip(*(r.contract_frames(p/'observations/roughness-contract.txt',t) for p,t in zip(paths,(off,on))),strict=True):
        assert key==other
        for tag in sorted(a.keys()|b.keys()):
            if a.get(tag)!=b.get(tag):
                name=f'OFE{key[3]}/{tag[0]}';counts[name]+=1
                if name not in first:first[name]={'key':key,'tag':tag,'off':a.get(tag),'on':b.get(tag)}
                if tag in a and tag in b:maximum[name]=max(maximum.get(name,0),max(abs(x-y) for x,y in zip(a[tag],b[tag])))
    protected=[k for k in counts if any(tag in k for tag in ('RRC_DENSITY','RRC_DRIVERS','RRC_CONTEXT'))]
    assert not protected
    tables={}
    for kind,sub in [('WAT','output/interchange/H.wat.parquet'),('SOIL','derived/H.soil.parquet'),('ELEMENT','output/interchange/H.element.parquet')]:
        files=[p/sub for p in paths];tt=[[x for x in pq.read_table(f).to_pylist() if x['OFE']<3] for f in files]
        assert len(tt[0])==len(tt[1]);changes=[];columns=Counter()
        for a,b in zip(*tt):
            key={k:a[k] for k in ('year','julian','OFE')};assert key=={k:b[k] for k in key}
            fields={k:[a[k],b[k]] for k in a if a[k]!=b[k]}
            if fields:
                columns.update(fields.keys());changes.append({'key':key,'fields':fields})
        tables[kind]={'upstream_rows_per_lane':len(tt[0]),'changed_rows':len(changes),'first_three_changes':changes[:3], 'changed_column_counts':dict(columns)}
        for f in files:bindings[str(f.resolve())]=r.sha(f)
    src=Path(r.read(root/'intervention-map.json')['source_base'])
    for n in ['irs.for','xinflo.for','param.for','shears.for','decomp.for','covcal.for','infpar.for']:
        bindings[str((src/n).resolve())]=r.sha(src/n)
    for f in [root/'execution-declaration.json',root/'build-receipt.json',Path(__file__).resolve(),HERE/'review_buffer_roughness_runtime_r4_v2.py']:
        bindings[str(f.resolve())]=r.sha(f)
    out={'accepted_isolation':False,'accepted_interpretation':False,'native_runs_by_reviewer':0,
         'scope':'Retained first-pair modern off/on diagnostic failure; no annual-improvement interpretation or tolerance change.',
         'raw_state_change_counts':dict(counts),'first_raw_state_change_per_tag_ofe':list(first.values()),
         'maximum_absolute_state_difference_per_tag_ofe':maximum,'protected_density_driver_differences':protected,
         'upstream_published_changes':tables,'source_supported_hypothesis':'Connected-segment duration is reassigned upstream by IRS; changed peak feeds XINFLO/PARAM/SHEARS persistent rill width. Residue/cover and infiltration/decomposition are possible later feedback paths. Exact event-chain attribution requires bounded observation replay; source possibilities alone do not prove each link.',
         'bindings':bindings}
    args.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({'protected_differences':0,'tables':{k:v['changed_rows'] for k,v in tables.items()}}))

if __name__=='__main__':main()
