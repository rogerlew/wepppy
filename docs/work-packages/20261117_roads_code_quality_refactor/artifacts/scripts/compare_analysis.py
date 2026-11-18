"""Compare all parsed native case/summary semantics with exact numeric equality."""
from pathlib import Path
import json,hashlib
base=Path('/tmp/roads-refactor-validation/native-baseline/roads_matrix0/analysis.json')
candidate=Path('/tmp/roads-refactor-validation/native-candidate-20261117b/roads_matrix0/analysis.json')
left,right=[json.loads(p.read_text()) for p in [base,candidate]]
assert len(left)==len(right)==516
assert {x['segment_run_id'] for x in left}==set(range(1,517))
assert {x['segment_run_id'] for x in right}==set(range(1,517))
right_by_id={x['segment_run_id']:x for x in right};differences=[]
for row in left:
 other=right_by_id[row['segment_run_id']]
 a={k:v for k,v in row.items() if k!='elapsed_seconds'}
 b={k:v for k,v in other.items() if k!='elapsed_seconds'}
 if a!=b:differences.append(row['name'])
receipt={'baseline':str(base),'candidate':str(candidate),'analysis_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [base,candidate]},'cases':516,'comparison':'All analyzed case and parsed scientific summary values exact; only elapsed_seconds excluded. Input/output/template hash receipts remain exact.','differences':differences,'pass':not differences}
Path('/tmp/roads-refactor-validation/analysis-candidate-20261117b-comparison.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
assert not differences
