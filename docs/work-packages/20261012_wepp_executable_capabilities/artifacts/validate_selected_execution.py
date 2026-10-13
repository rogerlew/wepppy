"""Bounded selected-release execution on the disposable browser-created project."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import uuid

import redis
from rq import Queue
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.microservices.rq_engine.wepp_run_payload import apply_wepp_run_payload
from wepppy.nodb.core import Wepp
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
from wepppy.weppcloud.utils.helpers import get_wd
from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope, get_linux_wepp_bin_role_paths

EVIDENCE = Path(__file__).parent
REPO = Path('/workdir/wepppy')
runid = json.loads((EVIDENCE / 'browser-validation.json').read_text())['runid']
root = Path(get_wd(runid))
assert root.name == runid and runid == 'sabbatical-stitcher', 'Only the retained disposable acceptance run is authorized'
before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ('config.cfg', 'config-manifest.json')}
# The exact production grouped-payload handler persists both explicit changes.
for selected in ('wepp_260803', 'wepp_261010'):
    apply_wepp_run_payload(str(root), {'wepp_bin': selected})
    assert Wepp.load_detached(str(root)).wepp_bin == selected
assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == value for name, value in before.items())
saved = Wepp.load_detached(str(root)).wepp_bin
native = json.loads((EVIDENCE / 'native-input-validation.json').read_text())
fixture = Path(native['root']) / 'wepp_261010/9002/2'
# These are reproducibly generated from the committed inputs named by the native receipt.
for relative in ('landuse/hill_101.mofe.man', 'soils/hill_101.mofe.sol', 'watershed/slope_files/hillslopes/hill_101.mofe.slp'):
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not destination.exists(), destination
    shutil.copyfile(fixture / relative, destination)
runs = root / 'wepp/runs'
runs.mkdir(parents=True, exist_ok=True)
prep_multi_ofe_hillslope(('101', 1, str(root), str(runs), 2, None, .42, False, None, False, None, False, None, None, True, True))
shutil.copyfile(REPO / 'tests/disturbed/data/test_climate.cli', runs / 'p1.cli')
make_hillslope_run(1, 2, str(runs), reveg=False, wepp_bin=saved)
with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as connection:
    job = Queue('default', connection=connection).enqueue_call(
        run_hillslope, args=(1, str(runs)), kwargs={'wepp_bin': saved},
        timeout=120, result_ttl=86400, job_id='cbexec-native-' + uuid.uuid4().hex,
        meta={'runid': runid, 'validation': 'CBEXEC bounded selected native execution'},
    )
receipt = {'runid': runid, 'wd': str(root), 'job_id': job.id, 'queue': 'default',
           'selected_binary': saved, 'config_hashes_unchanged': before,
           'hillslope_binary_sha256': hashlib.sha256(Path(get_linux_wepp_bin_role_paths(saved)[1]).read_bytes()).hexdigest(),
           'submit_uid': os.getuid(), 'submit_gid': os.getgid()}
(EVIDENCE / 'selected-execution-submission.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
