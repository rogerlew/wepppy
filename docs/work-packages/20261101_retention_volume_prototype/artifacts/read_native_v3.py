"""Read existing native observations; distinguish reconstruction from execution."""
import calendar
from collections import Counter
import hashlib
import math
from pathlib import Path
import re
import struct

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def f(x): return struct.unpack('f',struct.pack('f',x))[0]
def sub(a,b): return f(f(a)-f(b))
def mul(a,b): return f(f(a)*f(b))
def add(a,b): return f(f(a)+f(b))

def guards(dry,fc,sm,por):
    if not all(math.isfinite(v) for v in [dry,fc,sm,por]) or por<=0: raise ValueError('Invalid guard operands')
    branches=[]
    if sm>=por: sm=mul(por,.95); branches.append('sm20-ceiling')
    if fc>=sm:
        delta=sub(fc,dry); fc=mul(sm,.99); dry=sub(fc,delta)
        dry=max(dry,f(.01)); fc=max(fc,f(.01)); branches.append('fc-sm20-pair')
    if f(fc/por)>f(.83):
        temp=f(fc/mul(por,.83)); fc=mul(por,.83); dry=f(dry/temp); branches.append('fc-por-ratio')
    dry=max(dry,f(.01)); fc=max(fc,f(.01))
    return dry,fc,branches

def remapped_inputs(horizons):
    """Binary32 input weighting for this declared two-horizon uniform panel."""
    if len(horizons)!=2 or float(horizons[0]['solthk'])!=200: raise ValueError('Unsupported source support')
    keys=['wp','fc','rfg','bd']
    if any(horizons[0][k]!=horizons[1][k] for k in keys): raise ValueError('Unsupported nonuniform fixture')
    end=mul(min(float(horizons[-1]['solthk'])+200,1800),.001)
    first=mul(200,.001); remaining=[first,sub(end,first)]
    source=[f(horizons[0]['wp']),f(horizons[0]['fc']),f(min(85,float(horizons[0]['rfg']))/100),mul(min(2,max(.8,float(horizons[0]['bd']))),1000)]
    count=round(min(float(horizons[-1]['solthk'])+200,1800)/200)
    boundaries=[]; depth=0.
    for _ in range(count): depth=add(depth,.2); boundaries.append(depth)
    grid=[]; j=0
    for i in range(count):
        spacing=sub(boundaries[i],boundaries[i-1]) if i==count-1 else f(.2)
        need=spacing; values=[0.]*4
        while True:
            take=min(remaining[j],need)
            weight=f(take/spacing)
            values=[add(a,mul(weight,b)) for a,b in zip(values,source)]
            if remaining[j]<=need:
                need=sub(need,remaining[j]); j+=1
                if abs(need)<=f(.001): break
            else:
                remaining[j]=sub(remaining[j],need); break
        grid.append(values)
    return [grid[0],grid[0]]+grid[1:]

def read(root,fixture):
    if fixture['parsed']['ofes'][0]['sat']!=.75: raise ValueError('Unexpected initialization SAT')
    emitted_depth=float(fixture['parsed']['ofes'][0]['horizons'][-1]['solthk'])
    # Pinned input.for adds200mm then caps1800; declared cases only.
    expected_depth=min(emitted_depth+200,1800)
    layers=round((expected_depth-200)/200)+2
    expected={(ofe,i) for ofe in range(1,4) for i in range(1,layers+1)}
    grouped={}; observed_order=[]
    for sequence,line in enumerate((root/'runs/storage-init.txt').read_text().splitlines(),1):
        c=line.split()
        if len(c)!=10 or int(c[1])!=sequence: raise ValueError('Trace framing/sequence')
        tag=c[0]; key=tuple(map(int,c[2:4])); values=list(map(float,c[4:]))
        if not all(math.isfinite(v) for v in values): raise ValueError('Nonfinite trace')
        row=grouped.setdefault(key,{})
        if tag in row: raise ValueError('Duplicate tag')
        row[tag]=values; observed_order.append((key,tag))
    if set(grouped)!=expected: raise ValueError('Computational support mismatch')
    order=['SO_SCON_INPUT','SO_SCON_PORE','SO_SCON_ROCK','SO_SCON_DRY','SO_SCON_UL','SO_SCON_K']
    expected_order=[]
    for ofe in range(1,4):
        keys=sorted(key for key in expected if key[0]==ofe)
        expected_order += [(key,tag) for key in keys for tag in order]
        expected_order += [(key,'SO_WBH_UL') for key in keys]
    if observed_order!=expected_order: raise ValueError('Unexpected observed phase/order')
    checked=[]
    saturation={o:f(.75) for o in range(1,4)}
    emitted=fixture['parsed']['ofes'][0]['horizons'][0]
    expected_inputs=remapped_inputs(fixture['parsed']['ofes'][0]['horizons'])
    for key,t in sorted(grouped.items()):
        inp=t['SO_SCON_INPUT']; por,air,share,rho,*_=t['SO_SCON_PORE']
        rock=t['SO_SCON_ROCK']; dry,fc,*_=t['SO_SCON_DRY']
        ul,_,_,dg,st,depth=t['SO_SCON_UL']
        expected_input=expected_inputs[key[1]-1]
        if [inp[0],inp[1],inp[4],inp[5]]!=expected_input: raise ValueError('Exact native input remap mismatch')
        if por<=0 or share<=0 or dg<=0: raise ValueError('Nonpositive capacity operand')
        rockmass=mul(inp[4],rho)
        expected_cpm=sub(1,f(rockmass/add(rockmass,mul(2650,sub(1,inp[4])))))
        if share!=expected_cpm: raise ValueError('CPM reconstruction drift')
        expected_dry,expected_fc,branches=guards(rock[0],rock[1],rock[2],por)
        if (dry,fc)!=(expected_dry,expected_fc): raise ValueError('Guard reconstruction drift')
        if ul!=mul(sub(por,dry),dg): raise ValueError('UL arithmetic drift')
        wb=t['SO_WBH_UL']
        if wb[:4]!=[ul,por,dry,dg] or wb[5]!=depth: raise ValueError('Water-balance consumed operand drift')
        minimum=f(dry/mul(por,share))
        saturation[key[0]]=max(saturation[key[0]],minimum)
        stock=mul(sub(mul(mul(saturation[key[0]],por),share),dry),dg)
        if stock<f(1e-10): stock=0.0
        if stock!=st or wb[4]!=st: raise ValueError('Initialized stock/clock drift')
        capacity=mul(dg,sub(fc,dry)); drfc=add(capacity,mul(sub(1,air),dg))
        ratio=f(capacity/ul) if ul else None
        expected_cumulative=.1 if key[1]==1 else .2*(key[1]-1)
        if abs(depth-expected_cumulative)>2e-6: raise ValueError('Computational depth drift')
        checked.append(dict(ofe=key[0],layer=key[1],input_wp=inp[0],input_fc=inp[1],input_density=inp[5],native_density=rho,
            cpm=share,por=por,air=air,reconstructed_sat=saturation[key[0]],postrock_wp=rock[0],postrock_fc=rock[1],final_wp=dry,final_fc=fc,
            reconstructed_guard_branches=branches,ul=ul,fc_capacity=capacity,st=st,depth=depth,
            initialized_drainage_denominator=sub(ul,drfc),initialized_fc_ul=ratio,
            initialized_domains_valid=(ratio is not None and 0<ratio<1 and sub(ul,drfc)>0),
            drainage_division_executed=False))
    obs=Counter(); hk=[]; fcul={}; frost=Counter()
    expression=re.compile(r'^(\S+) y=\s*(-?\d+) d=\s*(-?\d+) e=\s*(-?\d+) c=\s*(-?\d+) s=\s*(-?\d+) v1=\s*(\S+) v2=\s*(\S+)\s*$')
    for line in (root/'runs/wepp_observe.log').open():
        m=expression.match(line)
        if not m: raise ValueError('Observe framing')
        tag=m[1]; obs[tag]+=1
        vals=[float(m[7]),float(m[8])]
        if not all(math.isfinite(v) for v in vals): raise ValueError('Nonfinite observation')
        if tag.endswith('HK_FCUL'):
            key=(int(m[4]),int(m[6]))
            if key in fcul: raise ValueError('Duplicate HK operands')
            fcul[key]=dict(values=vals,clock=tuple(int(m[i]) for i in range(2,7)),family=tag.split('_HK_')[0])
        if tag.endswith('HK_RATIO'): hk.append(dict(tag=tag,year=int(m[2]),day=int(m[3]),ofe=int(m[4]),layer=int(m[6]),ratio=vals[0],clock=tuple(int(m[i]) for i in range(2,7)),family=tag.split('_HK_')[0]))
        if tag.startswith(('WFR','FR_LOC')): frost[tag]+=1
    if len(hk)!=len(expected) or {(x['ofe'],x['layer']) for x in hk}!=expected: raise ValueError('HK initialization coverage')
    if set(fcul)!=expected: raise ValueError('HK operand coverage')
    for row in checked:
        values=fcul[(row['ofe'],row['layer'])]['values']
        for observed,actual in zip(values,[row['fc_capacity'],row['ul']],strict=True):
            tolerance=5.1e-5*abs(actual)+1e-12
            if abs(observed-actual)>tolerance: raise ValueError('Executed HK FCUL mismatch')
    for item in hk:
        operands=fcul[(item['ofe'],item['layer'])]
        if item['clock']!=operands['clock'] or item['family']!=operands['family']: raise ValueError('HK clock/family mismatch')
        actual=next(x for x in checked if (x['ofe'],x['layer'])==(item['ofe'],item['layer']))['initialized_fc_ul']
        if actual is None or abs(item['ratio']-actual)>5.1e-6: raise ValueError('HK observation differs')
    outputs={p.name:p for p in (root/'output').iterdir()}
    if set(outputs)!={'H1.'+s+'.dat' for s in ['ebe','element','loss','pass','plot','soil','wat']}: raise ValueError('Output inventory')
    for name,p in outputs.items():
        if not p.stat().st_size: raise ValueError('Empty output')
        for line in p.open():
            tokens=line.split(); stars=[x for x in tokens if set(x)=={'*'}]
            if stars:
                text=line.strip()
                decoration=name=='H1.loss.dat' and (text=='*** CAUTION ***' or (text.startswith(('** Soil Loss (','** Maximum Soil Loss ','** Soil Deposition (','** Maximum Soil Deposition ')) and text.endswith(' **') and stars==['**','**']))
                if not decoration: raise ValueError('Numeric stars or unknown decoration')
            for token in tokens:
                try: value=float(token.replace('D','E'))
                except ValueError: continue
                if not math.isfinite(value): raise ValueError('Nonfinite output')
    keys=set(); depths=set()
    for line in outputs['H1.wat.dat'].open():
        c=line.split()
        if len(c)!=25 or not c[0].isdigit(): continue
        key=tuple(map(int,c[:3]))
        if key in keys: raise ValueError('Duplicate calendar key')
        keys.add(key); depths.add(float(c[21]))
    calendar_keys={(o,d,y) for o in range(1,4) for y in range(1,17) for d in range(1,367 if calendar.isleap(y) else 366)}
    if keys!=calendar_keys or depths!={expected_depth}: raise ValueError('Incomplete calendar/depth')
    return dict(passed=True,emitted_depth_mm=emitted_depth,native_depth_mm=expected_depth,initialization=checked,executed_hk=hk,observation_counts=dict(obs),frost_observation_counts=dict(frost),
        full_calendar_rows=len(keys),output_hashes={n:sha(p) for n,p in outputs.items()},
        limitation='Initialization-domain evidence; no complete-history drainage/accepted-flux closure claim')
