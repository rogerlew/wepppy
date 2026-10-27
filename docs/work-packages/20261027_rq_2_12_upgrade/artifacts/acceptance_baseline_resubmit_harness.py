import requests,re,json,time,hashlib,os
from pathlib import Path
from datetime import datetime,timezone
import redis,rq
from rq import Worker
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.weppcloud.app import app,user_datastore
BASE='https://wc.bearhive.duckdns.org'
SOURCE='rlew-international-refuge';TARGET='rq212-20261027-baseline';CONFIG='disturbed-wbt-profile'
OUT=Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts');OUT.mkdir(exist_ok=True)
record={'started':datetime.now(timezone.utc).isoformat(),'rq':rq.__version__,'source':SOURCE,'target':TARGET,'config':CONFIG,'auth':'existing dev-agent session seeded via Flask test client; actual HTTP profile CSRF mint and bearer API validation','requests':[]}
def save(): (OUT/'acceptance_baseline.json').write_text(json.dumps(record,indent=2,default=str))
def post(path,payload):
 r=s.post(BASE+path,json=payload,headers={'Authorization':'Bearer '+token},timeout=90)
 data=r.json();record['requests'].append({'path':path,'payload':payload,'status':r.status_code,'response':data});save();r.raise_for_status();return data

def wait(jobid,label):
 deadline=time.monotonic()+1200
 while time.monotonic()<deadline:
  r=s.get(BASE+'/rq-engine/api/jobinfo/'+jobid,headers={'Authorization':'Bearer '+token},timeout=45);r.raise_for_status();data=r.json()
  def nodes(x):
   if isinstance(x,dict):
    if 'status' in x and 'job_id' in x: yield x
    for value in x.values(): yield from nodes(value)
   elif isinstance(x,list):
    for value in x: yield from nodes(value)
  states=[(x['job_id'],x['status']) for x in nodes(data)]
  print(label,states,flush=True)
  record[label]={'job_id':jobid,'tree':data,'polled':datetime.now(timezone.utc).isoformat()};save()
  if states and (all(st in ('finished','failed','stopped','canceled') for _,st in states) or (any(st in ('failed','stopped','canceled') for _,st in states) and not any(st in ('queued','started','scheduled') for _,st in states))):
   assert all(st=='finished' for _,st in states),str(states)
   return data
  time.sleep(3)
 raise TimeoutError(label)
conn=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
record['workers_before']=[{'name':w.name,'queues':w.queue_names(),'job':w.get_current_job_id(),'state':w.get_state()} for w in Worker.all(connection=conn)];save()
with app.app_context():
 u=user_datastore.find_user(email='dev-agent@example.com');assert u and u.active
 c=app.test_client()
 with c.session_transaction() as x: x['_user_id']=u.fs_uniquifier;x['_fresh']=True
 assert c.get('/profile').status_code==200
 cookie=c.get_cookie(app.config.get('SESSION_COOKIE_NAME','session'));assert cookie
 s=requests.Session();s.cookies.set(cookie.key,cookie.value)
 r=s.get(BASE+'/weppcloud/profile',timeout=30);r.raise_for_status();assert u.email in r.text
 m=re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"',r.text);assert m
 r=s.post(BASE+'/weppcloud/profile/mint-token',headers={'X-CSRFToken':m.group(1)},timeout=30);r.raise_for_status()
 data=r.json();token=(data.get('Content') or data.get('content') or data.get('success') or {}).get('token');assert token
 response=post(f'/rq-engine/api/runs/{TARGET}/{CONFIG}/run-wepp',{'wepp_bin':'wepp_261026'})
 wait(response['job_id'],'model')
record['finished']=datetime.now(timezone.utc).isoformat();save()
