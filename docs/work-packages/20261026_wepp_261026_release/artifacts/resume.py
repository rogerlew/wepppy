from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,re
root=Path('/tmp/wepp-261026-segmented');cwd=Path('/workdir/wepppy');cache=cwd/'.pytest_cache/wepp-261026-segmented'
nodes=[s.strip() for s in Path('/tmp/wepp-261026-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',s)]
complete=set()
for report in [cwd/'.pytest_cache/wepp-261026-full.report.jsonl',*cache.glob('*.jsonl')]:
 phases={}
 for line in report.read_text().splitlines():
  x=json.loads(line)
  if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
 complete|={n for n,p in phases.items() if p.get('teardown')=='passed' and (p.get('call') in ('passed','skipped') or p.get('setup')=='skipped')}
modules=sorted({n.split('::')[0] for n in set(nodes)-complete})
# Run the corrected capability module whole to validate all representations.
assert 'tests/nodb/test_project_config_builder_snapshot.py' in modules
lanes=[dict(name='tail-'+str(i),args=modules[i::4]) for i in range(4)]
(root/'tail-plan.json').write_text(json.dumps(dict(covered=len(complete),remaining=len(set(nodes)-complete),lanes=lanes),indent=2)+'\n')
def run(lane):
 command=['wctl','run-pytest',*lane['args'],'--maxfail=1','--report-log='+str(cache/(lane['name']+'.jsonl'))]
 with (root/(lane['name']+'.log')).open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
 result=dict(name=lane['name'],exit_code=r.returncode,command=command)
 (root/(lane['name']+'-result.json')).write_text(json.dumps(result,indent=2)+'\n');return result
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,lanes))
(root/'tail-results.json').write_text(json.dumps(results,indent=2)+'\n');print([(r['name'],r['exit_code']) for r in results])
