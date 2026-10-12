"""Submit one bounded SA-01 prep worker on forest; never executes a model."""
from pathlib import Path
import json
import uuid

import redis
from rq import Queue
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core.wepp import Wepp, prep_multi_ofe_hillslope
from wepppy.nodb.core.soil_anisotropy import effective_anisotropy

ROOT = Path('/wc1/runs/sa/sa-anisotropy-validation')
DESTINATION = ROOT / 'wepp/runs-rq-validation'
DESTINATION.mkdir(exist_ok=True)
overrides = effective_anisotropy(Wepp.load_detached(str(ROOT)))
assert overrides == (25, 3)
args = ('101', 1, str(ROOT), str(DESTINATION), 1, None, .4,
        False, 300, False, 1000, False, 1000, None, False, False, overrides)
with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
    job = Queue('default', connection=connection).enqueue_call(
        prep_multi_ofe_hillslope, args=(args,), timeout=120, result_ttl=86400,
        job_id='sa-anisotropy-' + uuid.uuid4().hex,
        meta={'runid': ROOT.name, 'validation': 'SA-01 bounded native worker'},
    )
    print(json.dumps({'job_id': job.id, 'queue': 'default', 'destination': str(DESTINATION)}))
