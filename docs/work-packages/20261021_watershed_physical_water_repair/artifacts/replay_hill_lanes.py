from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil,subprocess,json,hashlib,time
ROOT=Path('/workdir/watershed-physical-water-repair-20261021')
AUDIT=Path('/workdir/watershed-physical-water-audit-20261021')

def run(task):
 lane,name,initial=task
 source=AUDIT/'release-matrix'/name
 case=ROOT/lane/'cases'/(name+('-gw100' if initial else ''))
 shutil.copytree(source/'runs',case/'runs',ignore=shutil.ignore_patterns('*.out'))
 (case/'output').mkdir()
 if initial:
  p=case/'runs/gwcoeff.txt';lines=p.read_text().splitlines();lines[0]='100.0 Initial groundwater storage (mm)';p.write_text('\n'.join(lines)+'\n')
 binary=ROOT/lane/'src/wepp_hill';start=time.monotonic()
 with (case/'runs/p1.run').open('rb') as inp,(case/'stdout').open('wb') as out,(case/'stderr').open('wb') as err:
  result=subprocess.run([str(binary)],cwd=case/'runs',stdin=inp,stdout=out,stderr=err,timeout=1800)
 success=result.returncode==0 and 'SIMULATION SUCCESSFULLY' in (case/'stdout').read_text(errors='replace')
 data={'lane':lane,'case':case.name,'returncode':result.returncode,'success':success,'seconds':time.monotonic()-start,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'wat_baseline_identical':(case/'output/H1.wat.dat').read_bytes()==(source/'output/H1.wat.dat').read_bytes() if (case/'output/H1.wat.dat').exists() else False}
 if success:
  lines=(case/'output/H1.wat.dat').read_text().splitlines();data['final_wat_row']=lines[-1]
 (case/'execution.json').write_text(json.dumps(data,indent=2)+'\n');print(data,flush=True);return data
if __name__=='__main__':
 tasks=[('wpa04','daily-'+name,initial) for name in ['single','upper60','three'] for initial in [False,True]]+[('wpa03','hourly-'+name,False) for name in ['single','upper60','three']]+[('wpa03','daily-upper60',False)]
 with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(run,tasks))
 (ROOT/'hill-lane-results.json').write_text(json.dumps(results,indent=2)+'\n')
