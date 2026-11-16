"""Disposable direct admission/native acceptance; never writes the source project."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

os.environ['WEPPPY_NCPU'] = '4'
from starlette.requests import Request
from wepppy.microservices.rq_engine.omni_routes import _run_omni
from wepppy.nodb.mods.omni import Omni, OmniScenario
from wepppy.nodb.mods.omni.omni_sbs_freshness import child_source
from wepppy.nodb.core import Ron
from wepppy.rq.project_rq import _reset_forked_run_job_markers

runid = 'qa-omni-reload-20261116'
wd = Path('/wc1/runs/qa') / runid
out = Path('/workdir/wepppy/docs/work-packages/20261116_omni_sbs_reload/artifacts/runtime_result.json')
manifest = json.loads((wd.parent / (runid + '-copy-manifest.json')).read_text())
assert manifest['status'] == 'prepared'
assert not (wd / 'omni.nodb').exists(), 'Do not overwrite a prior native attempt'
_reset_forked_run_job_markers(runid, str(wd), runid + ':fork')
ron = Ron.getInstance(str(wd))
if 'omni' not in ron.mods:
    with ron.locked():
        ron._mods = list(ron.mods) + ['omni', 'treatments']
from wepppy.nodb.mods.treatments import Treatments
Treatments(str(wd), 'config.cfg')
omni = Omni(str(wd), 'config.cfg')
staged = wd / 'omni/_limbo/00/qa_omni_reload.tif'
staged.parent.mkdir(parents=True)
shutil.copyfile(wd / 'disturbed/GrizzlyCreek_SBS_final.tif', staged)
saved = {'type': 'sbs_map', 'sbs_file_path': str(staged)}
omni.parse_scenarios([(OmniScenario.SBSmap, saved)])
result = {'runid': runid, 'uid': os.getuid(), 'gid': os.getgid(),
          'groups': os.getgroups(), 'stages': [], 'status': 'running'}
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
expected = digest(staged)
result['source_sha256'] = expected

def record():
    out.write_text(json.dumps(result, indent=2) + '\n')
record()
for stage in ('initial', 'restored_forced_rerun'):
    if stage != 'initial':
        assert not staged.exists()
        body = json.dumps({'scenarios': Omni.load_detached(str(wd)).scenarios}).encode()
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        request = Request({'type': 'http', 'method': 'POST', 'path': '/',
                           'headers': [(b'content-type', b'application/json')]}, receive)
        response = asyncio.run(_run_omni(runid, '_base', request))
        assert response.status_code == 200, response.body
        assert staged.exists() and digest(staged) == expected
        # Force execution instead of a cache hit to test input survival across reset.
        omni = Omni.getInstance(str(wd))
        omni.scenario_dependency_tree = {}
    start = time.monotonic()
    omni.run_omni_scenarios()
    child = child_source(omni, saved)
    assert child.exists() and digest(child) == expected
    assert not staged.exists()
    child_root = child.parent.parent
    artifacts = {}
    for suffix in ('*.man', '*.sol', '*.run'):
        files = sorted((child_root / 'wepp/runs').glob(suffix))
        assert files, suffix
        artifacts[suffix] = {'count': len(files), 'sample': files[0].name,
                             'sha256': digest(files[0]),
                             'first_line': files[0].read_text().splitlines()[0]}
    report = omni.scenarios_report()
    assert not report.empty
    result['stages'].append({'stage': stage, 'seconds': time.monotonic()-start,
                             'child_sha256': digest(child), 'artifacts': artifacts,
                             'report_rows': len(report), 'report_columns': list(report.columns)})
    record()
result['status'] = 'passed'
record()
print(json.dumps(result), flush=True)
