import json,os
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
p=Path('/geodata/weppcloud_runs/.qcat-role-20261027-0020')
assert not p.exists()
p.mkdir(mode=0o750)
(p/'probe.json').write_text(json.dumps({'probe':'qcat-role-20261027-0020','source_owner':[os.getuid(),os.getgid()]}))
(p/'.config-amendment.lock').touch(mode=0o600)
print(json.dumps({'path':str(p),'uid':os.getuid(),'gid':os.getgid(),'prepared':True}))
