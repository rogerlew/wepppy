from pathlib import Path
import json,subprocess,re,shlex
root=Path('/tmp/roads-wbt-segmented');cwd=Path('/workdir/wepppy');cache=cwd/'.pytest_cache/roads-wbt-segmented'
modules=set(next(x['args'] for x in json.loads((root/'plan.json').read_text())['lanes'] if x['name']=='rest-0'))
nodes=[s.strip() for s in Path('/tmp/roads-wbt-collection.log').read_text().splitlines() if re.match(r'^tests/\S+\.py::',s)]
phases={}
for line in (cache/'rest-0.jsonl').read_text().splitlines():
 x=json.loads(line)
 if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
complete={n for n,p in phases.items() if p.get('teardown')=='passed' and (p.get('call') in ('passed','skipped') or p.get('setup')=='skipped')}
remaining=sorted({n.split('::')[0] for n in nodes if n.split('::')[0] in modules and n not in complete})
pytest=['/opt/venv/bin/pytest',*remaining,'--maxfail=1','--report-log='+str(cache/'rest-0-resume.jsonl')]
command=['wctl','docker','compose','exec','-e','PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers','weppcloud','bash','-lc','cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy '+shlex.join(pytest)]
with (root/'rest-0-resume.log').open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
(root/'rest-0-resume-result.json').write_text(json.dumps(dict(command=command,exit_code=r.returncode),indent=2)+'\n')
print(r.returncode)
