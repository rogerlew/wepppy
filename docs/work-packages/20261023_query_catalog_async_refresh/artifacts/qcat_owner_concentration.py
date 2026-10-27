import collections,json,os
from pathlib import PurePosixPath
import redis
from wepppy.config.redis_settings import RedisDB,redis_connection_kwargs
assert (os.getuid(),os.getgid())==(1002,130)
c=redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
roots=[('/wc1/runs','wc1:runs',2),('/wc1/batch','wc1:batch',1),('/wc1/culverts','wc1:culverts',1),('/geodata/weppcloud_runs','legacy:runs',1)]
keys=['query-catalog:validation:20261027:legacy-stream-0035','query-catalog:inventory:9d4205ed0955b7518cd3b2a8556a00c6e83cf29b7a8ca97b2a32a165d341a6d4']
counts={ns:collections.Counter() for _,ns,_ in roots};total=0
for key in keys:
 for raw in c.smembers(key+':scopes'):
  p=PurePosixPath(raw.decode());matches=[(root,ns,depth) for root,ns,depth in roots if p.is_relative_to(root)]
  assert len(matches)==1
  root,ns,depth=matches[0];parts=p.relative_to(root).parts;assert len(parts)>=depth
  counts[ns][parts[:depth]]+=1;total+=1
result={}
for ns,owners in counts.items():
 values=list(owners.values())
 result[ns]={'scopes':sum(values),'owners':len(values),'largest_owner_scope_count':max(values),'owners_with_multiple_scopes':sum(v>1 for v in values),'scopes_per_owner_histogram':dict(sorted(collections.Counter(values).items()))}
assert total==30891
print(json.dumps({'state':'passed','scope':'All discovered scopes, INCLUDING READONLY; not writable-only concentration. Lexical owner depth matches canonical _owner after full classification validated locators. No project reads or writes.','total_scopes':total,'namespaces':result}))
