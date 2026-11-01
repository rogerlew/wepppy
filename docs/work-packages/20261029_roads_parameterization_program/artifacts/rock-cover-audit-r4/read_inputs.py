"""Read only the 36 accepted Roads histories; no model or production imports."""
import argparse
import csv
import hashlib
import json
import math
import re
import shlex
from pathlib import Path

DECL_SHA = 'e291e9b290f0bf5a360ba74a673e63bca9aa1307a52e6d5fce6de0836e71c30e'
MATERIALS = {'1718465','1718494','1856573','2711184'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def clean(text):
    return [s for line in text.splitlines() if (s:=line.split('#',1)[0].strip())]

def soil(text):
    lines=clean(text); version=lines[0]
    if version not in ('98.4','9002'): raise ValueError('unsupported soil format')
    if lines[2].split()!=['3','0']: raise ValueError('wrong OFE count/context')
    ix=3; result=[]
    for ofe in range(1,4):
        if version=='9002':
            if len(shlex.split(lines[ix]))!=5: raise ValueError('runtime header')
            ix+=1
        h=shlex.split(lines[ix]);ix+=1
        if len(h)!=(8 if version=='9002' else 9): raise ValueError('material header')
        n=int(h[2]); previous=0.; layers=[]
        for j in range(n):
            vals=list(map(float,lines[ix].split()));ix+=1
            if len(vals)!=(18 if version=='9002' else 6):raise ValueError('horizon width')
            if not all(math.isfinite(v) for v in vals):raise ValueError('nonfinite')
            depth=vals[0];rfg=vals[10 if version=='9002' else 5]
            if depth<=previous or not 0<=rfg<=100:raise ValueError('depth or RFG bounds')
            layers.append(dict(horizon=j+1,top_mm=previous,bottom_mm=depth,rfg_pct=rfg));previous=depth
        if version=='9002':
            if len(lines[ix].split())!=3:raise ValueError('restriction record')
            ix+=1
        result.append(dict(ofe=ofe,role=h[0],format=version,layers=layers))
    if ix!=len(lines):raise ValueError('trailing soil records')
    return result

def management(text):
    a='# Initial Conditions Section #';b='# Surface Effects Section #';c='# Management Section #'
    if any(text.count(k)!=1 for k in (a,b,c)):raise ValueError('missing/duplicate section')
    block=clean(text.split(a)[1].split(b)[0]);
    if block[0]!='3':raise ValueError('initial count')
    ix=1; result=[]
    for scenario in range(1,4):
        # Scenario header is name and three comment records; blank comment counts.
        # Retained files have only two nonempty description records.
        name=block[ix];ix+=3
        if block[ix]!='1':raise ValueError('not supported cropland initial format')
        ix+=1
        v=list(map(float,block[ix].split()));ix+=1
        if len(v)!=6:raise ValueError('cropland initial six fields')
        iresd=int(block[ix]);imngmt=int(block[ix+1]);ix+=2
        w=list(map(float,block[ix].split()));ix+=1
        if len(w)!=5:raise ValueError('cropland initial five fields')
        rtyp=int(block[ix]);ix+=1
        z=list(map(float,block[ix].split()));ix+=1
        mass=list(map(float,block[ix].split()));ix+=1
        if len(z)!=5 or len(mass)!=2:raise ValueError('initial tail')
        if any(not 0<=x<=1 for x in (v[1],v[5],w[2])):raise ValueError('cover fraction bounds')
        result.append(dict(initial_scenario=scenario,scenario_name=name,landuse=1,cancov=v[1],inrcov=v[5],rilcov=w[2],rrinit_m=w[3],rspace_m=w[4],root_mass_kg_m2=mass[0],submerged_residue_mass_kg_m2=mass[1],explicit_roki='absent_cropland_format',explicit_rokr='absent_cropland_format'))
    if ix!=len(block):raise ValueError('trailing initial records')
    tail=clean(text.split(c)[1]);n=int(tail[4]);indices=list(map(int,tail[5:5+n]))
    if n!=3 or sorted(indices)!=[1,2,3]:raise ValueError('initial OFE binding missing or duplicate')
    return [dict(ofe=i+1,**result[k-1]) for i,k in enumerate(indices)]

def write_csv(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);repo=a.repo.resolve(); bindings={}
    def bind(p,expected=None):
        p=p.resolve();h=sha(p)
        if expected and h!=expected:raise ValueError('input hash drift: '+str(p))
        st=p.stat();bindings[str(p)]=dict(sha256=h,bytes=st.st_size,mtime_ns=st.st_mtime_ns)
    decl=repo/'out/roads-parameterization-program-20261031/buffer-roughness-hillslope-response-r4/attempt-u2/execution-declaration.json';bind(decl,DECL_SHA)
    tasks=json.loads(decl.read_text())['tasks']; keys=[(t['stratum'],t['lane'],t['mode']) for t in tasks]
    if len(keys)!=36 or len(set(keys))!=36:raise ValueError('missing/duplicate history')
    strata=list(dict.fromkeys(t['stratum'] for t in tasks));cases={s:'B'+str(i+1) for i,s in enumerate(strata)}
    if len(strata)!=9 or {t['case']['soil'] for t in tasks}!=MATERIALS:raise ValueError('unexpected panel')
    soils=[];mans=[];histories=[]
    for t in tasks:
        if {(x['lane'],x['mode']) for x in tasks if x['stratum']==t['stratum']}!={('legacy',0),('legacy',1),('modern',0),('modern',1)}:raise ValueError('coverage')
        root=Path(t['folder'])/'runs';sp=root/'p1.sol';mp=root/'p1.man';bind(sp,t['inputs']['p1.sol']);bind(mp,t['inputs']['p1.man'])
        ss=soil(sp.read_text());mm=management(mp.read_text())
        base=dict(case=cases[t['stratum']],stratum=t['stratum'],case_id=t['event']['case_id'],lane=t['lane'],mode=t['mode'],material=t['case']['soil'])
        for p,d in zip(ss,t['soil_readback']):
            if p['role']!=d['slid'] or len(p['layers'])!=d['nsl']:raise ValueError('soil declared header mismatch')
            for layer,dl in zip(p['layers'],d['horizons']):
                if layer['bottom_mm']!=dl['solthk'] or layer['rfg_pct']!=dl['rfg']:raise ValueError('soil declaration mismatch')
                soils.append(dict(**base,ofe=p['ofe'],role=p['role'],soil_format=p['format'],**layer))
        for m in mm:mans.append(dict(**base,**m))
        histories.append(dict(**base,soil_sha256=sha(sp),management_sha256=sha(mp)))
    for s in strata:
        h=[x for x in histories if x['stratum']==s]
        if len({x['management_sha256'] for x in h})!=1:raise ValueError('management differs between lanes or modes')
        for lane in ('legacy','modern'):
            if len({x['soil_sha256'] for x in h if x['lane']==lane})!=1:raise ValueError('soil differs across roughness mode')
    # Actual parser negative controls rather than mirrored arithmetic assertions.
    controls={}
    for label,parser,value in [('missing_section',management,mp.read_text().replace('# Initial Conditions Section #','missing',1)),('duplicate_section',management,mp.read_text()+'\n# Initial Conditions Section #'),('nonmonotonic_depth',soil,re.sub(r'(?m)^\s*200(?:\.0*)?\s+', '0 ', sp.read_text(), count=1))]:
        try:parser(value)
        except ValueError:controls[label]=True
        else:raise ValueError('negative control did not reject '+label)
    write_csv(a.out/'soil-fragments.csv',soils);write_csv(a.out/'management-cover.csv',mans);write_csv(a.out/'histories.csv',histories)
    for name,b in bindings.items():
        p=Path(name);st=p.stat()
        if dict(sha256=sha(p),bytes=st.st_size,mtime_ns=st.st_mtime_ns)!=b:raise ValueError('original mutated')
    receipt=dict(passed=True,histories=len(histories),soil_horizon_rows=len(soils),management_ofe_rows=len(mans),management_unique_files=len({h['management_sha256'] for h in histories}),all_four_histories_per_case_management_identical=True,all_roughness_pair_soils_identical=True,explicit_surface_rock_fields='absent in all cropland initial scenarios; not asserted zero surface rock',controls=controls,bindings=bindings,reader_sha256=sha(Path(__file__)),tables={p.name:sha(p) for p in sorted(a.out.glob('*.csv'))},limits=['Input initial cover is not event-day cover.','No field measurements or RUSLE run artifacts are inferred.','Soil file horizons are not native computational layers.','Modern lane remains conditioned erosion_road_cap.'])
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ('bindings','limits')},indent=2))
if __name__=='__main__':main()
