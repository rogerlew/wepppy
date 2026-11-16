"""Retain recovery evidence despite the fixture's unrelated watershed date mismatch."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['WEPPPY_NCPU'] = '4'
from starlette.requests import Request
from wepppy.microservices.rq_engine.omni_routes import _run_omni
from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.mods.omni.omni_sbs_freshness import child_source

wd = Path('/wc1/runs/qa/qa-omni-reload-20261116')
out = Path('/workdir/wepppy/docs/work-packages/20261116_omni_sbs_reload/artifacts/runtime_followup.json')
assert not out.exists(), 'Retain every runtime attempt'
omni = Omni.getInstance(str(wd))
saved = omni.scenarios[0]
staged = Path(saved['sbs_file_path'])
child = child_source(omni, saved)
assert child.exists() and not staged.exists()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
expected = digest(child)
body = json.dumps({'scenarios': omni.scenarios}).encode()
async def receive():
    return {'type': 'http.request', 'body': body, 'more_body': False}
request = Request({'type': 'http', 'method': 'POST', 'path': '/',
                   'headers': [(b'content-type', b'application/json')]}, receive)
response = asyncio.run(_run_omni(wd.name, '_base', request))
assert response.status_code == 200, response.body
assert digest(staged) == expected
assert Omni.load_detached(str(wd)).scenarios == [saved]
result = {'admission_status': response.status_code, 'restored_sha256': expected,
          'real_nodb_reload': True, 'uid': os.getuid(), 'gid': os.getgid(),
          'known_fixture_blocker': 'channel climate starts 2007; hillslope passes start 1980',
          'status': 'running'}
out.write_text(json.dumps(result, indent=2)+'\n')
omni = Omni.getInstance(str(wd))
omni.scenario_dependency_tree = {}
started = time.time()
try:
    omni.run_omni_scenarios()
except Exception as exc:  # Acceptance boundary: preserve the real native failure, never mask it.
    result['execution_error'] = str(exc)
    result['status'] = 'watershed_blocked'
else:
    result['status'] = 'passed'
assert child.exists() and digest(child) == expected
assert not staged.exists()
root = child.parent.parent
from osgeo import gdal
raster = gdal.Open(str(child))
result['raster'] = {'width': raster.RasterXSize, 'height': raster.RasterYSize,
                    'bands': raster.RasterCount, 'checksum': raster.GetRasterBand(1).Checksum()}
raster = None
result['consumed_after_reset'] = True
result['artifacts'] = {}
for suffix in ('*.man', '*.sol', '*.run'):
    files = sorted((root / 'wepp/runs').glob(suffix))
    assert files
    result['artifacts'][suffix] = {'count': len(files), 'sample': files[0].name,
                                   'sha256': digest(files[0]),
                                   'first_line': files[0].read_text().splitlines()[0]}
losses = sorted((root / 'wepp/output').glob('H*.loss.dat'))
assert losses
assert all(p.stat().st_mtime >= started for p in losses)
result['fresh_hillslope_outputs'] = len(losses)
result['seconds'] = time.time()-started
result['watershed_error_tail'] = (root / 'wepp/runs/pw0.err').read_text().splitlines()[-5:]
out.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result), flush=True)
