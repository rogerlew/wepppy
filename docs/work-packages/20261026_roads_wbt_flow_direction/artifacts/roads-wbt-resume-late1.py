from pathlib import Path
import json,subprocess
root=Path('/tmp/roads-wbt-segmented');cwd=Path('/workdir/wepppy');cache=cwd/'.pytest_cache/roads-wbt-segmented'
args=next(x['args'] for x in json.loads((root/'late-plan.json').read_text())['lanes'] if x['name']=='late-1')
phases={}
for line in (cache/'late-1.jsonl').read_text().splitlines():
 x=json.loads(line)
 if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
complete={n for n,p in phases.items() if p.get('teardown')=='passed' and (p.get('call') in ('passed','skipped') or p.get('setup')=='skipped')}
remaining=[n for n in args if n not in complete and not n.startswith('tests/nodb/mods/test_swat_interchange.py::')]
command=['wctl','run-pytest',*remaining,'--maxfail=1','--report-log='+str(cache/'late-1-resume.jsonl')]
with (root/'late-1-resume.log').open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
(root/'late-1-resume-result.json').write_text(json.dumps(dict(command=command,exit_code=r.returncode),indent=2)+'\n')
print(r.returncode)
