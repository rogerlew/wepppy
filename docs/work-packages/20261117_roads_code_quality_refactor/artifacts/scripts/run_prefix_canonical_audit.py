"""Bounded canonical prefix replay with source and pytest phase receipts."""
import hashlib,json,os,sys
from pathlib import Path
import pytest
out=Path('/tmp/roads-refactor-validation')
label=sys.argv[1]
modules=json.loads((out/'canonical-prefix-sensitive-modules.json').read_text())['modules']
source_files=modules+['tests/conftest.py','tests/microservices/conftest.py','pyproject.toml']
def hashes():return {name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in source_files}
class Audit:
    def __init__(self):self.nodeids=[];self.reports=[]
    def pytest_collection_finish(self,session):self.nodeids=[item.nodeid for item in session.items]
    def pytest_runtest_logreport(self,report):
        self.reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'duration':report.duration})
audit=Audit();before=hashes()
environment={k:os.environ.get(k) for k in ['VECTOR_UPLOAD_RUN_FILESYSTEM_ID','VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT']}
print('RETENTION_ENV',environment,flush=True)
status=int(pytest.main(modules+['-q','--maxfail=0','--tb=short','--junitxml='+str(out/(label+'.xml'))],plugins=[audit]))
after=hashes()
receipt={'modules':modules,'source_files':source_files,'environment':environment,'source_sha256_before':before,'source_sha256_after':after,'source_unchanged':before==after,'nodeids':audit.nodeids,'reports':audit.reports,'exitstatus':status}
(out/(label+'.json')).write_text(json.dumps(receipt,indent=2))
assert before==after,'Source changed during canonical prefix qualification'
raise SystemExit(status)
