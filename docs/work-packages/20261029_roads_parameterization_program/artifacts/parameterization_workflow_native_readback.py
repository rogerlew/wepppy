"""Independent native-input readback for the disposable real Roads workflow."""
import argparse
import hashlib
import json
import re
import shlex
import shutil
from collections import Counter
from pathlib import Path
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

ROOT=Path('/wc1/runs/ro/roads-param-ui-20261103-v1')
RAW=Path('/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1')
FIELDS={'ki_kg_s_m4':5,'kr_s_m':6,'critical_shear_pa':7,'ksat_mm_h':8}
ROLE={'Road':'road','Fill':'fill','Forest':'buffer'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def headers(text):return [shlex.split(s) for s in text.splitlines() if s.lstrip().startswith("'")]

def main(label,attempt=''):
    suffix='-'+attempt if attempt else ''
    receipt_path=RAW/f'native-{label}{suffix}-readback.json'
    if receipt_path.exists():raise FileExistsError(receipt_path)
    from wepppy.nodb.mods.roads import Roads
    state=Roads.getInstance(str(ROOT))._parameterization
    canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode()
    config_hash=hashlib.sha256(canonical(state)).hexdigest()
    baseline=state['baseline']
    for name,asset in baseline['assets'].items():assert hashlib.sha256(asset['text'].encode()).hexdigest()==asset['sha256'],name
    manifest=json.loads((ROOT/'wepp/roads/segments/roads.segment.pass.manifest.json').read_text())
    assert isinstance(manifest,list)
    rows=[row for row in manifest if row['status']=='completed']
    assert len(rows)==35 and not any(row['status']=='failed' for row in manifest)
    values=[];counts=Counter();files={};neutral=[]
    saved=RAW/('default-native-inputs-'+attempt if attempt else 'default-native-inputs')
    if label=='default':saved.mkdir()
    for row in rows:
        prov=row['parameterization'];assert prov['baseline_id']==baseline['id']
        assert prov['configuration_hash']==config_hash
        source_name=next(n for n in prov['source_asset_hashes'] if n.endswith('.sol'))
        source={ROLE[t[0]]:{key:float(t[col]) for key,col in FIELDS.items()} for t in headers(baseline['assets'][source_name]['text'])}
        inputs={Path(x['relpath']).suffix:ROOT/x['relpath'] for x in prov['input_files']}
        assert set(inputs)=={'.sol','.slp','.man'}
        for entry in prov['input_files']:
            p=ROOT/entry['relpath'];assert sha(p)==entry['sha256'];files[entry['relpath']]=entry['sha256']
            if label=='default':shutil.copyfile(p,saved/p.name)
            elif p.suffix in {'.slp','.man'}:
                assert p.read_bytes()==(saved/p.name).read_bytes(),p.name
                neutral.append(p.name)
        actual=headers(inputs['.sol'].read_text());assert len(actual)==len(prov['ofes'])==3
        for t,ofe in zip(actual,prov['ofes']):
            role=ROLE[t[0]];assert role==ofe['role'];counts[role]+=1
            expected=dict(source[role])
            if role=='road' and row['traffic']!='high':
                expected['ki_kg_s_m4']/=4;expected['kr_s_m']/=4
            for field,col in FIELDS.items():
                override=state['overrides'][role][field]
                resolved=expected[field]
                if override['mode']=='multiply':resolved*=override['value']
                elif override['mode']=='absolute':resolved=override['value']
                resolved=float(f'{resolved:.6g}')
                assert float(t[col])==resolved==ofe['emitted'][field],(row['segment_run_id'],role,field)
            values.append({'segment_run_id':row['segment_run_id'],'role':role,'values':{f:float(t[c]) for f,c in FIELDS.items()}})
    current=lifecycle.require_current(ROOT)
    assert set(current)=={'policy','is_single_storm','required_relpaths','parameterization_hash','parameterization_snapshot_sha256'}
    assert current['parameterization_hash']==config_hash
    assert current['parameterization_snapshot_sha256']==sha(ROOT/'wepp/roads/output/roads.parameterization.comparison.json')
    trace_hashes={}
    for rid in [str(row['segment_run_id']) for row in rows]+['w0']:
        p=ROOT/f'wepp/roads/runs/p{rid}.err';text=p.read_text()
        assert 'binary_identity_status=ok' in text and 'WEPP COMPLETED' in text
        trace_hashes[p.name]=sha(p)
    result={'label':label,'baseline_id':baseline['id'],'configuration_hash':config_hash,'profiles':len(rows),
        'role_counts':dict(counts),'native_values':values,'input_hashes':files,'unchanged_geometry_management_files':neutral,
        'native_trace_hashes':trace_hashes,'current_result_receipt':current,'all_roles_exact_input_readback':True}
    receipt_path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(label,len(rows),'profiles',dict(counts),'exact native input propagation and current output receipt passed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label',choices=['default','custom']);p.add_argument('--attempt',default='');args=p.parse_args();main(args.label,args.attempt)
