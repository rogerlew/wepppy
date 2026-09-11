"""Archive/restore a disposable copy of all migrated model records, not the live run."""
import json
import os
from pathlib import Path
import shutil
import uuid
import zipfile
from wepppy.nodb.core import Ron
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.rq.project_rq import archive_rq, restore_archive_rq

runid = 'artifact-observability-archive-'+uuid.uuid4().hex[:8]
wd = Path('/wc1/runs/ar')/runid
wd.mkdir()
Ron(str(wd),'disturbed9002_wbt.cfg')
source = Path('/wc1/runs/ad/addicted-reservist/postfire_debris_flow')
root = wd/'postfire_debris_flow'
shutil.copytree(source,root)
expected = {str(path.relative_to(wd)):p.digest(path) for path in root.rglob('*') if path.is_file()}
print('ARCHIVE_START',json.dumps({'runid':runid,'files':len(expected),'uid':os.getuid(),'gid':os.getgid()}),flush=True)
archive_rq(runid,comment='Artifact observability validation: complete copy of migrated postfire records')
archive = next((wd/'archives').glob('*.zip'))
with zipfile.ZipFile(archive) as zipped:
    assert set(expected).issubset(zipped.namelist())
    assert zipped.testzip() is None
# Test real replacement/restoration of a changed file on the disposable project.
(root/'manifest.json').write_text('changed solely to verify restoration')
restore_archive_rq(runid,archive.name)
assert expected == {str(path.relative_to(wd)):p.digest(path) for path in root.rglob('*') if path.is_file()}
print('ARCHIVE_RESTORE_PASS',json.dumps({'runid':runid,'archive':archive.name,'files_unchanged':len(expected),
                                      'archive_bytes':archive.stat().st_size}),flush=True)
