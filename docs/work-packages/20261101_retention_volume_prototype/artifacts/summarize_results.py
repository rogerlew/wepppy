"""Compact paired initialized-state accounting from accepted observed values."""
import hashlib
import json
from pathlib import Path
import sys
import read_native_v3 as n
source=Path(sys.argv[1]);out=Path(sys.argv[2])
before=hashlib.sha256(source.read_bytes()).hexdigest();r=json.loads(source.read_text())
if not r['passed']: raise ValueError('Unaccepted readback')
rows=[]
for key in ['84543623','84543461','84543462','87913598','85179904','85179901']:
    result=dict(chkey=key)
    for lane in ['baseline','candidate']:
        case=next(x for x in r['cases'] if x['chkey']==key and x['lane']==lane)
        by_ofe=[]
        for ofe in range(1,4):
            selected=[x for x in case['initialization'] if x['ofe']==ofe]
            previous=0.;absolute=0.;structural=0.
            for x in selected:
                thickness=n.sub(x['depth'],previous);previous=x['depth']
                absolute+=x['st']+x['final_wp']*thickness
                structural+=x['por']*thickness
            by_ofe.append(dict(ofe=ofe,st_mm=1000*sum(x['st'] for x in selected),
                absolute_initial_water_mm=1000*absolute,structural_porosity_mm=1000*structural,
                available_ul_minus_st_mm=1000*sum(x['ul']-x['st'] for x in selected)))
        result[lane]=dict(emitted_depth_mm=case['emitted_depth_mm'],native_depth_mm=case['native_depth_mm'],
            first_layer=case['initialization'][0],by_ofe=by_ofe,
            minimum_initialized_drainage_denominator_m=min(x['initialized_drainage_denominator'] for x in case['initialization']),
            all_initialized_domains_valid=all(x['initialized_domains_valid'] for x in case['initialization']))
    result['max_absolute_water_delta_mm']=max(abs(c['absolute_initial_water_mm']-b['absolute_initial_water_mm']) for b,c in zip(result['baseline']['by_ofe'],result['candidate']['by_ofe']))
    rows.append(result)
if hashlib.sha256(source.read_bytes()).hexdigest()!=before: raise ValueError('Readback changed')
with out.open('x') as f:
    json.dump(dict(readback_sha256=before,pairs=rows,comparisons=r['comparisons'],native_reruns=0),f,indent=2);f.write('\n')
print('Summarized six observed pairs')
