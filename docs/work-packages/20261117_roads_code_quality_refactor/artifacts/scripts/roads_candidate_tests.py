from pathlib import Path
import subprocess,sys,shlex,os
root=Path(os.environ.get('ROADS_TEST_CHECKOUT','/home/workdir/wepppy-roads-code-quality'))
sys.path.insert(0,str(root))
from tools.wctl2.checkout_identity import checked_test_command
out=Path('/tmp/roads-refactor-validation');out.mkdir(exist_ok=True)
label=sys.argv[1];args=sys.argv[2:]
command='cd /workdir/wepppy && VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT=/tmp PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/pytest '+shlex.join(args)
with checked_test_command(root,command) as checked:
 invocation=['wctl','run','--rm','--no-deps','--pull','never','-T','--volume','/home/workdir/wepppy/.git:/home/workdir/wepppy/.git:ro','--volume',str(root)+':/workdir/wepppy','--volume',str(out)+':'+str(out),'--entrypoint','/bin/bash','weppcloud','-lc',checked]
 with (out/(label+'.log')).open('w') as log:
  result=subprocess.run(invocation,cwd=root,stdout=log,stderr=subprocess.STDOUT)
print((out/(label+'.log')).read_text()[-5000:]);raise SystemExit(result.returncode)
