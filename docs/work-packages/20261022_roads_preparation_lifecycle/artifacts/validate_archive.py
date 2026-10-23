"""Canonical archive/restore retains current Roads and visible historical evidence."""
from contextlib import nullcontext
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

source = Path('/wc1/runs/ro/roads-segment-summary-validation')
runid = 'roads-lifecycle-archive-validation'
restored = Path('/wc1/runs/ro')/runid
assert not restored.exists(), 'Use a fresh isolated restore destination'
receipt = lifecycle.require_current(source)
paths = receipt['required_relpaths'] + [str(lifecycle.RECEIPT),
    'wepp/roads/segments/roads.inslope.monotonic.geojson',
    'wepp/roads/segments/roads.segment.pass.manifest.json']
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
before = {path:digest(source/path) for path in paths}
history = [str(path.relative_to(source)) for path in (source/lifecycle.HISTORY).glob('*/wepp/roads/output/roads.current.json')]
assert history
runtime = ArchiveRuntime(get_current_job=lambda: None, get_wd=lambda _: str(source),
    get_prep_from_runid=lambda _: None, lock_statuses=lambda _: {}, clear_nodb_file_cache=lambda _: [],
    publish_status=lambda *_: None, disk_usage=shutil.disk_usage, zip_file_cls=zipfile.ZipFile,
    project_config_lifecycle_guard=lambda _: nullcontext(), project_config_authority_wd=lambda _: str(source))
archive_rq(runid, 'Roads lifecycle isolated validation', runtime=runtime)
archive = max((source/'archives').glob(runid+'.*.zip'),key=lambda p:p.stat().st_mtime_ns)
with zipfile.ZipFile(archive) as handle:
    assert lifecycle.LOCK not in handle.namelist()
(restored/'archives').mkdir(parents=True)
shutil.copy2(archive, restored/'archives'/archive.name)
with lifecycle.operation(restored):
    inode = (restored/lifecycle.LOCK).stat().st_ino
restore_archive_rq(runid, archive.name, runtime=replace(runtime,
    get_wd=lambda _:str(restored), project_config_authority_wd=lambda _:str(restored)))
assert (restored/lifecycle.LOCK).stat().st_ino == inode
assert lifecycle.available(restored)
assert lifecycle.require_current(restored) == receipt
assert all(digest(restored/path)==value for path,value in before.items())
assert all((restored/path).is_file() for path in history)
result = {'source':str(source),'restored':str(restored),'uid':os.getuid(),'gid':os.getgid(),
          'archive_sha256':digest(archive),'resources_verified':before,'history_receipts':history,
          'lock_inode_preserved':True,'lock_excluded_from_archive':True,'restored_current':True,
          'runtime_callbacks':'isolated RQ/status/cache callbacks; canonical real filesystem archive/restore'}
Path('/tmp/roads-lifecycle-archive.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
