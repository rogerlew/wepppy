"""Exercise canonical archive/restore I/O on isolated generated climate artifacts."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,shutil,zipfile
from wepppy.rq.project_rq_archive import ArchiveRuntime,archive_rq,restore_archive_rq
O=Path(__file__).resolve().parent
R=O/'archive_fixture';R.mkdir(exist_ok=True)
shutil.copytree(O/'after',R/'climate',dirs_exist_ok=True)
def hashes():return {str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'climate').iterdir() if p.is_file()}
before=hashes();events=[]
runtime=ArchiveRuntime(get_current_job=lambda:None,get_wd=lambda _:str(R),get_prep_from_runid=lambda _:SimpleNamespace(clear_archive_job_id=lambda:None),lock_statuses=lambda _: {},clear_nodb_file_cache=lambda _: [],publish_status=lambda *args:events.append(args),disk_usage=shutil.disk_usage,zip_file_cls=zipfile.ZipFile,project_config_lifecycle_guard=lambda _:nullcontext(),project_config_authority_wd=lambda _:str(R))
archive_rq('daymet-source-audit',None,runtime=runtime)
archive=next((R/'archives').glob('*.zip'))
with zipfile.ZipFile(archive) as z:
 for name,digest in before.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
(R/'climate/daymet_2021-2021.parquet').write_bytes(b'test restore')
restore_archive_rq('daymet-source-audit',archive.name,runtime=runtime)
assert hashes()==before
(O/'archive_verification.json').write_text(json.dumps({'files':before,'all_members_match':True,'restored_bytes_match':True,'runtime_scope':'isolated fixture; orchestration metadata stubs, real canonical archive and restore filesystem I/O'},indent=2)+'\n')
print('PASS: archive members and restored bytes match all generated climate artifacts')
