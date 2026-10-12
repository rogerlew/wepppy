import json, shutil, tempfile, zipfile
from pathlib import Path
from contextlib import nullcontext
from wepppy.rq.project_rq_archive import ArchiveRuntime, archive_rq, restore_archive_rq
from wepppy.weppcloud.combined_viewer_preparation import digest
from wepppy.weppcloud.utils.portland_collections import portland_runids
run = sorted(portland_runids())[0]
source = Path('/wc1/runs/po') / run
with tempfile.TemporaryDirectory(prefix='pcv-archive-') as directory:
    root = Path(directory) / 'isolated-copy'
    shutil.copytree(source, root)
    before = {str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file()}
    runtime = ArchiveRuntime(get_current_job=lambda:None, get_wd=lambda _:str(root),
        get_prep_from_runid=lambda _:None, lock_statuses=lambda _:{}, clear_nodb_file_cache=lambda _:[],
        publish_status=lambda *args:None, disk_usage=shutil.disk_usage, zip_file_cls=zipfile.ZipFile,
        project_config_lifecycle_guard=lambda _:nullcontext(), project_config_authority_wd=lambda _:str(root))
    archive_rq('pcv-isolated', 'Combined viewer archive proof', runtime=runtime)
    archive = next((root/'archives').glob('*.zip'))
    with zipfile.ZipFile(archive) as z:
        assert set(before) <= set(z.namelist())
    restore_archive_rq('pcv-isolated',archive.name,runtime=runtime)
    after = {str(p.relative_to(root)):digest(p) for p in root.rglob('*') if p.is_file() and 'archives' not in p.relative_to(root).parts}
    assert before == after
    print(json.dumps({'run':run,'files':len(before),'byte_parity':True,
        'method':'actual archive_rq/restore_archive_rq on isolated copy; queue/status/lock adapters isolated',
        'manifest':before['combined-viewer-preparation/manifest.json'],
        'parquet':before['wepp/output/interchange/loss_pw0.hill.parquet']}))
