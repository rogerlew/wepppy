from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,re
root=Path('/tmp/roads-wbt-segmented');root.mkdir(exist_ok=True)
cwd=Path('/workdir/wepppy');cache=cwd/'.pytest_cache/roads-wbt-segmented';cache.mkdir(exist_ok=True)
nodes=[s.strip() for s in Path('/tmp/roads-wbt-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',s)]
assert len(nodes)==len(set(nodes))==11947
phases={}
for line in (cwd/'.pytest_cache/roads-wbt-full.jsonl').read_text().splitlines():
 x=json.loads(line)
 if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
complete={n for n,p in phases.items() if p.get('teardown')=='passed' and (p.get('call') in ('passed','skipped') or p.get('setup')=='skipped')}
remaining=set(nodes)-complete
expensive=['tests/disturbed/test_disturbed_matrix.py','tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py']
lanes=[]
for label,module in zip(['disturbed','soil'],expensive):
 selected=[n for n in nodes if n in remaining and n.split('::')[0]==module]
 lanes += [dict(name=f'{label}-{i}',args=selected[i::4]) for i in range(4)]
rest=sorted({n.split('::')[0] for n in remaining if n.split('::')[0] not in expensive})
lanes += [dict(name=f'rest-{i}',args=rest[i::4]) for i in range(4)]
(root/'plan.json').write_text(json.dumps(dict(collected=len(nodes),complete_prefix=sorted(complete),lanes=lanes),indent=2)+'\n')
def run(lane):
 command=['wctl','run-pytest',*lane['args'],'--maxfail=1','--report-log='+str(cache/(lane['name']+'.jsonl'))]
 with (root/(lane['name']+'.log')).open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
 result=dict(name=lane['name'],exit_code=r.returncode,command=command)
 (root/(lane['name']+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
 return result
with ThreadPoolExecutor(max_workers=12) as pool:results=list(pool.map(run,lanes))
(root/'results.json').write_text(json.dumps(results,indent=2)+'\n');print([(r['name'],r['exit_code']) for r in results])
