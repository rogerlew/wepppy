import json,os,signal,subprocess,sys,time
from pathlib import Path
from datetime import timedelta
from uuid import uuid4
import redis,rq
from rq import Queue,Worker
from tests.rq.rq212_tasks import lifecycle_job
s='/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock';c=redis.Redis(unix_socket_path=s,db=10)
assert not list(c.scan_iter()),'DB10 is not disposable/empty'
q=Queue('rq212-takeover-'+uuid4().hex,connection=c);processes=[];logs=[];jobs=[]
def wait(f):
 for _ in range(1500):
  v=f()
  if v:return v
  time.sleep(.02)
 raise RuntimeError('timeout')
def start():
 log=Path('/tmp/'+q.name+'-'+str(len(processes))+'.log');p=subprocess.Popen([sys.executable,'.pytest_cache/rq212_tasks_db10.py',s,q.name,'/tmp/'+q.name+'.audit','--scheduler'],stdout=log.open('w'),stderr=subprocess.STDOUT,start_new_session=True);processes.append(p);logs.append(log);return p
def child_pids(pid):return [int(x) for x in Path('/proc/'+str(pid)+'/task/'+str(pid)+'/children').read_text().split()]
def scheduler_pid():
 for key in c.scan_iter(match='rq:scheduler:*'):
  if c.type(key)==b'hash' and c.hget(key,'queues')==q.name.encode():
   pid=c.hget(key,'pid')
   if pid:return int(pid)
 return None
def sockets(pid):return [os.readlink(f) for f in Path('/proc/'+str(pid)+'/fd').glob('*') if f.exists() and os.readlink(f).startswith('socket:')]
def blocked():return [x['id'] for x in c.client_list() if x.get('db')=='10' and x.get('cmd')=='blmove' and 'b' in x.get('flags','')]
def enqueue(scheduled=False):
 j=q.enqueue_in(timedelta(seconds=1),lifecycle_job,kwargs={'marker':q.name+'-'+str(len(jobs))}) if scheduled else q.enqueue(lifecycle_job,kwargs={'marker':q.name+'-'+str(len(jobs))});jobs.append(j);return j
try:
 p=start();j=enqueue(True);wait(lambda:j.get_status()=='finished');wait(lambda:blocked());old=wait(scheduler_pid)
 os.kill(old,signal.SIGKILL);time.sleep(1.2);wake=enqueue();wait(lambda:wake.get_status()=='finished')
 new=wait(lambda:scheduler_pid() if scheduler_pid()!=old else None);j2=enqueue(True);wait(lambda:j2.get_status()=='finished');old_clients=wait(lambda:blocked());print(json.dumps({'version':rq.__version__,'worker':p.pid,'old_scheduler':old,'maintenance_scheduler':new,'worker_sockets':sockets(p.pid),'scheduler_sockets':sockets(new),'blocked_clients':old_clients,'scheduled_result':j2.return_value()},sort_keys=True),flush=True)
 os.kill(p.pid,signal.SIGKILL);p.wait();wait(lambda:not(set(old_clients)&{x['id'] for x in c.client_list()}));p2=start();wait(lambda:any(w.pid==p2.pid for w in Worker.all(connection=c)));j3=enqueue();wait(lambda:j3.get_status()=='finished');print(json.dumps({'replacement':p2.pid,'job':j3.id,'result':j3.return_value(),'intermediate':c.lrange(q.intermediate_queue.key,0,-1)}),flush=True)
finally:
 for p in processes:
  if p.poll() is None:
   p.terminate()
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 for log in logs:print(log.read_text(),flush=True)
 # DB10 was admitted only after proving empty and is owned by this probe.
 keys=list(c.scan_iter())
 if keys:c.delete(*keys)
