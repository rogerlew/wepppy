"""Authorized existing-project migration; no model rerun or numerical edits."""
import json
import os
from pathlib import Path
from wepppy.nodb.mods.postfire_debris_flow import migration as m, production as p

wd = Path('/wc1/runs/ad/addicted-reservist')
root = wd/'postfire_debris_flow'
state = p.state_at(wd)
accepted = state['last_successful_run']
legacy = root/'.staging'
binary = {str(file.relative_to(legacy)):p.digest(file) for file in legacy.rglob('*')
          if file.is_file() and file.suffix != '.json'}
print('BEFORE',json.dumps({'accepted_id':accepted['id'],'completed_at':accepted['completed_at'],
      'binary_files':len(binary),'attempts':len(list(legacy.iterdir())),'uid':os.getuid(),'gid':os.getgid()}),flush=True)
report = m.migrate_attempts(wd)
for name, digest in binary.items():
    assert p.digest(root/m._visible('.staging/'+name)) == digest, name
now = p.state_at(wd)
assert now['last_successful_run']['id'] == accepted['id']
assert now['last_successful_run']['completed_at'] == accepted['completed_at']
assert p.artifacts_current(wd,now['active_dnbr'])
assert p.artifacts_current(wd,now['last_successful_run'])
assert not legacy.exists()
assert not any(part.startswith('.') for path in root.rglob('*') for part in path.relative_to(root).parts)
print('AFTER',json.dumps({'status':report['status'],'binary_files_unchanged':len(binary),
      'inventory_files':len(report['inventory']),'engine_upgrades':report['upgraded_engine_records']}),flush=True)
print('STATE',json.dumps(p.get_state(wd,'config'),default=str),flush=True)
print('HASHES',json.dumps({str(path.relative_to(root)):p.digest(path) for path in root.rglob('*') if path.is_file()}),flush=True)
