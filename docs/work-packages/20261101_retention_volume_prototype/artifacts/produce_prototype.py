"""Experimental paired actual writer outputs; production preparation unchanged."""
import argparse
import copy
import hashlib
import json
import math
import platform
import re
from pathlib import Path
import wepppy.soils.ssurgo.ssurgo as ss
from wepppy.wepp.soils.utils import WeppSoilUtil

PANEL = ['84543623','84543461','84543462','87913598','85179904','85179901']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, obj):
    with p.open('x') as f:
        json.dump(obj,f,indent=2,allow_nan=False); f.write('\n')
def finite(v): return isinstance(v,(int,float)) and math.isfinite(v)
def decision(r):
    if r['status'] != 'serialized': return 'prior-exclusion',None
    s,p=r['source'],r['prepared']
    if set(r['final_branches'].values()) != {'source-capped-mass'}: return 'fallback-unchanged',None
    rho=s.get('dbthirdbar_r'); fc=s.get('wthirdbar_r'); wp=s.get('wfifteenbar_r'); w=p['mass_percent']/100
    if not all(finite(v) for v in [rho,fc,wp,w]): return 'missing-original-input',None
    if not 0<rho<2.65: return 'density-assumption-conflict',None
    if not 0<=w<=.85: return 'native-cap-conflict',None
    if not 0<wp<fc: return 'zero-or-unordered-source',None
    share=2.65*(1-w)/(rho*w+2.65*(1-w))
    values=dict(fc=fc/100/share,wp=wp/100/share,share=share,screen_porosity=1-rho/2.65)
    if not 0<values['wp']<values['fc']<values['screen_porosity']: return 'porosity-assumption-conflict',values
    return 'eligible',values

def soil_for(h,r):
    soil=ss.WeppSoil.__new__(ss.WeppSoil)
    soil.log=[]; soil.mukey=int(r['source']['mukey'])
    soil.description='# Controlled retention audit: '+r['id']
    soil.num_ofes=1; soil.ksflag=0; soil.is_urban=False; soil.is_water=False
    soil.initial_sat=.75
    soil.majorComponent=ss.MajorComponent(dict(muname='controlled single horizon',albedodry_r=.16))
    soil.horizons=[h]; soil.horizons_mask=[1]; soil.num_layers=1
    soil.res_lyr_i=None; soil.res_lyr_ksat=None
    return soil

def main(old,out):
    out.mkdir()
    producer_hash=sha(__file__)
    if sha(old/'audit-v1/receipt.json')!='8cc2b27294120ad5d5edf1cab8b84645e7ecefff57f1c7ba81e79286cebb1792': raise ValueError('Unaccepted prior receipt')
    if sha(old/'audit-v1/declaration.json')!='cfd6092d1c38fafd3e5e35c69f177c4301e26096264ce3b5c063dff5301c13b6': raise ValueError('Unaccepted prior declaration')
    original=json.loads((old/'audit-v1/receipt.json').read_text())
    declared=json.loads((old/'audit-v1/declaration.json').read_text())
    for name,digest in declared['dependencies'].items():
        if sha(name)!=digest: raise ValueError('Dependency drift '+name)
    baseline_hash=sha(old/'audit-v1/receipt.json')
    if len(original['results'])!=72: raise ValueError('Panel drift')
    save(out/'declaration.json',dict(producer_sha256=sha(__file__),old_receipt_sha256=baseline_hash,
        dependencies=declared['dependencies'],panel=PANEL,python=platform.python_version(),
        scope='Actual writer; isolated prepared retention override; original exclusions retained without reattempt'))
    rows=[]
    for r in original['results']:
        reason,values=decision(r)
        row=dict(id=r['id'],kind=r['kind'],reason=reason,inverse=values,prior_status=r['status'],source=r['source'])
        dest=out/r['id']; dest.mkdir()
        if r['status']!='serialized':
            row['original_exclusion']=r; save(dest/'receipt.json',row); rows.append(row); continue
        oldfile=old/'audit-v1'/r['id']/'audit.sol'
        if sha(oldfile)!=r['artifact_sha256']: raise ValueError('Prior soil drift')
        h=ss.Horizon(str(r['source']['chkey']),dict(r['source'],texture='retention-audit',reskind=None,fragvol_r=None),defaults={})
        for lane in ['baseline','candidate']:
            target=dest/lane; target.mkdir()
            prepared=copy.deepcopy(h)
            if lane=='candidate' and reason=='eligible': prepared.field_cap=values['fc']; prepared.wilt_pt=values['wp']
            soil_for(prepared,r).write(wd=str(target),fname='audit.sol',overwrite=False,version='7778')
            path=target/'audit.sol'
            row[lane]=dict(sha256=sha(path),fc=prepared.field_cap,wp=prepared.wilt_pt,
                parsed=WeppSoilUtil(str(path)).obj)
        if (dest/'baseline/audit.sol').read_bytes()!=oldfile.read_bytes(): raise ValueError('Baseline writer drift')
        base=row['baseline']['parsed']; cand=row['candidate']['parsed']; normalized=copy.deepcopy(cand)
        for b,c,n in zip(base['ofes'][0]['horizons'],cand['ofes'][0]['horizons'],normalized['ofes'][0]['horizons'],strict=True):
            for field in ['fc','wp']:
                expected=row['candidate'][field]
                if c[field]!=float(f'{expected:.4f}'): raise ValueError('Candidate precision')
                n[field]=b[field]
        base_lines=(dest/'baseline/audit.sol').read_bytes().splitlines(keepends=True)
        candidate_lines=(dest/'candidate/audit.sol').read_bytes().splitlines(keepends=True)
        if len(base_lines)!=len(candidate_lines): raise ValueError('Text support drift')
        for index in range(5,5+len(base['ofes'][0]['horizons'])):
            tokens=list(re.finditer(rb'\S+',candidate_lines[index])); prior_tokens=base_lines[index].split()
            for field in [5,4]:
                token=tokens[field]; line=candidate_lines[index]
                candidate_lines[index]=line[:token.start()]+prior_tokens[field]+line[token.end():]
        if candidate_lines!=base_lines: raise ValueError('Nonretention byte drift')
        if normalized!=base: raise ValueError('Nonretention numeric mutation')
        if reason!='eligible' or r['prepared']['mass_percent']==0:
            if row['baseline']['sha256']!=row['candidate']['sha256']: raise ValueError('Compatibility drift')
        row['only_retention_changed']=True
        save(dest/'receipt.json',row); rows.append(row)
    for key in PANEL:
        row=next(r for r in rows if r['id']=='source-'+key)
        if row['reason']!='eligible': raise ValueError('Selected case ineligible')
    if sha(old/'audit-v1/receipt.json')!=baseline_hash: raise ValueError('Prior mutated')
    if any(sha(p)!=v for p,v in declared['dependencies'].items()): raise ValueError('Dependency changed')
    if sha(__file__)!=producer_hash: raise ValueError('Producer changed')
    save(out/'receipt.json',dict(passed=True,cases=rows,panel=PANEL,prior_receipt_unchanged=True))
    print(json.dumps({reason:sum(r['reason']==reason for r in rows) for reason in sorted({r['reason'] for r in rows})}))
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--old',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); main(a.old,a.out)
