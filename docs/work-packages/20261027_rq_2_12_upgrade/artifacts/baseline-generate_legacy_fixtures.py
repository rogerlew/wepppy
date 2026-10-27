"""Capture isolated genuine RQ 1.16.2 Redis states; contains no application data."""
import base64
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import redis
import rq
from rq import Queue
from rq.command import send_stop_job_command

def capture(connection, key):
 kind=connection.type(key).decode()
 enc=lambda value:base64.b64encode(value).decode()
 if kind=='string':value=enc(connection.get(key))
 elif kind=='hash':value={enc(k):enc(v) for k,v in connection.hgetall(key).items()}
 elif kind=='list':value=[enc(v) for v in connection.lrange(key,0,-1)]
 elif kind=='set':value=sorted(enc(v) for v in connection.smembers(key))
 elif kind=='zset':value={enc(k):v for k,v in connection.zrange(key,0,-1,withscores=True)}
 elif kind=='stream':value=[[enc(k),{enc(f):enc(v) for f,v in fields.items()}] for k,fields in connection.xrange(key)]
 else:raise ValueError(kind)
 return {'key':enc(key),'type':kind,'value':value,'pttl':connection.pttl(key)}

socket='/workdir/wepppy/.pytest_cache/rq212-baseline/redis.sock'
c=redis.Redis(unix_socket_path=socket,db=6)
assert rq.__version__=='1.16.2'
assert c.dbsize()==0
prefix='rq212-legacy-'+uuid.uuid4().hex
q=Queue(prefix,connection=c)
finished=q.enqueue(math.sqrt,81,job_id=prefix+'-finished',result_ttl=86400)
failed=q.enqueue(math.sqrt,-1,job_id=prefix+'-failed',failure_ttl=86400)
active=q.enqueue(time.sleep,120,job_id=prefix+'-started',result_ttl=86400)
queued=q.enqueue(math.sqrt,16,job_id=prefix+'-queued',result_ttl=86400)
deferred=q.enqueue(math.sqrt,25,job_id=prefix+'-deferred',depends_on=queued,result_ttl=86400)
scheduled=q.enqueue_at(datetime.utcnow()+timedelta(days=1),math.sqrt,36,job_id=prefix+'-scheduled',result_ttl=86400)
code='import redis;from rq import Queue,Worker;c=redis.Redis(unix_socket_path='+repr(socket)+',db=6);Worker([Queue('+repr(prefix)+',connection=c)],connection=c).work(burst=True)'
worker=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  if active.get_status()=='started':break
  if worker.poll() is not None:raise RuntimeError('fixture worker exited early')
  time.sleep(.1)
 else:raise RuntimeError('fixture workhorse did not start')
 jobs={name:job for name,job in [('queued',queued),('deferred',deferred),('scheduled',scheduled),('started',active),('finished',finished),('failed',failed)]}
 assert {name:job.get_status() for name,job in jobs.items()}=={name:name for name in jobs}
 snapshot={'rq_version':rq.__version__,'redis_version':c.info('server')['redis_version'],'queue':prefix,'jobs':{name:job.id for name,job in jobs.items()},'keys':[]}
 for key in sorted(c.scan_iter()):
  payload=c.dump(key)
  snapshot['keys'].append(capture(c,key))
 out=Path('/workdir/wepppy/.pytest_cache/rq212-baseline/legacy-fixtures.json');out.write_text(json.dumps(snapshot,indent=2))
 print(json.dumps({'path':str(out),'states':list(jobs),'key_count':len(snapshot['keys']),'queue':prefix}))
 worker.terminate()  # Warm stop prevents dequeuing queued successors.
 time.sleep(.25)
 send_stop_job_command(c,active.id)
 worker.wait(timeout=30)
 assert queued.get_status()=='queued' and deferred.get_status()=='deferred'
 snapshot['jobs']['stopped']=snapshot['jobs'].pop('started')
 snapshot['keys']=[]
 for key in sorted(c.scan_iter()):
  snapshot['keys'].append(capture(c,key))
 out.with_name('legacy-drained-fixtures.json').write_text(json.dumps(snapshot,indent=2))
 print('drained snapshot captured')
finally:
 if worker.poll() is None:
  worker.terminate();worker.wait(timeout=15)
