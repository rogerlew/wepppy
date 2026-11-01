"""Finite retention/configuration campaign; prepare and comparator phases."""
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,time
from pathlib import Path
from select_window import select_events
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
RAW=REPO/'out/retention-frost-consumers-20261101'
PRIOR=REPO/'out/retention-volume-prototype-20261101'
FLUX=REPO/'out/frozen-water-flux-20261101/campaign-v2'
PANEL=['84543623','84543461','85179901']
CELLS=[(k,'baseline',1) for k in PANEL]+[(k,r,s) for k in PANEL for r in ['baseline','candidate'] for s in [0,1] if (r,s)!=('baseline',1)]
ENV={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran','PYTHONDONTWRITEBYTECODE':'1'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,d):
 with Path(p).open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def name(cell):return f'{cell[0]}-{cell[1]}-ks{cell[2]}'
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def load_module(path,title):
 spec=importlib.util.spec_from_file_location(title,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
NATIVE_READER=REPO/'docs/work-packages/20261101_retention_volume_prototype/artifacts/read_native_v3.py'
FROST_READER=REPO/'docs/work-packages/20261101_frozen_water_history_ownership/artifacts/read_history.py'
def check(files):
 for p,d in files.items():
  if sha(p)!=d:raise ValueError('Dependency drift '+str(p))
def prepare():
 root=RAW/'prepared-v3';root.mkdir()
 fixture=PRIOR/'fixtures-v1/receipt.json'
 if sha(fixture)!='7e7197e1f4455075e8d177560a8a313720c408b17b70e165f26769ecc3ae7f7d':raise ValueError('Fixture drift')
 source=json.loads(fixture.read_text());previous=json.loads((PRIOR/'campaign-v1/receipt.json').read_text())
 build=json.loads((FLUX/'build-receipt.json').read_text())['after']
 if len(build)!=986:raise ValueError('Base build count')
 bindings={str(FLUX/'build'/p):v for p,v in build.items()}
 check(bindings)
 binary=FLUX/'build/src/wepp'
 if sha(binary)!='17fbcf4540e7d7a29980b4eccb0851652689160960663ae8140ed3cddb377b72':raise ValueError('Binary drift')
 shutil.copytree(FLUX/'build',root/'base-build')
 for cell in CELLS:
  k,r,ks=cell;dest=root/name(cell);dest.mkdir()
  old=next(x for x in previous['cases'] if x['chkey']==k and x['lane']==r)
  for p,h in old['inputs'].items():
   src=PRIOR/'campaign-v1'/(k+'-'+r)/'runs'/p
   if sha(src)!=h:raise ValueError('Prior runtime drift')
   shutil.copy2(src,dest/p)
  lines=(dest/'p1.sol').read_text().splitlines(keepends=True)
  indexes=[i for i,line in enumerate(lines) if line.strip()=='3 0']
  if indexes!=[3]:raise ValueError('Header support')
  lines[3]='3 '+str(ks)+'\n';(dest/'p1.sol').write_text(''.join(lines))
  (dest/'buffer_observe.on').write_text('0 0\n');(dest/'frwatc_history.on').touch(exist_ok=False)
  expected={'buffer_observe.on','frwatc_history.on'}|({'p1.sol'} if ks else set())
  if {p for p,h in inventory(dest).items() if p not in old['inputs'] or h!=old['inputs'][p]}!=expected:raise ValueError('Unexpected input change')
 runtime=json.loads((FLUX/'runtime.json').read_text())
 bindings.update({str(p):sha(p) for p in [Path(__file__),HERE/'select_window.py',NATIVE_READER,FROST_READER,fixture,FLUX/'build-receipt.json',FLUX/'runtime.json']})
 bindings.update(runtime['libraries'])
 if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'):raise ValueError('Loader override')
 ldd=subprocess.check_output(['/usr/bin/ldd',str(root/'base-build/src/wepp')],text=True,env=ENV)
 libraries={str(Path(p).resolve()):sha(p) for p in re.findall(r'(/[^\s()]+)',ldd)}
 if libraries!=runtime['libraries']:raise ValueError('Runtime mismatch')
 save(root/'declaration.json',dict(cells=CELLS,inputs={name(c):inventory(root/name(c)) for c in CELLS},dependencies=bindings,base_inventory=inventory(root/'base-build'),libraries=libraries,fixture_receipt_sha256=sha(fixture),native_processes=24,comparator_processes=12,observer_processes=12))
 print('Prepared twelve isolated cells; no model invocation')
def frost_read(path):
 mod=load_module(FROST_READER,'frost_reader')
 return select_events(mod.events(path))
def execute(binary,runs,root):
 record=dict(command=[str(binary)],cwd=str(runs),PATH=ENV['PATH'],FC=ENV['FC'],timeout_seconds=900,started=time.time())
 save(root/'process-pre.json',record)
 with (runs/'p1.run').open('rb') as stdin,(runs/'stdout').open('xb') as out,(runs/'stderr').open('xb') as err:
  try:
   p=subprocess.run(record['command'],cwd=runs,env=ENV,stdin=stdin,stdout=out,stderr=err,timeout=900)
   record.update(returncode=p.returncode,status='completed')
  except subprocess.TimeoutExpired:record.update(returncode=None,status='timeout')
 record.update(seconds=time.time()-record['started'],stdout_sha256=sha(runs/'stdout'),stderr_sha256=sha(runs/'stderr'),completion='WEPP COMPLETED' in (runs/'stdout').read_text())
 save(root/'process-result.json',record);return record

def comparators():
 prep=RAW/'prepared-v3';d=json.loads((prep/'declaration.json').read_text());approval=json.loads((RAW/'comparator-approval.json').read_text())
 if approval['declaration_sha256']!=sha(prep/'declaration.json'):raise ValueError('Approval binding')
 check({**d['dependencies'],**approval['reviews']})
 if inventory(prep/'base-build')!=d['base_inventory']:raise ValueError('Copied build drift')
 root=RAW/'comparators-v1';root.mkdir();binary=prep/'base-build/src/wepp'
 if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'):raise ValueError('Execution loader override')
 ldd=subprocess.check_output(['/usr/bin/ldd',str(binary)],text=True,env=ENV)
 libraries={str(Path(p).resolve()):sha(p) for p in re.findall(r'(/[^\s()]+)',ldd)}
 if libraries!=d['libraries']:raise ValueError('Execution runtime drift')
 save(root/'runtime.json',dict(libraries=libraries,binary_sha256=sha(binary)))
 source=json.loads((PRIOR/'fixtures-v1/receipt.json').read_text());reader=load_module(NATIVE_READER,'native_reader')
 results=[];windows={}
 for cell in CELLS:
  k,r,ks=cell;dest=root/name(cell);runs=dest/'runs';runs.mkdir(parents=True);(dest/'output').mkdir()
  for p in (prep/name(cell)).iterdir():shutil.copy2(p,runs/p.name)
  check({str(runs/p):h for p,h in d['inputs'][name(cell)].items()})
  save(dest/'pre-execution.json',dict(cell=cell,inputs=d['inputs'][name(cell)],binary_sha256=sha(binary),declaration_sha256=sha(prep/'declaration.json')))
  result=execute(binary,runs,dest);result['cell']=cell
  try:
   if result['returncode']!=0 or not result['completion']:raise ValueError('Native process incomplete')
   fixture=next(x for x in source['cases'] if x['id']=='source-'+k)[r]
   result.update(reader.read(dest,fixture));result['frost']=frost_read(runs/'frwatc-history.txt')
   result['frost_sha256']=sha(runs/'frwatc-history.txt')
   check({str(runs/p):h for p,h in d['inputs'][name(cell)].items()})
   if ks==0 and result['frost']['counts'].get('FROST_CALL',0):raise ValueError('Unexpected KS0 frost')
  except (ValueError,KeyError,OSError,OverflowError,ZeroDivisionError) as error:
   result.update(passed=False,error=str(error))
  save(dest/'receipt.json',result);results.append(result)
  if r=='baseline' and ks==1:
   windows[k]=dict(target=result.get('frost',{}).get('selected'),source_receipt_sha256=sha(dest/'receipt.json'),coverage=result.get('passed',False))
   if len(windows)==3:save(root/'selected-windows.json',dict(rule='first baselineKS1 OFE1 WB_PRE positivefrozen day>=2 after actualFROST_CALL',windows=windows))
  print(json.dumps(dict(cell=cell,passed=result['passed'],target=windows.get(k,{}).get('target'),error=result.get('error'))),flush=True)
 check(d['dependencies'])
 if inventory(prep/'base-build')!=d['base_inventory']:raise ValueError('Base changed')
 save(root/'receipt.json',dict(passed=all(x['passed'] for x in results),cases=results,windows=windows))
 if not all(x['passed'] for x in results):raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','comparators']);a=p.parse_args()
 prepare() if a.action=='prepare' else comparators()
