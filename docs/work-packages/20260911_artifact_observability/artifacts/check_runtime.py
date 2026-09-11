"""Disposable storage-only check under the actual rq-worker identity and locks."""
import json
import os
from pathlib import Path
import uuid
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.postfire_debris_flow import migration as m, production as p
from wepppy.nodb.mods.postfire_debris_flow.observability import write_json
from wepppy.nodb.mods.postfire_debris_flow.postfire_debris_flow import PostfireDebrisFlow

runid = 'artifact-observability-check-' + uuid.uuid4().hex[:8]
wd = Path('/wc1/runs/ar')/runid
wd.mkdir()
Ron(str(wd),'disturbed9002_wbt.cfg')
controller = PostfireDebrisFlow(str(wd),'disturbed9002_wbt.cfg')
source = wd/'postfire_debris_flow'/'.staging'/('a'*32)/'results'
source.mkdir(parents=True)
for name in p.FILES[:-1]:
    (source/name).write_bytes(b'storage-only fixture '+name.encode())
write_json(source/'manifest.json', {'schema_version':1,'path':str(source),'fixture':'storage-only'})
with controller.locked():
    controller._state['last_successful_run'] = {'id':'a'*32,'snapshot':{'inputs':{'selections':{'engine_sha256':m.LEGACY_ENGINE}}},
        'artifacts':{str(path.relative_to(wd)):p.signature(wd,path,strong=True) for path in source.iterdir()}}
report = m.migrate_attempts(str(wd))
assert report['status']=='complete'
assert not (wd/'postfire_debris_flow'/'.staging').exists()
assert p.artifacts_current(wd,p.state_at(wd)['last_successful_run'])
assert p.state_at(wd)['last_successful_run']['snapshot']['inputs']['selections']['engine_sha256']==m.TARGET_ENGINE
print(json.dumps({'status':'passed','runid':runid,'uid':os.getuid(),'gid':os.getgid(),
                  'migration_status':report['status'],'files':len(report['inventory'])}))
