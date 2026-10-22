from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,re
root=Path('/workdir/wepp-261021-rerelease-20261021');cwd=Path('/workdir/wepppy');soil='tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py'
nodes=[x.strip() for x in (root/'full-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',x)]
assert len(nodes)==11173,len(nodes)
completed=[]
for line in (root/'wepppy-full-suite.log').read_text().splitlines():
 m=re.match(r'^(tests/\S+\.py) ',line)
 if m:
  if m[1]==soil:break
  if m[1] not in completed:completed.append(m[1])
soil_nodes=[n for n in nodes if n.split('::')[0]==soil];assert len(soil_nodes)==230,len(soil_nodes)
remaining=sorted({n.split('::')[0] for n in nodes}-set(completed)-{soil})
covered=[n for n in nodes if n.split('::')[0] in completed]
lanes=[{'name':'soil-'+str(i),'nodes':soil_nodes[i::4]} for i in range(4)]+[{'name':'remainder','modules':remaining}]
ledger={'full_collected_count':len(nodes),'completed_modules':completed,'completed_module_nodes':covered,'interrupted_summary':'2434 passed,48 skipped,73warnings; partial soil module is deliberately rerun','lanes':lanes,'scope':'segmented completion; not an uninterrupted single-process suite'}
(root/'segmented-coverage.json').write_text(json.dumps(ledger,indent=2)+'\n')
def run(lane):
 args=['wctl','run-pytest',*lane.get('nodes',lane.get('modules',[])),'--maxfail=1','--report-log='+str(cwd/'.pytest_cache/wepp-261021-rerelease'/(lane['name']+'.report.jsonl'))]
 with (root/(lane['name']+'.log')).open('w') as log:result=subprocess.run(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
 return {'lane':lane['name'],'returncode':result.returncode,'command':args}
with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(run,lanes))
(root/'segmented-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items() if k!='command'} for r in results]))
raise SystemExit(0 if all(x['returncode']==0 for x in results) else 1)
