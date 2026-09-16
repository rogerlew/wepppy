"""Canonical archive/restore engine against an isolated module-only copy.

Only the newly created validation directory is restored/replaced. This checks
real zip member selection, integrity and restoration; it is not a live-project
restore or a claim of archive API authorization testing.
"""
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import zipfile

from wepppy.rq.project_rq_archive import ArchiveRuntime,archive_rq,restore_archive_rq


def inventory(root):
    result={}
    for p in root.rglob('*'):
        if p.is_file() and 'archives' not in p.relative_to(root).parts:
            with p.open('rb') as f: result[str(p.relative_to(root))]=hashlib.file_digest(f,'sha256').hexdigest()
    return result


def main():
    source,target,report=map(Path,sys.argv[1:])
    assert target.parent==Path('/wc1/runs/pf') and target.name.startswith('pfdf-archive-validation-')
    assert not target.exists();target.mkdir()
    shutil.copytree(source/'postfire_debris_flow',target/'postfire_debris_flow')
    shutil.copyfile(source/'postfire_debris_flow.nodb',target/'postfire_debris_flow.nodb')
    before=inventory(target)
    runtime=ArchiveRuntime(get_current_job=lambda:None,get_wd=lambda _:str(target),
        get_prep_from_runid=lambda _:SimpleNamespace(clear_archive_job_id=lambda:None),
        lock_statuses=lambda _:{},clear_nodb_file_cache=lambda _:[],publish_status=lambda *_:None,
        disk_usage=shutil.disk_usage,zip_file_cls=zipfile.ZipFile,
        project_config_lifecycle_guard=lambda _:nullcontext(),project_config_authority_wd=lambda _:str(target))
    archive_rq(target.name,'Kf module retention acceptance',runtime=runtime)
    archive=next((target/'archives').glob('*.zip'))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(before)
    restore_archive_rq(target.name,archive.name,runtime=runtime)
    assert inventory(target)==before
    categories={name:sum(bool(predicate(path)) for path in before) for name,predicate in {
        'source_preparation':lambda p:'/source_preparation/' in p,
        'http_bodies':lambda p:p.endswith('.body'),
        'sqlite':lambda p:'.sqlite' in p,
        'valid_masks':lambda p:p.endswith('/valid_mask.tif'),
        'failed_acquisition':lambda p:p.endswith('/native_failure.json'),
        'native_kf':lambda p:p.endswith('/native_kf.tif'),
        'kf_metadata':lambda p:p.endswith('/publisher_metadata.xml'),
        'kf_manifests':lambda p:p.endswith('/kf/manifest.json')}.items()}
    result=dict(source=str(source),isolated_restore=str(target),archive=str(archive),
        exact_restored_files=len(before),categories=categories,sha256=before)
    with report.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True)
    print(json.dumps({k:v for k,v in result.items() if k!='sha256'}))


if __name__=='__main__':main()
