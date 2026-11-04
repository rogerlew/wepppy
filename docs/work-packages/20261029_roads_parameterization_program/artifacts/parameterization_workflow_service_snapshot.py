"""Record non-secret local service/source identities for real workflow evidence."""
import hashlib,json,os,platform,sys
from pathlib import Path
RAW=Path('/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1')
REPO=Path('/workdir/wepppy')
paths=['wepppy/nodb/mods/roads/roads.py','wepppy/nodb/mods/roads/parameterization.py',
'wepppy/nodb/mods/roads/_parameterization_comparisons.py',
'wepppy/weppcloud/routes/nodb_api/roads_bp.py','wepppy/weppcloud/controllers_js/roads_parameterization.js',
'wepppy/weppcloud/templates/roads/parameterization.htm','wepppy/wepp/interchange/_roads_lifecycle.py',
'wepppy/rq/roads_rq.py','wepppy/rq/project_rq.py','wepp_runner/bin/wepp_261029','wepp_runner/bin/wepp_261029_hill']
mask=os.umask(0);os.umask(mask)
result={'service':sys.argv[1],'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),
'umask':oct(mask),'hostname':platform.node(),'source_sha256':{p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in paths},
'mounts':[s for s in Path('/proc/self/mountinfo').read_text().splitlines() if ' /wc1 ' in s or ' /workdir/wepppy ' in s]}
(RAW/(sys.argv[1]+'-identity.json')).write_text(json.dumps(result,indent=2)+'\n')
print(sys.argv[1],result['uid'],result['gid'],result['umask'],len(result['source_sha256']),'source identities recorded')
