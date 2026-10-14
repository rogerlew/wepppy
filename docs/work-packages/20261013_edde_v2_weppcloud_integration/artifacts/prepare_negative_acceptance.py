from pathlib import Path
import shutil
from wepppy.nodb.core import Climate
p=Path('/wc1/runs/ed/edde-ca-prism-rejected-20261014')
if not p.exists(): shutil.copytree('/wc1/runs/ed/edde-ca-20261014',p,ignore=shutil.ignore_patterns('archives'))
c=Climate.getInstance(str(p)); print(c.config_stem,c.cli_fn)
# A filesystem copy must not claim the original run's workflow associations.
# Clear only inherited associations in this isolated acceptance clone.
from wepppy.nodb.redis_prep import RedisPrep
prep=RedisPrep.getInstance(str(p))
assert prep.run_id == p.name
keys=[key for key in prep.redis.hkeys(prep.run_id) if key.startswith('rq:') or key == 'archive:job_id']
if keys: prep.redis.hdel(prep.run_id,*keys)
prep.dump()
