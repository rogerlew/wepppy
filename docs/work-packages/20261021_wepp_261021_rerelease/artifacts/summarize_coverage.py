from pathlib import Path
import json,hashlib,re
r=Path('/workdir/wepp-261021-rerelease-20261021');reports=Path('/workdir/wepppy/.pytest_cache/wepp-261021-rerelease')
ledger=json.loads((r/'segmented-coverage.json').read_text())
nodes=[x.strip() for x in (r/'full-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',x)]
expected=set(nodes);prefix=set(ledger['completed_module_nodes']);good=set(prefix);failed=set();by_report={};observed={}
for p in sorted(reports.glob('*.report.jsonl')):
 outcomes={};errors=set()
 for line in p.read_text().splitlines():
  x=json.loads(line)
  if x.get('$report_type')!='TestReport':continue
  n=x['nodeid'];status=x['outcome'];phase=x['when']
  if status=='failed':errors.add(n);failed.add(n)
  if phase=='call' and status=='passed' or status=='skipped':outcomes[n]=status
 for n in errors:outcomes.pop(n,None)
 good.update(outcomes)
 observed.update(outcomes)
 by_report[p.name]={'passed':sum(v=='passed' for v in outcomes.values()),'skipped':sum(v=='skipped' for v in outcomes.values()),'failures':sorted(errors),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
missing=sorted(expected-good)
s={'collected_nodes':len(expected),'collection_import_skips':1,'unique_passes':2404+sum(v=='passed' for n,v in observed.items() if n not in prefix),'unique_skips_including_collection':48+sum(v=='skipped' for n,v in observed.items() if n not in prefix),'completed_prefix_nodes':len(prefix),'covered_unique_nodes':len(good&expected),'missing_nodes':missing,'failure_nodes_observed':sorted(failed),'failures_with_later_pass':sorted(failed&good),'reports':by_report,'all_collected_nodes_covered':not missing,'full_collection_sha256':hashlib.sha256((r/'full-collection.log').read_bytes()).hexdigest(),'covered_node_set_sha256':hashlib.sha256(('\n'.join(sorted(good&expected))+'\n').encode()).hexdigest(),'scope':'Segmented execution; original full command intentionally interrupted in slow soil module. Failure history retained even where isolated rerun passes.'}
(r/'coverage-summary.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({k:v for k,v in s.items() if k not in ['missing_nodes','reports']},indent=2));print('missing',len(missing),'first',missing[:2])
