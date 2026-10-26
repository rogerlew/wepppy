from pathlib import Path
import subprocess,json,sys
root=Path('/tmp/wepp-261026-segmented');cwd=Path('/workdir/wepppy');cache=cwd/'.pytest_cache/wepp-261026-segmented'
old,new=sys.argv[1:3];args=json.loads((root/(old+'-result.json')).read_text())['command'][2:-2]
complete_modules=[]
report=cache/(old+'.jsonl');phases={}
for line in report.read_text().splitlines():
 x=json.loads(line)
 if x.get('$report_type')=='TestReport':phases.setdefault(x['nodeid'],{})[x['when']]=x['outcome']
failed={n.split('::')[0] for n,p in phases.items() if 'failed' in p.values()}
# Keep the failed module and every subsequent original module. Successfully
# completed earlier modules remain accounted by their original report.
start=min(args.index(m) for m in failed)
remaining=args[start:]
command=['wctl','run-pytest',*remaining,'--maxfail=1','--report-log='+str(cache/(new+'.jsonl'))]
with (root/(new+'.log')).open('w') as out:r=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT)
(root/(new+'-result.json')).write_text(json.dumps(dict(name=new,exit_code=r.returncode,command=command),indent=2)+'\n')
print(new,r.returncode)
