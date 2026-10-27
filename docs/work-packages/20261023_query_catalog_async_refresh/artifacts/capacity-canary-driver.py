import concurrent.futures
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import threading
import time
import uuid

HERE=Path(__file__).resolve().parent;repo=HERE.parents[3]
OUT=HERE/'capacity-canary-logs';OUT.mkdir(exist_ok=True)
name='qcat-capacity-20261027-'+uuid.uuid4().hex[:8]
config=dict(name=name,base='/wc1/query-catalog-validation/20261026/'+name,source='/wc1/query-catalog-validation/20261026/rollout-cycle-2355/runs/representative')
files={'probe.py':(HERE/'capacity-canary-probe.py').read_text(),'config.json':json.dumps(config)}
for f in ['query_catalog_rq.py','_query_catalog_inventory.py']:files[f]=(repo/'wepppy/rq'/f).read_text()
container='docker-rq-worker-batch-1';locations={}
for host in ['wepp1','wepp2']:
 stage='''import json,os,sys,tempfile
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
p=Path(tempfile.mkdtemp(prefix="qcat-capacity-"))
for name,text in json.load(sys.stdin).items():
 f=p/name;f.write_text(text);f.chmod(0o600)
print(p)
'''
 r=subprocess.run(['ssh',host,'docker exec -i '+container+' python -c '+shlex.quote(stage)],input=json.dumps(files),capture_output=True,text=True,timeout=25)
 assert r.returncode==0,r.stderr
 locations[host]=r.stdout.strip();assert locations[host].startswith('/tmp/qcat-capacity-')
(OUT/'manifest.json').write_text(json.dumps(dict(config=config,locations=locations,source_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}),indent=2))
def command(host,role):return ['ssh',host,'docker','exec','-i',container,'python','-u',locations[host]+'/probe.py',role,host]
def once(role):
 with (OUT/(role+'.stdout')).open('w') as out,(OUT/(role+'.stderr')).open('w') as err:
  r=subprocess.run(command('wepp1',role),stdout=out,stderr=err,text=True,timeout=720)
 assert r.returncode==0,f'{role} failed; logs retained'
 print(role+' complete',flush=True)
once('setup')
workers=[]
try:
 for host in locations:
  ready=threading.Event();err=(OUT/(host+'.stderr')).open('w')
  process=subprocess.Popen(command(host,'worker'),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True)
  def collect(process=process,host=host,ready=ready):
   with (OUT/(host+'.stdout')).open('w') as out:
    for line in process.stdout:
     out.write(line);out.flush()
     if '"event": "worker_ready"' in line:ready.set()
  thread=threading.Thread(target=collect);thread.start();workers.append((process,thread,ready,err))
 for process,thread,ready,err in workers:assert ready.wait(35),'worker did not register'
 once('enqueue');start=time.time()
 for process,thread,ready,err in workers:process.stdin.write('go\n');process.stdin.flush();process.stdin.close()
 for process,thread,ready,err in workers:
  code=process.wait(timeout=max(1,660-(time.time()-start)));thread.join();err.close();assert code==0,'owned worker failed; logs retained'
 print('workers complete',time.time()-start,flush=True)
 once('verify')
finally:
 for process,thread,ready,err in workers:
  if process.poll() is None:
   # Close the owned barrier input; allow the bounded worker process to exit.
   if not process.stdin.closed:process.stdin.close()
   process.wait(timeout=735)
  thread.join(timeout=5)
  if not err.closed:err.close()
