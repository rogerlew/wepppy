"""One-time reviewed retirement of two proven completed October pilot permits."""
import copy, hashlib, json, os, time
from datetime import datetime
from pathlib import Path
import redis
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

if not __debug__:
 raise RuntimeError('Optimized Python is forbidden for this guarded operation')
root=Path('/cutover')
ledger_key='query-catalog:batch-admission:v1'
pause_key=ledger_key+':paused'
pilot_key='query-catalog:pilot:qcat-20261027-shared01'
expected_ids={'query_catalog_refresh_f1ad2339-ebeb-4c95-9562-184b257450a4','query_catalog_refresh_89b64ce2-0f44-4902-8ec7-e0de8b833a47'}
expected_ledger='bef8d251c310df87872dcd569dc2784f3cd5d698e6cc334b374442930abd2474'
expected_history='a940ebc78d12d43970feb3916f80b00c925506a234679c0974b82dcab8bc8710'
owner=b'production-cutover-20261106:expired-permit-reconciliation'
history_raw=Path('/wc1/query-catalog-validation/20261027/shared-pilot-01/result.json').read_bytes()
assert hashlib.sha256(history_raw).hexdigest()==expected_history
history=json.loads(history_raw)
assert history['outcome']=='completed'
assert history['status']['global_outstanding']==history['status']['global_uncertain']==0
holds=json.loads((root/'old-runtime-holds.json').read_text())
assert 0<=time.time()-holds['observed_at']<300
assert len(holds['containers'])==8
assert {(c['host'],c['service']) for c in holds['containers']}=={('wepp1','weppcloud'),('wepp1','rq-engine'),('wepp1','scheduler'),('wepp1','rq-worker'),('wepp1','rq-worker-batch'),('wepp2','rq-worker'),('wepp2','rq-worker-batch'),('wepp3','rq-worker-fork-archive')}
assert all(c['state']=='exited' and c['pid']==0 for c in holds['containers'])

def save(name,data):
 fd=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())

r=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
queues=['rq:queue:'+q for q in ('default','batch','fork-archive')]
registries=['rq:'+kind+':'+q for q in ('default','batch','fork-archive') for kind in ('wip','deferred','scheduled')]
job_keys=['rq:job:'+jid for jid in sorted(expected_ids)]
with r.pipeline() as p:
 p.watch(ledger_key,pause_key,pilot_key,pilot_key+':observer',*job_keys,*queues,*registries)
 assert not p.exists(pilot_key+':observer')
 assert p.ttl(ledger_key)==p.ttl(pilot_key)==p.ttl(pause_key)==-1
 assert p.get(pause_key)==owner
 before=p.get(ledger_key);assert hashlib.sha256(before).hexdigest()==expected_ledger
 ledger=json.loads(before);assert set(ledger['jobs'])==expected_ids
 pilot_raw=p.get(pilot_key);assert pilot_raw is not None
 assert hashlib.sha256(pilot_raw).hexdigest()=='1c525ccb0670e0ad4370e52cbefdb9dd055b2bb893d52b7b309c5007b9e686c5'
 pilot=json.loads(pilot_raw)
 assert pilot['pause_reason']=='acceptance_readback_complete'
 assert pilot['state']=='paused'
 for jid in expected_ids:
  binding=ledger['jobs'][jid]
  historical=copy.deepcopy(history['status']['jobs'][jid]);assert historical.pop('status')=='finished'
  assert binding==historical==pilot['jobs'][jid]
  assert binding['claimed'] is True and binding['execution_exited_at']
  assert history['jobs'][jid]['status']=='finished'
  assert datetime.fromisoformat(history['jobs'][jid]['ended_at'].replace('Z','+00:00')).timestamp()>=binding['execution_exited_at']
  assert not p.exists('rq:job:'+jid)
 for key in queues+registries:
  members=p.lrange(key,0,-1) if key in queues else p.zrange(key,0,-1)
  if ':wip:' in key:assert not members
  for raw in members:
   value=raw.decode()
   assert not any(value==jid or value.startswith(jid+':') for jid in expected_ids)
 after=copy.deepcopy(ledger)
 for jid in expected_ids:del after['jobs'][jid]
 assert {k:v for k,v in after.items() if k!='jobs'}=={k:v for k,v in ledger.items() if k!='jobs'}
 save('catalog-ledger-before.json',before)
 save('catalog-pilot-before.json',pilot_raw)
 after_raw=json.dumps(after,separators=(',',':')).encode()
 save('catalog-ledger-intended-after.json',after_raw)
 directory_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(directory_fd)
 finally:os.close(directory_fd)
 p.multi();p.set(ledger_key,after_raw);p.execute()
assert r.get(ledger_key)==after_raw
assert r.get(pilot_key)==pilot_raw
assert r.get(pause_key)==owner
save('catalog-ledger-after.json',after_raw)
print(json.dumps({'retired_completed_permits':sorted(expected_ids),'before_sha256':expected_ledger,'after_sha256':hashlib.sha256(after_raw).hexdigest(),'historical_sha256':expected_history,'pilot_bytes_unchanged':True,'pause_preserved':True,'initialized_at':after['initialized_at']}))
