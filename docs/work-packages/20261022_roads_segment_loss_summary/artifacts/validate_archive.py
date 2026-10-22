"""Canonical filesystem archive/restore of corrected UM1, with isolated job callbacks."""
from contextlib import nullcontext
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import zipfile

from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq

source = Path('/workdir/wepppy/tests/wepp/interchange/fixtures/roads-accounting-scratch/um1-restored')
runid = 'roads-segment-summary-validation'
restored = Path('/wc1/runs/ro')/runid
assert not restored.exists(), 'Use a fresh restore destination'
paths = ['wepp/roads/output/interchange/'+name for name in
         ['roads_segment_loss_summary.parquet', 'H.pass.parquet', 'H.wat.parquet']]
paths.append('wepp/roads/segments/roads.segment.pass.manifest.json')
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
before = {path: digest(source/path) for path in paths}
runtime = ArchiveRuntime(get_current_job=lambda: None, get_wd=lambda _: str(source),
    get_prep_from_runid=lambda _: None, lock_statuses=lambda _: {}, clear_nodb_file_cache=lambda _: [],
    publish_status=lambda *_: None, disk_usage=shutil.disk_usage, zip_file_cls=zipfile.ZipFile,
    project_config_lifecycle_guard=lambda _: nullcontext(), project_config_authority_wd=lambda _: str(source))
archive_rq(runid, 'Isolated Roads segment summary validation', runtime=runtime)
archive = max((source/'archives').glob(runid+'.*.zip'), key=lambda p:p.stat().st_mtime_ns)
(restored/'archives').mkdir(parents=True)
shutil.copy2(archive, restored/'archives'/archive.name)
restore_runtime = replace(runtime, get_wd=lambda _: str(restored), project_config_authority_wd=lambda _: str(restored))
restore_archive_rq(runid, archive.name, runtime=restore_runtime)
assert all(digest(restored/path) == value for path,value in before.items())
mode = lambda path: oct(stat.S_IMODE(path.stat().st_mode))
assert all(mode(source/path) == mode(restored/path) for path in paths)
result = {'archive_helper':'wepppy.rq.project_rq_archive', 'source':str(source), 'restored':str(restored),
    'archive_sha256':digest(archive), 'verified_sources':before, 'uid':os.getuid(), 'gid':os.getgid(),
    'summary_mode':mode(restored/paths[0]), 'runtime_callbacks':'isolated job/status/locks/cache; real filesystem implementation'}
Path('/tmp/roads-segment-archive-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
