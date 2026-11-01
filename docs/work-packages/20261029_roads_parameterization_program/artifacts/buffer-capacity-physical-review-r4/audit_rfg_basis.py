"""Audit retained emitted rock-fraction lineage for the nine selected generated cases."""
import argparse
import csv
import hashlib
import json
import shlex
import math
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_emitted(text):
    lines=[line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if lines[:2]!=['9002','Any comments:']:raise ValueError('Unexpected emitted soil format')
    count=lines[2].split()
    if len(count)!=2 or count!=['3','0']:raise ValueError('Unexpected emitted OFE count/context')
    index=3;profiles=[]
    for _ in range(3):
        runtime=shlex.split(lines[index]);index+=1
        if len(runtime)!=5:raise ValueError('Malformed role runtime header')
        header=shlex.split(lines[index]);index+=1
        if len(header)!=8:raise ValueError('Malformed role material header')
        nsl=int(header[2]);horizons=[]
        for layer in range(nsl):
            values=list(map(float,lines[index].split()));index+=1
            if len(values)!=18 or not all(math.isfinite(x) for x in values):raise ValueError('Malformed9002 horizon')
            if values[0]<=0 or (horizons and values[0]<=horizons[-1]['solthk']):raise ValueError('Horizon order/depth')
            horizons.append(dict(solthk=values[0],rfg=values[10]))
        restriction=list(map(float,lines[index].split()));index+=1
        if len(restriction)!=3:raise ValueError('Malformed restriction row')
        profiles.append(dict(slid=header[0],texid=header[1],nsl=nsl,horizons=horizons))
    if index!=len(lines):raise ValueError('Unexpected trailing soil records')
    return profiles


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    repo=a.repo.resolve();art=repo/'docs/work-packages/20261029_roads_parameterization_program/artifacts';raw=repo/'out/roads-parameterization-program-20261031'
    old=raw/'restriction-provenance-inputs';records=json.loads((art/'restriction-source-retention-v1.json').read_text());bindings={}
    def bind(p,expected=None):
        h=sha(p)
        if expected is not None and h!=expected:raise ValueError(f'Hash drift:{p}')
        st=p.stat();bindings[str(p)]=dict(sha256=h,bytes=st.st_size,mtime_ns=st.st_mtime_ns)
    for p in (repo/'wepppy/soils/ssurgo/ssurgo.py',old/'ssurgo.py'):bind(p,records['ssurgo.py']['sha256'])
    bind(art/'restriction-source-retention-v1.json')
    decl=raw/'buffer-roughness-hillslope-response-r4/attempt-u2/execution-declaration.json';bind(decl,'e291e9b290f0bf5a360ba74a673e63bca9aa1307a52e6d5fce6de0836e71c30e')
    tasks=json.loads(decl.read_text())['tasks'];selected=[t for t in tasks if t['lane']=='modern'];assert len(selected)==18
    materials=sorted({t['case']['soil'] for t in selected});assert materials==['1718465','1718494','1856573','2711184']
    source_layers={}
    for material in materials:
        p=old/(material+'.sol');bind(p,records[material+'.sol']['sha256'])
        hs=[]
        for line in p.read_text().splitlines():
            cells=line.split()
            if len(cells)!=11 or line.lstrip().startswith('#'):continue
            try:vals=list(map(float,cells))
            except ValueError:continue
            hs.append((vals[0],vals[-1]))
        if not hs:raise ValueError('Missing retained source horizons')
        source_layers[material]=hs
    rows=[]
    for t in selected:
        p=Path(t['folder'])/'runs/p1.sol';bind(p,t['inputs']['p1.sol'])
        emitted=parse_emitted(p.read_text())
        if len(emitted)!=len(t['soil_readback']):raise ValueError('Declared/emitted profile count')
        for actual,declared in zip(emitted,t['soil_readback']):
            if actual['slid']!=declared['slid'] or actual['texid']!=declared['texid'] or actual['nsl']!=declared['nsl']:raise ValueError('Declared/emitted role header')
            if actual['horizons']!=[dict(solthk=h['solthk'],rfg=h['rfg']) for h in declared['horizons']]:raise ValueError('Declared/emitted horizon order/depth/RFG')
        for ofe,profile in enumerate(emitted,1):
            for ix,h in enumerate(profile['horizons'],1):
                if h['solthk']>200:continue
                original=next(v for end,v in source_layers[t['case']['soil']] if h['solthk']<=end)
                if h['rfg']!=original:raise ValueError('RFG material changed in normalized upper200mm')
                rows.append(dict(stratum=t['stratum'],mode=t['mode'],material=t['case']['soil'],ofe=ofe,input_horizon=ix,cumulative_depth_mm=h['solthk'],emitted_rfg_percent=h['rfg'],retained_source_rfg_percent=original,exact=True))
    with (a.out/'emitted-rfg-lineage.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    for path,entry in bindings.items():
        p=Path(path);s=p.stat();assert dict(sha256=sha(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)==entry
    receipt=dict(passed=True,generated_histories=18,upper200mm_input_horizon_rows=len(rows),materials=materials,ssurgo_source_matches_retained_audit=True,bindings=bindings,reader_sha256=sha(Path(__file__)),table_sha256=sha(a.out/'emitted-rfg-lineage.csv'),
        direct_emitted_parse='9002 headers and all18-field horizon records; exact role horizon counts/order/depth/RFG against declaration before upper200mm source join',
        conclusion='Builder combines weight-basis fraggt10_r,frag3to10_r,sieveno10_r and emits smr as RFG. fragvol_r is metadata, not this emitted quantity. No volume-to-mass correction is warranted by these field names.',
        limitation='Source snapshot belongs to retained provenance audit, not independently captured original September generation execution. Original raw sieve values are not in this compact capsule; no remote/current SSURGO data substituted. Native computational remapping and field representativeness are separate questions.')
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(len(rows),'upper200mm horizon rows exact')


if __name__=='__main__':main()
