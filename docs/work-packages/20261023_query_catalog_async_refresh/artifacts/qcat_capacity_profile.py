import hashlib,heapq,importlib.util,json,os,time
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
os.umask(0o077)
base=Path('/tmp/qcat-capacity-profile-20261027');base.mkdir(mode=0o700)
roots=[dict(path='/wc1/'+n,namespace='wc1:'+n,coordination='/wc1/query-engine-coordination/locks',layout=l) for n,l in [('runs','sharded'),('batch','batch'),('culverts','culverts')]]
roots.append(dict(path='/geodata/weppcloud_runs',namespace='legacy:runs',coordination='/wc1/query-engine-coordination/locks',layout='flat'))
os.environ['QUERY_CATALOG_ROOTS_JSON']=json.dumps(roots);os.environ['QUERY_CATALOG_REFRESH_ENABLED']='false'
import redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
from wepppy.query_engine.catalog_refresh import configured_roots,is_catalog_readonly
spec=importlib.util.spec_from_file_location('inventory_profile', '/tmp/qcat_inventory_final.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ));configs=configured_roots()
keys=['query-catalog:validation:20261027:legacy-stream-0035','query-catalog:inventory:9d4205ed0955b7518cd3b2a8556a00c6e83cf29b7a8ca97b2a32a165d341a6d4']
seen=set();counts={r.namespace:dict(scopes=0,readonly=0,writable=0,unwritable=0,missing_catalog=0) for r in configs};samples={r.namespace:[] for r in configs};errors=[];cursors={k:0 for k in keys};start=time.monotonic();rounds=0
while time.monotonic()-start<4500:
 for key in keys:
  cursor,paths=c.sscan(key+':scopes',cursor=cursors[key],count=300);cursors[key]=cursor
  for raw in paths:
   name=raw.decode()
   if name in seen:continue
   seen.add(name);digest=hashlib.sha256(name.encode()).hexdigest()
   try:
    p=inv.validated_scope_path(configs,name)
    config=max((r for r in configs if p.is_relative_to(r.path)),key=lambda r:len(r.path.parts))
    d=counts[config.namespace];d['scopes']+=1
    readonly=is_catalog_readonly(p);writable=os.access(p,os.W_OK)
    d['readonly']+=int(readonly);d['writable']+=int(not readonly and writable);d['unwritable']+=int(not readonly and not writable)
    d['missing_catalog']+=int(not (p/'_query_engine/catalog.json').is_file())
    if not readonly and writable:
     bucket=samples[config.namespace];bucket.append({'digest':digest,'path':str(p)});bucket.sort(key=lambda x:x['digest']);del bucket[12:]
   except (OSError,ValueError,RuntimeError) as exc:errors.append({'scope_digest':digest,'error':type(exc).__name__})
 states=[inv.state(c,k) for k in keys]
 summary={'elapsed_seconds':time.monotonic()-start,'counts':counts,'errors':errors,'profiled':len(seen),'discovered':sum(c.scard(k+':scopes') for k in keys),'inventory_completed':[bool(s.get('completed_at')) for s in states],'sample_method':'12 smallest SHA256 path digests per namespace, writable non-READONLY only; raw sample paths private'}
 (base/'summary.json').write_text(json.dumps(summary,indent=2));(base/'samples.json').write_text(json.dumps(samples,indent=2))
 if rounds%10==0:print(json.dumps(summary),flush=True)
 rounds+=1
 if all(summary['inventory_completed']) and summary['profiled']>=summary['discovered']:
  summary['state']='completed';(base/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True);break
 time.sleep(2)
else:
 summary['state']='incomplete_deadline';print(json.dumps(summary),flush=True)
