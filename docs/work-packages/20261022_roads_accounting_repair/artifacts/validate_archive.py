"""Exercise existing archive/restore filesystem code on isolated corrected UM1.

Job, status, lock and cache callbacks are isolated; archive writing, restoration,
permission handling and corrected-report admission use the real implementations.
"""
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
from wepppy.wepp.interchange.roads_accounting import LEDGER, accounting_source, load
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport

base = Path('/workdir/wepppy/tests/wepp/interchange/fixtures/roads-accounting-scratch')
source, restored = base/'um1', base/'um1-restored'
assert not restored.exists(), 'Use a fresh restore destination'
ledger = load(source)
paths = set(ledger['inputs']) | set(ledger['canonical_pass']) | set(ledger['products']) | {str(LEDGER)}
hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
before = {path: hash_file(source/path) for path in paths}
runtime = ArchiveRuntime(get_current_job=lambda: None, get_wd=lambda _: str(source),
    get_prep_from_runid=lambda _: None, lock_statuses=lambda _: {}, clear_nodb_file_cache=lambda _: [],
    publish_status=lambda *_: None, disk_usage=shutil.disk_usage, zip_file_cls=zipfile.ZipFile,
    project_config_lifecycle_guard=lambda _: nullcontext(), project_config_authority_wd=lambda _: str(source))
archive_rq('roads-accounting-validation', 'Isolated Roads accounting validation', runtime=runtime)
archive = max((source/'archives').glob('roads-accounting-validation.*.zip'), key=lambda p:p.stat().st_mtime_ns)
(restored/'archives').mkdir(parents=True)
shutil.copy2(archive, restored/'archives'/archive.name)
restored_runtime = replace(runtime, get_wd=lambda _: str(restored), project_config_authority_wd=lambda _: str(restored))
restore_archive_rq('roads-accounting-validation', archive.name, runtime=restored_runtime)
assert all(hash_file(restored/path) == digest for path,digest in before.items())
accounting_source(restored)
report = HillslopeWatbalReport(restored, output_scope='roads')
result = {'archive_helper':'wepppy.rq.project_rq_archive', 'source':str(source), 'restored':str(restored),
    'archive_sha256':hash_file(archive), 'verified_lineage_files':len(paths), 'uid':os.getuid(),
    'gid':os.getgid(), 'restored_ledger_mode':oct(stat.S_IMODE((restored/LEDGER).stat().st_mode)),
    'source_ledger_mode':oct(stat.S_IMODE((source/LEDGER).stat().st_mode)),
    'report_area_m2':report.wsarea, 'report_cache_status':report.cache_status,
    'runtime_callbacks':'isolated job/status/locks/cache; real filesystem implementation'}
assert result['restored_ledger_mode'] == result['source_ledger_mode']
(base/'archive-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
