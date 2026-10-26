from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,re
root=Path('/tmp/roads-wbt-segmented');cwd=Path('/workdir/wepppy');cache=cwd/'.pytest_cache/roads-wbt-segmented'
nodes=[s.strip() for s in Path('/tmp/roads-wbt-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',s)]
modules=set(next(x['args'] for x in json.loads((root/'plan.json').read_text())['lanes'] if x['name']=='rest-2'))
phases={}
for line in (cache/'rest-2.jsonl').read_text().splitlines():
 x=json.loads(line)
 if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
complete={n for n,p in phases.items() if p.get('teardown')=='passed' and (p.get('call') in ('passed','skipped') or p.get('setup')=='skipped')}
remaining=[n for n in nodes if n.split('::')[0] in modules and n not in complete]
lanes=[dict(name=f'late-{i}',args=remaining[i::4]) for i in range(4)]
(root/'late-plan.json').write_text(json.dumps(dict(reason='Split slow remaining rest-2 segment; preserve every collected node',lanes=lanes),indent=2)+'\n')
def run(lane):
 command=['wctl','run-pytest',*lane['args'],'--maxfail=1','--report-log='+str(cache/(lane['name']+'.jsonl'))]
 assert sum(map(len,command))<120000
 with (root/(lane['name']+'.log')).open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
 result=dict(name=lane['name'],exit_code=r.returncode,command=command)
 (root/(lane['name']+'-result.json')).write_text(json.dumps(result,indent=2)+'\n');return result
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,lanes))
(root/'late-results.json').write_text(json.dumps(results,indent=2)+'\n');print([(r['name'],r['exit_code']) for r in results])
