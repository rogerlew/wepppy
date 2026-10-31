"""Hash readback of frozen ledger, unchanged audits and publication derivative."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parent

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def read(name):
    return json.loads((ROOT/name).read_text())

def check(item):
    assert sha(item['path'])==item['sha256'],item['path']

d=read('declaration.json');index=read('results.json');assert len(index)==116
assert sha(ROOT/'ledger.py')==d['script_sha256']
for path,digest in d['dependencies'].items():assert sha(path)==digest,path
counts=dict(case_receipts=0,source_records=0,parsed_parquets=0,derived_parquets=0,particle_audits=0)
for item in index:
    assert sha(item['receipt'])==item['sha256'];counts['case_receipts']+=1
    rec=json.loads(Path(item['receipt']).read_text())
    for lane,r in rec['lanes'].items():
        check(r['record']);counts['source_records']+=1
        for p in r['parsed'].values():check(p);counts['parsed_parquets']+=1
        p=Path(item['receipt']).parent/lane/'particle-audit-v2.json'
        assert sha(p)==r['particle_audit_sha256'];counts['particle_audits']+=1
    for p in rec['outputs'].values():check(p);counts['derived_parquets']+=1
assert counts==dict(case_receipts=116,source_records=232,parsed_parquets=928,derived_parquets=696,particle_audits=232)
figure=read('figure-data.json');draft=read('figure-layout-draft/figure-data.json')
assert figure['points']==draft['points'] and len(figure['points'])==43
assert sha(ROOT/'plot_boundaries.py')==figure['script_sha256']
assert sha(ROOT/'case-summary.json')==figure['case_summary_sha256']
for ext,digest in figure['files'].items():assert sha(ROOT/f'small-reference-paired-boundaries.{ext}')==digest
explore=read('exploratory-hydrology.json')
assert explore['script_sha256']==sha(ROOT/'explore_hydrology.py')
assert explore['frozen_summary_sha256']==sha(ROOT/'summary.json')
assert explore['case_summary_sha256']==sha(ROOT/'case-summary.json')
assert len(explore['events_detail'])==explore['events']==115
names=['declaration.json','analysis-declaration.json','ledger.py','summarize.py','schema.json','results.json','preflight.json','summary.json','case-summary.json','interpretation-metadata.json','explore_hydrology.py','exploratory-hydrology.json','top-discrepancy-events.json','positive-ranked-discrepancy-events.json','exploratory-negative-discrepancy-events.json','plot_boundaries.py','figure-data.json','small-reference-paired-boundaries.png','small-reference-paired-boundaries.pdf','small-reference-paired-boundaries.svg']
result=dict(passed=True,scope='Artifact hash readback only; numerical independent acceptance is separately retained.',script_sha256=sha(__file__),dependencies_rehashed=len(d['dependencies']),counts=counts,figure_all43_points_unchanged=True,strict_audit_criteria_unchanged=True,files={name:sha(ROOT/name) for name in names})
(ROOT/'final-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
