import os,sys
import pytest
if sys.argv[1]=='aligned':os.environ['VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT']='/tmp'
print('RETENTION_ENV', {k:os.environ.get(k) for k in ['VECTOR_UPLOAD_RUN_FILESYSTEM_ID','VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT']},flush=True)
raise SystemExit(pytest.main(['tests/nodb/mods/test_omni.py::test_omni_clone_links_directory_shared_inputs','-q','--tb=short']))
