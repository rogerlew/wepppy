"""Read-only RQ worker metadata; never enqueue, mutate, or stop workers."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
connection=redis.StrictRedis(**redis_connection_kwargs(RedisDB.RQ,decode_responses=True))
fields=['name','queues','state','last_heartbeat','birth','hostname','pid']
workers=[]
for key in sorted(connection.smembers('rq:workers')):
 values=connection.hmget(key,fields);row=dict(zip(fields,values))
 if 'batch' in (row['queues'] or '').split(','):workers.append({'key':key,**row})
source=Path('/workdir/wepppy/tests/rq/test_batch_deferred_recovery.py')
receipt={'observed_at':datetime.now(timezone.utc).isoformat(),'redis_database':int(RedisDB.RQ),'read_commands':['SMEMBERS rq:workers','HMGET worker metadata'],'batch_workers':workers,'test_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'baseline_sha256':'2ea4b9d244889061dad363cd37ff9169a5d5118de6d8c5e349b4b71499f80355','baseline_identical':hashlib.sha256(source.read_bytes()).hexdigest()=='2ea4b9d244889061dad363cd37ff9169a5d5118de6d8c5e349b4b71499f80355'}
Path('/tmp/roads-refactor-validation/batch-worker-observation.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2));connection.close()
