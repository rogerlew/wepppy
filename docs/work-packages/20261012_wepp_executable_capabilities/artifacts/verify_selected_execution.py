"""Read actual native output and runner identity for the selected-release job."""
from pathlib import Path
import hashlib
import json
import re

import redis
from rq.job import Job
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Wepp
from wepppy.wepp.soils.utils import WeppSoilUtil

EVIDENCE = Path(__file__).parent
receipt = json.loads((EVIDENCE / 'selected-execution-submission.json').read_text())
root = Path(receipt['wd'])
with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
    job = Job.fetch(receipt['job_id'], connection=connection)
    status = job.get_status(refresh=True)
    assert status == 'finished', job.exc_info or status
    assert job.return_value()[0] is True
    worker_name = job.worker_name
assert Wepp.load_detached(str(root)).wepp_bin == receipt['selected_binary']
for name, digest in receipt['config_hashes_unchanged'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
output = root / 'wepp/output/H1.loss.dat'
content = output.read_text()
assert content and not re.search(r'\b(?:nan|inf(?:inity)?)\b', content, re.I)
soil = root / 'wepp/runs/p1.sol'
assert len(WeppSoilUtil(str(soil), preserve_input_format=True).obj['ofes']) == 2
logs = [path for directory in ('wepp/runs', 'wepp/output') for path in (root / directory).iterdir()
        if path.is_file() and 'err' in path.name]
identity_lines = [line for path in logs for line in path.read_text().splitlines() if 'binary_identity' in line]
assert any(receipt['hillslope_binary_sha256'] in line for line in identity_lines), identity_lines
result = receipt | {'status': str(status), 'worker_name': worker_name,
                    'function': job.func_name, 'native_success': True, 'ofes': 2,
                    'prepared_sha256': hashlib.sha256(soil.read_bytes()).hexdigest(),
                    'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                    'output_bytes': output.stat().st_size, 'output_uid': output.stat().st_uid,
                    'output_gid': output.stat().st_gid, 'output_mode': oct(output.stat().st_mode & 0o777),
                    'runner_identity': identity_lines,
                    'scope': 'Real grouped payload save/reload, real MOFE prep, native hillslope execution on forest default RQ worker. No full watershed simulation or production run mutation.'}
(EVIDENCE / 'selected-execution-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
