from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil,subprocess,json,hashlib,time
ROOT=Path('/workdir/watershed-physical-water-repair-20261021')
AUDIT=Path('/workdir/watershed-physical-water-audit-20261021')
def run(task):
 lane,name,observed=task
 source=AUDIT/'release-matrix'/name
 case=ROOT/lane/'cases'/('on' if observed else 'off')/name
 shutil.copytree(source/'runs',case/'runs',ignore=shutil.ignore_patterns('*.out'))
 (case/'output').mkdir()
 if observed:(case/'runs/water_audit.on').touch()
 binary=ROOT/lane/'src/wepp'
 # Full watershed-capacity executable supports hill execution too. Both
 # phases intentionally use identical freshly built source/executable bytes.
 records=[]
 for card in ['p1.run','pw0.run']:
  start=time.monotonic()
  with (case/'runs'/card).open('rb') as inp,(case/(card+'.stdout')).open('wb') as out,(case/(card+'.stderr')).open('wb') as err:
   result=subprocess.run([str(binary)],cwd=case/'runs',stdin=inp,stdout=out,stderr=err,timeout=1800)
  success=result.returncode==0 and 'SIMULATION SUCCESSFULLY' in (case/(card+'.stdout')).read_text(errors='replace')
  records.append({'card':card,'returncode':result.returncode,'success':success,'seconds':time.monotonic()-start})
  if not success:break
 data={'lane':lane,'case':name,'observed':observed,'records':records,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}
 (case/'execution.json').write_text(json.dumps(data,indent=2)+'\n');print(data,flush=True);return data
if __name__=='__main__':
 tasks=[(lane,name,observed) for lane in ['wpa01-observed','wpa02-observed','combined-observed'] for name in ['daily-upper60','hourly-upper60'] for observed in [False,True]]
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,tasks))
 (ROOT/'routing-lane-results.json').write_text(json.dumps(results,indent=2)+'\n')
