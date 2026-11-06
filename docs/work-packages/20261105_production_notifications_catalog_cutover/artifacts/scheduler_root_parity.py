import json,os
from wepppy.query_engine.catalog_refresh import configured_roots
from wepppy.rq._query_catalog_inventory import validated_path
if not __debug__:raise RuntimeError('Optimized Python prohibited')
assert os.environ['EXTERNAL_HOST']=='wepp.cloud'
assert (os.getuid(),os.getgid())==(1002,130)
roots=configured_roots();rows=[]
for i,root in enumerate(roots):
 path=validated_path(roots,{'root':i,'relative':'.'})
 assert path.is_dir() and os.access(path,os.R_OK|os.X_OK)
 stat=path.stat();coord=root.coordination.stat()
 assert root.coordination.is_dir() and os.access(root.coordination,os.R_OK|os.W_OK|os.X_OK)
 rows.append({'path':str(path),'namespace':root.namespace,'directory_identity':[stat.st_dev,stat.st_ino],'coordination':str(root.coordination),'coordination_identity':[coord.st_dev,coord.st_ino]})
assert len(rows)==7 and len({r['namespace'] for r in rows})==4
print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'roots':rows},indent=2))
