import json,os,signal,subprocess,sys,time
from pathlib import Path
from datetime import timedelta
from uuid import uuid4
import redis,rq
from rq import Queue,Worker
from tests.rq.rq212_tasks import lifecycle_job
s='/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock';c=redis.Redis(unix_socket_path=s,db=2);q=Queue('rq212-poolprobe-'+uuid4().hex,connection=c)
log=Path('/tmp/'+q.name+'.log');p=subprocess.Popen([sys.executable,'-m','tests.rq.rq212_tasks',s,q.name,'/tmp/'+q.name+'.audit','--pool'],stdout=log.open('w'),stderr=subprocess.STDOUT,start_new_session=True)
def wait(f):
 for _ in range(1000):
  v=f()
  if v:return v
  time.sleep(.02)
 raise RuntimeError('timeout')
def snap(label,pids):
 print(label,json.dumps({'rq':rq.__version__,'pids':pids,'fds':{str(pid):[os.readlink(f) for f in Path('/proc/'+str(pid)+'/fd').glob('*') if f.exists()] for pid in pids},'clients':[{k:v for k,v in x.items() if k in ('id','name','cmd','flags','db','age','idle')} for x in c.client_list()]},sort_keys=True),flush=True)
try:
 a=q.enqueue_in(timedelta(seconds=1),lifecycle_job,kwargs={'marker':q.name+'-a'})
 wait(lambda:a.get_status()=='finished');w=wait(lambda:next((w for w in Worker.all(connection=c) if q.name in w.queue_names() and w.get_state()=='idle'),None))
 children=[int(x) for x in Path('/proc/'+str(w.pid)+'/task/'+str(w.pid)+'/children').read_text().split()]
 snap('before',[p.pid,w.pid,*children]);os.kill(w.pid,signal.SIGKILL)
 wait(lambda:next((x for x in Worker.all(connection=c) if q.name in x.queue_names() and x.name!=w.name),None))
 b=q.enqueue(lifecycle_job,kwargs={'marker':q.name+'-b'});time.sleep(2)
 snap('after',[p.pid,*children]);print('job',b.id,b.get_status(),b.worker_name,'queue',q.job_ids,'intermediate',c.lrange(q.intermediate_queue.key,0,-1),flush=True)
 if b.get_status()!='finished':
  for child in children:
   os.kill(child,signal.SIGKILL)
  cjob=q.enqueue(lifecycle_job,kwargs={'marker':q.name+'-c'});wait(lambda:cjob.get_status()=='finished');print('post-scheduler-kill',cjob.id,cjob.get_status(),flush=True)
finally:
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 try:os.killpg(p.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 print(log.read_text(),flush=True)
 for key in list(c.scan_iter(match='*'+q.name+'*')):c.delete(key)
 q.delete(delete_jobs=True)
