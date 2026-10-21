from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util,shutil,subprocess,json,hashlib,time
ROOT=Path('/workdir/watershed-physical-water-repair-20261021')
AUDIT=Path('/workdir/watershed-physical-water-audit-20261021')
NATIVE=Path('/workdir/wepp-forest-release-20261009')
BIN=ROOT/'mc-guard-candidate/src'
spec=importlib.util.spec_from_file_location('portable',NATIVE/'tools/physical_water_case.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
SHARED={'wepp_ui.txt','pmetpara.txt','snow.txt','gwcoeff.txt','chan.inp','chntyp.txt','tc.txt'}
def run(task):
 group,name=task;case=ROOT/'mc-guard-replays'/group/name
 if group=='portable':
  mode,layout=name.split('-',1);mod.prepare(case,layout,mode,2)
 elif group=='calendar':
  mod.prepare(case,'upper60','hourly',400)
 else:
  source=AUDIT/group/name/'runs';(case/'runs').mkdir(parents=True);(case/'output').mkdir()
  for p in source.iterdir():
   if p.suffix in {'.run','.man','.sol','.cli','.slp','.str','.chn','.imp'} or p.name in SHARED:shutil.copy2(p,case/'runs'/p.name)
 inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (case/'runs').iterdir()}
 records=[]
 cards=sorted(p.name for p in (case/'runs').glob('p*.run') if p.name!='pw0.run')+['pw0.run']
 for card in cards:
  binary=BIN/('wepp' if card=='pw0.run' else 'wepp_hill');start=time.monotonic()
  with (case/'runs'/card).open('rb') as inp,(case/(card+'.stdout')).open('wb') as out,(case/(card+'.stderr')).open('wb') as err:
   proc=subprocess.run([str(binary)],cwd=case/'runs',stdin=inp,stdout=out,stderr=err,timeout=1800)
  success=proc.returncode==0 and 'SIMULATION SUCCESSFULLY' in (case/(card+'.stdout')).read_text(errors='replace')
  records.append({'card':card,'success':success,'returncode':proc.returncode,'seconds':time.monotonic()-start})
  if not success:break
 data={'group':group,'case':name,'records':records,'input_manifest':inputs,'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (case/'output').iterdir() if p.is_file()}}
 (case/'execution.json').write_text(json.dumps(data,indent=2)+'\n');print(group,name,[(r['card'],r['success'],round(r['seconds'],1)) for r in records],flush=True);return data
if __name__=='__main__':
 tasks=[('portable',f'{mode}-{layout}') for mode in ['daily','hourly'] for layout in ['single','equal','upper60','lower60','three']]
 tasks += [('release-matrix',p.name) for p in sorted((AUDIT/'release-matrix').iterdir()) if (p/'runs').is_dir()]
 tasks += [('networks',p.name) for p in sorted((AUDIT/'networks').iterdir()) if (p/'runs').is_dir()]
 tasks += [('calendar','hourly-upper60-400')]
 with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(run,tasks))
 (ROOT/'mc-guard-replay-results.json').write_text(json.dumps(results,indent=2)+'\n')
