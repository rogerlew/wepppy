from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,re
root=Path('/tmp/wepp-261026-segmented');cwd=Path('/workdir/wepppy')
report=cwd/'.pytest_cache/wepp-261026-full.report.jsonl'
nodes=[s.strip() for s in Path('/tmp/wepp-261026-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',s)]
assert len(nodes)==11940,len(nodes)
phases={}
for line in report.read_text().splitlines():
 x=json.loads(line)
 if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
complete={n for n,p in phases.items() if p.get('teardown')=='passed' and (p.get('call') in ('passed','skipped') or p.get('setup')=='skipped')}
remaining=set(nodes)-complete
soil='tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py'
soil_nodes=[n for n in nodes if n in remaining and n.split('::')[0]==soil]
rest=sorted({n.split('::')[0] for n in remaining if n.split('::')[0]!=soil})
lanes=[dict(name='soil-'+str(i),args=soil_nodes[i::4]) for i in range(4)]+[dict(name='remainder',args=rest)]
ledger=dict(collected=len(nodes),completed_prefix=sorted(complete),remaining=len(remaining),lanes=lanes,scope='Complete inventory; canonical full run interrupted in slow Rosetta soil matrix; no test exclusions')
(root/'coverage-plan.json').write_text(json.dumps(ledger,indent=2)+'\n')
def run(lane):
 command=['wctl','run-pytest',*lane['args'],'--maxfail=1','--report-log='+str(cwd/'.pytest_cache/wepp-261026-segmented'/(lane['name']+'.jsonl'))]
 with (root/(lane['name']+'.log')).open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
 result=dict(name=lane['name'],exit_code=r.returncode,command=command)
 (root/(lane['name']+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
 return result
with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(run,lanes))
(root/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print([(r['name'],r['exit_code']) for r in results])
