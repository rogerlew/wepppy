"""Strict matrix parity: validate receipts, then compare all inputs and outputs."""
from pathlib import Path
import argparse
import hashlib
import json

parser=argparse.ArgumentParser()
parser.add_argument('baseline',type=Path)
parser.add_argument('candidate',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()

def records(root):
    paths=sorted(root.glob('case-*.json'),key=lambda p:int(p.stem.split('-')[1]))
    assert len(paths)==516, (str(root),len(paths))
    result=[json.loads(p.read_text()) for p in paths]
    assert [r['segment_run_id'] for r in result]==list(range(1,517))
    assert len({r['name'] for r in result})==516
    assert all(r['status']=='completed' for r in result)
    return result

def normalize(data,root):
    return data.replace(str(root).encode(),b'<MATRIX_ROOT>')

left,right=records(args.baseline),records(args.candidate)
identity_a=json.loads((args.baseline/'execution-identity.json').read_text())
identity_b=json.loads((args.candidate/'execution-identity.json').read_text())
assert identity_a['native_sha256']==identity_b['native_sha256'], 'native extension identity changed'
assert {k:v for k,v in identity_a['source_sha256'].items() if k.startswith('wepp_runner/bin/')}=={k:v for k,v in identity_b['source_sha256'].items() if k.startswith('wepp_runner/bin/')}, 'native executable identity changed'
ignored={'elapsed_seconds','input_sha256','output_sha256'}
comparisons=[]
differences=[]
for a,b in zip(left,right):
    if {k:v for k,v in a.items() if k not in ignored}!={k:v for k,v in b.items() if k not in ignored}:
        differences.append({'case':a['name'],'type':'case_semantics'})
    for kind in ('input_sha256','output_sha256'):
        assert set(a[kind])==set(b[kind]), (a['name'],kind,'artifact membership mismatch')
        for rel in sorted(a[kind]):
            data_a=(args.baseline/rel).read_bytes();data_b=(args.candidate/rel).read_bytes()
            assert hashlib.sha256(data_a).hexdigest()==a[kind][rel],('baseline receipt mismatch',rel)
            assert hashlib.sha256(data_b).hexdigest()==b[kind][rel],('candidate receipt mismatch',rel)
            equal=normalize(data_a,args.baseline)==normalize(data_b,args.candidate)
            comparisons.append({'path':rel,'kind':kind,'equal':equal,'raw_equal':data_a==data_b})
            if not equal: differences.append({'case':a['name'],'type':kind,'path':rel})
receipt={'baseline':str(args.baseline),'candidate':str(args.candidate),'cases':516,
         'files_compared':len(comparisons),'normalization':'Exact root-path byte substitution only; case elapsed_seconds excluded; all scientific metadata and native bytes otherwise exact.',
         'raw_equal_files':sum(r['raw_equal'] for r in comparisons),'differences':differences,
         'pass':not differences}
args.output.write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
raise SystemExit(int(bool(differences)))
