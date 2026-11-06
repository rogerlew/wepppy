import json, os, time
from pathlib import Path
if not __debug__:
 raise RuntimeError('Optimized Python is forbidden for hold verification')
now=time.time()
rows=[]
observations={}
for host in ('wepp1','wepp2','wepp3'):
 data=json.loads(Path('/tmp/production-holds-'+host+'.json').read_text())
 assert data['host']==host
 assert 0<=now-data['observed_at']<300
 assert all(c['host']==host for c in data['containers'])
 observations[host]=data['observed_at']
 rows.extend(data['containers'])
expected={('wepp1','weppcloud'),('wepp1','rq-engine'),('wepp1','scheduler'),('wepp1','rq-worker'),('wepp1','rq-worker-batch'),('wepp2','rq-worker'),('wepp2','rq-worker-batch'),('wepp3','rq-worker-fork-archive')}
assert len(rows)==len(expected) and {(c['host'],c['service']) for c in rows}==expected
assert len({(c['host'],c['id']) for c in rows})==8
assert all(c['state']=='exited' and c['pid']==0 for c in rows)
result={'observed_at':min(observations.values()),'host_observations':observations,'aggregated_at':now,'containers':rows}
fd=os.open('/tmp/production-old-runtime-holds.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
print(json.dumps({'old_containers_stopped':8,'oldest_observation_age_seconds':now-result['observed_at']}))
