"""A01: unchanged native binary, failed-event observation target, exact parity."""
import argparse,hashlib,importlib.util,json,math,os,re,shutil,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
RAW=REPO/'out/rock-water-development-20261101';OLD=REPO/'out/retention-frost-consumers-20261101'
CASE='84543461-candidate-ks1';ROOT=RAW/'A01-v2';ENV={**os.environ,'PATH':'/usr/bin:/bin','FC':'/usr/bin/gfortran','PYTHONDONTWRITEBYTECODE':'1'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,d):
 with Path(p).open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def inventory(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def check(d):
 for p,h in d.items():
  if sha(p)!=h:raise ValueError('Dependency drift '+p)
def runtime(binary):
 if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'):raise ValueError('Loader override')
 text=subprocess.check_output(['/usr/bin/ldd',str(binary)],env=ENV,text=True)
 return {str(Path(p).resolve()):sha(p) for p in re.findall(r'(/[^\s()]+)',text)}
def prepare():
 ROOT.mkdir();runs=ROOT/'runs';runs.mkdir();(ROOT/'output').mkdir()
 d=json.loads((OLD/'prepared-v3/declaration.json').read_text());check(d['dependencies']);binary=OLD/'prepared-v3/base-build/src/wepp'
 if inventory(OLD/'prepared-v3/base-build')!=d['base_inventory']:raise ValueError('Base build drift')
 if runtime(binary)!=d['libraries']:raise ValueError('Runtime mismatch')
 source=OLD/'comparators-v1'/CASE;original=json.loads((source/'pre-execution.json').read_text())
 for p,h in original['inputs'].items():
  if sha(source/'runs'/p)!=h:raise ValueError('Original input drift')
  shutil.copy2(source/'runs'/p,runs/p)
 (runs/'buffer_observe.on').write_text('9 355\n')
 if {p for p,h in inventory(runs).items() if h!=original['inputs'][p]}!={'buffer_observe.on'}:raise ValueError('Unplanned input change')
 reference={str(source/'output'/p):sha(source/'output'/p) for p in inventory(source/'output')}
 reference[str(source/'runs/frwatc-history.txt')]=sha(source/'runs/frwatc-history.txt')
 deps={**d['dependencies'],str(binary):sha(binary),str(Path(__file__)):sha(__file__),str(source/'receipt.json'):sha(source/'receipt.json'),**reference}
 save(ROOT/'declaration.json',dict(purpose='Same failure with BPO window9/355; no model change',binary=str(binary),dependencies=deps,inputs=inventory(runs),libraries=d['libraries'],reference=reference,expected_returncode=1,expected_marker='HOURLY_WATER_UNMET',expected_partial_calendar_rows=9830,model_processes=1))
 print('A01 prepared; no native invocation')
def run():
 d=json.loads((ROOT/'declaration.json').read_text());approval=json.loads((ROOT/'approval.json').read_text())
 if approval['declaration_sha256']!=sha(ROOT/'declaration.json'):raise ValueError('Approval drift')
 check({**d['dependencies'],**approval['reviews']});runs=ROOT/'runs';check({str(runs/p):h for p,h in d['inputs'].items()})
 if runtime(d['binary'])!=d['libraries']:raise ValueError('Runtime drift')
 result=dict(command=[d['binary']],cwd=str(runs),PATH=ENV['PATH'],FC=ENV['FC'],timeout_seconds=900,start=time.time())
 save(ROOT/'process-pre.json',result)
 with (runs/'p1.run').open('rb') as inp,(runs/'stdout').open('xb') as out,(runs/'stderr').open('xb') as err:
  try:
   p=subprocess.run(result['command'],cwd=runs,env=ENV,stdin=inp,stdout=out,stderr=err,timeout=900);result['returncode']=p.returncode
  except subprocess.TimeoutExpired:result['returncode']=None;result['timeout']=True
 result.update(seconds=time.time()-result['start'],stdout_sha256=sha(runs/'stdout'),stderr_sha256=sha(runs/'stderr'))
 save(ROOT/'process-result.json',result)
 source=OLD/'comparators-v1'/CASE
 same=inventory(ROOT/'output')==inventory(source/'output') and sha(runs/'frwatc-history.txt')==sha(source/'runs/frwatc-history.txt')
 stdout=(runs/'stdout').read_text();diagnostics=[x.strip() for x in stdout.splitlines() if d['expected_marker'] in x]
 lines=[]
 for line in (ROOT/'output/H1.wat.dat').open():
  v=line.split()
  if len(v)==25 and v[0].isdigit():lines.append(tuple(map(int,v[:3])))
 original_diagnostics=[x.strip() for x in (source/'runs/stdout').read_text().splitlines() if d['expected_marker'] in x]
 records=[]
 for line in (runs/'buffer-observation.txt').open():
  v=line.split()
  if len(v)!=11 or int(v[1])!=9 or int(v[2]) not in (354,355) or not all(math.isfinite(float(x)) for x in v[5:]):raise ValueError('BPO framing/clock/numeric')
  records.append((v[0],*map(int,v[1:5])))
 required={('BP_WBH_SOURCE',9,355,3,1),('BP_WBH_ALLOC',9,355,3,1)}|{('BP_WBH_BEFORE_'+tag,9,355,3,100+i) for tag in ('W','K') for i in range(1,5)}
 if not required<=set(records) or any(records.count(x)!=1 for x in required):raise ValueError('Missing/duplicate failing-event BPO support')
 passed=diagnostics==original_diagnostics and result['returncode']==1 and len(diagnostics)==1 and same and len(set(lines))==len(lines)==9830 and 'WEPP COMPLETED' not in stdout
 check(d['dependencies']);check({str(runs/p):h for p,h in d['inputs'].items()})
 save(ROOT/'receipt.json',dict(passed=passed,expected_failure_reproduced=result['returncode']==1,full_history_admission=False,ordinary_and_frost_byte_parity=same,partial_daily_rows=len(lines),diagnostics=diagnostics,buffer_sha256=sha(runs/'buffer-observation.txt'),process=result))
 print(json.dumps(dict(passed=passed,diagnostics=diagnostics,ordinary_and_frost_byte_parity=same)))
 if not passed:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);a=p.parse_args();prepare() if a.action=='prepare' else run()
