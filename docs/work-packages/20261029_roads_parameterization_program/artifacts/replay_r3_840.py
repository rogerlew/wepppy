"""Unchanged 840-input diagnostic replay; no fitting or withheld materials."""
import sys,json,subprocess,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,'/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts')
import continuation as c
from wepppy.wepp.soils.utils import WeppSoilUtil
BASE=Path('/workdir/wepppy/out/roads-native-funding-20261031')
SOURCE=Path('/workdir/wepppy/out/roads-parameterization-program-20261030/development-matrix-v1/matrix-v1')
ROOT=BASE/'r3-matrix840'
BINARY=BASE/'r3-candidate/wepp'
SHA=c.b.digest(BINARY)

def execute(source):
 oldfile=source/('record.json' if (source/'record.json').exists() else 'failure.json')
 old=json.loads(oldfile.read_text());case=old['case'];folder=ROOT/'matrix-v1'/source.name
 runs=folder/'runs';out=folder/'output';runs.mkdir(parents=True,exist_ok=False);out.mkdir()
 for name,sha in old['inputs'].items():
  if c.b.digest(source/'runs'/name)!=sha:raise ValueError('Frozen input drift')
  shutil.copy2(source/'runs'/name,runs/name)
 shutil.copy2(source/'runs/reference.sol',runs/'reference.sol')
 if c.b.digest(BINARY)!=SHA:raise ValueError('Candidate binary drift')
 with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
  proc=subprocess.run([str(BINARY)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
 record=dict(case=case,inputs=old['inputs'],outputs={p.name:c.b.digest(p) for p in out.iterdir()},returncode=proc.returncode,binary_sha256=SHA,source_record_sha256=c.b.digest(oldfile),physical_pass=False,status='native_failure')
 if proc.returncode==0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs/'stdout').read_text():
  _,width,length=c.b.slope_text(case['design'])
  record.update(status='completed',width_m=width,profile_length_m=length,soil_readback=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes'],metrics=c.b.parse_loss(out/'H1.loss.dat',width))
  record['audit']=c.audit(folder,case,record)
  record['physical_pass']=record['audit']['physical_pass']
 else:record['tail']=(runs/'stdout').read_text()[-1600:]+(runs/'stderr').read_text()[-1200:]
 (folder/'record.json').write_text(json.dumps(record,indent=2)+'\n')
 return record

def main():
 tasks=sorted(p for p in SOURCE.iterdir() if p.is_dir());assert len(tasks)==840
 ROOT.mkdir(exist_ok=False)
 (ROOT/'declaration.json').write_text(json.dumps(dict(binary_sha256=SHA,script_sha256=c.b.digest(__file__),source=str(SOURCE),cases=[p.name for p in tasks],purpose='Scientific diagnostic, unchanged physical audits; no acceptance claim or retuning'),indent=2)+'\n')
 results=[]
 with ProcessPoolExecutor(max_workers=8) as pool:
  for record in pool.map(execute,tasks):
   results.append(record)
   if len(results)%20==0:print(len(results),sum(r['physical_pass'] for r in results),flush=True)
   (ROOT/'partial-results.json').write_text(json.dumps(results)+'\n')
 (ROOT/'results.json').write_text(json.dumps(results)+'\n')
 summary=dict(cases=len(results),completed=sum(r['status']=='completed' for r in results),physical_pass=sum(r['physical_pass'] for r in results),failures=[r['case'] for r in results if not r['physical_pass']])
 (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
