"""Rehash consumed decks and recompute completed-control native physical audits."""
from pathlib import Path
import json,hashlib
import continuation as c
import role_boundary_assessment_r3 as role
HERE=Path(__file__).resolve().parent
ROOT=Path('/workdir/wepppy/out/roads-parameterization-program-20261031/legacy-soil-control-r3')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 declaration=json.loads((ROOT/'declaration.json').read_text());rows=json.loads((ROOT/'results.json').read_text())
 assert len(rows)==len(declaration['cases'])==116
 assert sha(ROOT/'executed-study.py')==declaration['script_sha256']
 unique=set();groups={};physical=0
 for row,score in zip(rows,declaration['cases']):
  case=row['case'];assert case==score['case'];name='-'.join(case.values());folder=ROOT/'matrix-v1'/name
  baseline=role.MATRIX/'matrix-v1'/name;original=json.loads((baseline/'record.json').read_text())
  assert sha(baseline/'record.json')==row['source_record_sha256']
  reference=role.REFERENCE/'-'.join((case['climate'],role.TEXTURES[case['soil']],case['design'],case['surface'],case['traffic'],'legacy','legacy'))
  ref=json.loads((reference/'record.json').read_text());assert sha(reference/'record.json')==row['reference_record_sha256']
  for section,subdir in [('inputs','runs'),('outputs','output')]:
   assert all(sha(folder/subdir/name)==value for name,value in row[section].items())
  assert set(row['inputs'])==set(original['inputs'])
  assert [key for key in original['inputs'] if original['inputs'][key]!=row['inputs'][key]]==['p1.sol']
  assert sha(folder/'runs/p1.sol')==sha(reference/'runs/p1.sol')==ref['inputs']['p1.sol']
  assert row['binary_sha256']==role.SHA
  if row['status']=='completed':
   audit=c.audit(folder,case,row);assert audit==row['audit'];physical+=audit['physical_pass']
  unique.add(tuple(sorted(row['inputs'].items())))
  group=groups.setdefault(row['group'],dict(cases=0,within=0,physical=0));group['cases']+=1;group['within']+=bool(row.get('within'));group['physical']+=row['physical_pass']
 receipt=dict(cases=len(rows),unique_consumed_input_sets=len(unique),physical_pass=physical,groups=groups,all_recorded_bytes_verified=True,sole_input_change='p1.sol exact legacy reference',completed_native_audits_recomputed=True,results_sha256=sha(ROOT/'results.json'),declaration_sha256=sha(ROOT/'declaration.json'),verifier_sha256=sha(Path(__file__)))
 (HERE/'legacy-soil-control-r3-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
