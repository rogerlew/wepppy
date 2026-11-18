import json,os,sys
from pathlib import Path
import pytest
out=Path('/tmp/roads-refactor-validation')
modules=json.loads((out/'canonical-prefix-sensitive-modules.json').read_text())['modules']
print('RETENTION_ENV',{k:os.environ.get(k) for k in ['VECTOR_UPLOAD_RUN_FILESYSTEM_ID','VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT']},flush=True)
raise SystemExit(pytest.main(modules+['-q','--maxfail=0','--tb=short','--junitxml='+str(out/(sys.argv[1]+'.xml'))]))
