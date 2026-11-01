"""Frozen observation-only build and three complete parity-preserving histories."""
import argparse,json,os,runpy,shutil,subprocess,sys,time
from pathlib import Path
from read_flux_v4 import read,sha
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RAW=ROOT/'out/frozen-water-flux-20261101'
BASE=ROOT/'out/frozen-water-history-20261101/campaign-v1/build'
OLD=ROOT/'out/frozen-water-reset-20261101/targeted-v1'
OLDPUB=ROOT/'docs/work-packages/20261101_frozen_water_history_ownership/artifacts'
TARGETS={'zero-ks1':(3,20),'normal-ks1':(3,20),'high-ks1':(7,344)}
ENV={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran','PYTHONDONTWRITEBYTECODE':'1'}
def save(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def inv(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def verify(files):
 for p,h in files.items():
  if sha(Path(p))!=h:raise ValueError('Dependency drift: '+str(p))
def execute(cmd,cwd,stem,timeout,stdin=None):
 r=dict(command=list(map(str,cmd)),cwd=str(cwd),PATH=ENV['PATH'],FC=ENV['FC'],timeout_seconds=timeout,started=time.time())
 save(cwd/(stem+'-pre.json'),r)
 with (cwd/(stem+'.stdout')).open('xb') as out,(cwd/(stem+'.stderr')).open('xb') as err:
  stream=stdin.open('rb') if stdin else subprocess.DEVNULL
  try:
   proc=subprocess.run(r['command'],cwd=cwd,env=ENV,stdin=stream,stdout=out,stderr=err,timeout=timeout);r.update(status='completed',returncode=proc.returncode)
  except subprocess.TimeoutExpired:r.update(status='timeout',returncode=None)
  finally:
   if stdin:stream.close()
 r.update(elapsed_seconds=time.time()-r['started'],stdout_sha256=sha(cwd/(stem+'.stdout')),stderr_sha256=sha(cwd/(stem+'.stderr')))
 save(cwd/(stem+'-result.json'),r);return r

def freeze():
 prior=json.loads((BASE.parent/'build-receipt.json').read_text())['after'];base={n:v['sha256'] for n,v in prior.items()}
 if inv(BASE)!=base:raise ValueError('Base build inventory drift')
 files={str(BASE/n):h for n,h in base.items()}
 for p in list(HERE.glob('*.py'))+[HERE/'ownership-contract.md',HERE/'declaration.md',OLDPUB/'run_history_campaign.py',OLDPUB/'read_history.py']+list((RAW/'prepared-v3').iterdir()):
  if p.is_file():files[str(p)]=sha(p)
 for p in [RAW/'prepare_observer_v3.py',RAW/'reader-controls-v5/receipt.json']:files[str(p)]=sha(p)
 inputs={};comparators={}
 for s in TARGETS:
  d=json.loads((OLD/s/'readback.json').read_text());inputs[s]=d['inputs'];comparators[s]={k:d[k] for k in ['output_hashes','trace_sha256','buffer_observation_sha256']}
  for n,h in d['inputs'].items():files[str(OLD/s/'runs'/n)]=h
  files[str(OLD/s/'readback.json')]=sha(OLD/s/'readback.json')
  files[str(OLD/s/'runs/buffer-observation.txt')]=d['buffer_observation_sha256']
  files[str(OLD/s/'runs/frwatc-history.txt')]=d['trace_sha256']
 tools=['/usr/bin/gfortran','/usr/bin/gcc','/usr/bin/as','/usr/bin/ld','/usr/bin/make','/usr/bin/ldd']
 for n in ['f951','collect2']:tools.append(str(Path(subprocess.check_output(['/usr/bin/gfortran','-print-prog-name='+n],env=ENV,text=True).strip()).resolve()))
 for p in tools:files[p]=sha(p)
 libraries=json.loads((BASE.parents[1]/'observer-runtime.json').read_text())['libraries'];files.update(libraries)
 verify(files)
 save(RAW/'freeze.json',dict(files=files,base_inventory=base,inputs=inputs,comparators=comparators,libraries=libraries,targets=TARGETS,invocations=3))

def run():
 f=json.loads((RAW/'freeze.json').read_text());approval=json.loads((RAW/'approval.json').read_text())
 if approval['status']!='approved' or approval['freeze_sha256']!=sha(RAW/'freeze.json'):raise ValueError('Exact approval missing')
 verify({**f['files'],**approval['reviews']})
 root=RAW/'campaign-v2';root.mkdir();build=root/'build';shutil.copytree(BASE,build,copy_function=shutil.copy2)
 for p in (RAW/'prepared-v3').glob('*.for'):shutil.copyfile(p,build/'src'/p.name)
 before=inv(build);r=execute(['/usr/bin/make','-j4','FC=/usr/bin/gfortran','LINKER=/usr/bin/gfortran','wepp'],build/'src','flux-build',300)
 save(root/'build-receipt.json',dict(result=r,before=before,after=inv(build)))
 if r['returncode']!=0:raise RuntimeError('Build failed')
 binary=build/'src/wepp';ldd=subprocess.check_output(['/usr/bin/ldd',str(binary)],text=True,env=ENV);(root/'ldd.txt').write_text(ldd)
 libs={}
 for line in ldd.splitlines():
  for token in line.split():
   if token.startswith('/'):
    p=Path(token).resolve();libs[str(p)]=sha(p);break
 if libs!=f['libraries']:raise ValueError('New executable runtime drift')
 save(root/'runtime.json',dict(binary_sha256=sha(binary),libraries=libs))
 sys.path.insert(0,str(OLDPUB));validate=runpy.run_path(str(OLDPUB/'run_history_campaign.py'))['output_check']
 results=[]
 for s,(year,day) in TARGETS.items():
  dest=root/s;runs=dest/'runs';runs.mkdir(parents=True);(dest/'output').mkdir()
  for n,h in f['inputs'][s].items():shutil.copyfile(OLD/s/'runs'/n,runs/n)
  verify({str(runs/n):h for n,h in f['inputs'][s].items()})
  save(dest/'inputs.json',f['inputs'][s]);r=execute([binary],runs,'execution',900,runs/'p1.run');r.update(scenario=s,binary_sha256=sha(binary))
  if r['returncode']!=0 or 'WEPP COMPLETED' not in (runs/'execution.stdout').read_text():save(dest/'readback.json',{**r,'passed':False});raise RuntimeError('Native execution failed')
  try:
   r.update(validate(dest));c=f['comparators'][s]
   if r['output_hashes']!=c['output_hashes'] or sha(runs/'frwatc-history.txt')!=c['trace_sha256']:raise ValueError('Output/trace parity failed')
   observation=read(runs/'buffer-observation.txt',year,day,OLD/s/'runs/buffer-observation.txt')
   save(dest/'observations.json',observation)
   verify({str(runs/n):h for n,h in f['inputs'][s].items()})
   r.update(passed=True,trace_sha256=c['trace_sha256'],observations_sha256=sha(dest/'observations.json'),hourly_groups=observation['hourly_groups'],daily_groups=observation['daily_groups'],outside_allowance=observation['outside_allowance'],flagged_hours=observation['flagged_hours'],legacy_filtered_sha256=observation['legacy_filtered_sha256'])
  except (ValueError,OSError,KeyError) as error:
   save(dest/'readback.json',{**r,'passed':False,'error':str(error)})
   raise
  save(dest/'readback.json',r);results.append(r);print(s,r['passed'],r['outside_allowance'],flush=True)
 verify(f['files'])
 save(root/'receipt.json',dict(passed=True,cases=results,freeze_sha256=sha(RAW/'freeze.json'),dependencies_unchanged=True))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run']);a=ap.parse_args();freeze() if a.action=='freeze' else run()
