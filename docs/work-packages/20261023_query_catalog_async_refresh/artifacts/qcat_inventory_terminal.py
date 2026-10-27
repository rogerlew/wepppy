import json,hashlib,os,time
import redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
assert (os.getuid(),os.getgid())==(1002,130)
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
keys=['query-catalog:validation:20261027:legacy-stream-0035','query-catalog:inventory:9d4205ed0955b7518cd3b2a8556a00c6e83cf29b7a8ca97b2a32a165d341a6d4']
results=[]
for key in keys:
 state=json.loads(c.get(key+':discovery'))
 paths=c.smembers(key+':scopes');stream=c.xrange(key+':stream')
 fields=sorted({k.decode() for _,v in stream for k in v})
 assert fields==['path'],fields
 emitted=[v[b'path'] for _,v in stream]
 assert state.get('completed_at') and not state['errors']
 assert c.llen(key+':frontier')==0
 assert len(emitted)==len(set(emitted))==len(paths) and set(emitted)==paths
 results.append({'key':key,'state':state,'frontier':0,'scopes':len(paths),'stream':len(emitted),'unique_stream_equals_scope_set':True,'sorted_scope_digest':hashlib.sha256(b'\n'.join(sorted(paths))).hexdigest(),'ttl_seconds':c.ttl(key+':discovery')})
print(json.dumps({'state':'passed','observed_at':time.time(),'uid':os.getuid(),'gid':os.getgid(),'inventories':results,'total_scopes':sum(r['scopes'] for r in results),'limitation':'Discovery only; no fleet reconciliation or project writes.'}))
