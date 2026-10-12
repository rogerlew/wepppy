"""Verify an SA-01 RQ job by its generated artifact, not job status alone."""
import hashlib
import json
from pathlib import Path
import sys

import redis
from rq.job import Job
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.wepp.soils.utils import WeppSoilUtil

with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
    job = Job.fetch(sys.argv[1], connection=connection)
    status = job.get_status(refresh=True)
    assert status == 'finished', job.exc_info or status
    root = Path('/wc1/runs/sa/sa-anisotropy-validation')
    source = root / 'soils/hill_101.mofe.sol'
    output = root / 'wepp/runs-rq-validation/p1.sol'
    expected = root / 'wepp/runs/p1.sol'
    ratios = [[h['anisotropy'] for h in ofe['horizons']]
              for ofe in WeppSoilUtil(str(output)).obj['ofes']]
    assert ratios == [[25, 25, 3], [25, 25, 3]]
    assert output.read_bytes() == expected.read_bytes()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash == '7f6efd4c102c0b17aafd85b448dfebf27bbf31ce186576358f07ac86b6052880'
    result = {
        'job_id': job.id, 'status': status, 'worker_name': job.worker_name,
        'origin': job.origin, 'function': job.func_name,
        'output_uid': output.stat().st_uid, 'output_gid': output.stat().st_gid,
        'output_mode': oct(output.stat().st_mode & 0o777), 'ratios': ratios,
        'prepared_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'source_sha256': source_hash, 'byte_identical_to_direct_prep': True,
        'scope': 'Existing prep_multi_ofe_hillslope on actual forest default RQ worker; no model execution.',
    }
    artifact = Path(__file__).with_name('rq-native-validation.json')
    artifact.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
