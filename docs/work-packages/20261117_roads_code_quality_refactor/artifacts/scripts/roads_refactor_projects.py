from pathlib import Path
import concurrent.futures
import subprocess
import sys
import os
import shlex
sys.path.insert(0,'/home/workdir/wepppy-roads-baseline')
from tools.wctl2.checkout_identity import checked_test_command
root=Path(os.environ.get('ROADS_TEST_CHECKOUT','/home/workdir/wepppy-roads-baseline'))
out=Path('/tmp/roads-refactor-validation')
label=os.environ.get('ROADS_PARITY_LABEL','baseline-20261117a')

def run(design):
    command='cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python /tmp/roads-refactor-validation/project_parity.py '+shlex.join([label,'--design',design])
    with checked_test_command(root,command) as checked:
        invocation=['wctl','run','--rm','--no-deps','--pull','never','-T','--volume',str(root)+':/workdir/wepppy','--volume',str(out)+':'+str(out),'--entrypoint','/bin/bash','weppcloud','-lc',checked]
        with (out/('project-'+label+'-'+design+'.log')).open('w') as log:
            result=subprocess.run(invocation,cwd=root,stdout=log,stderr=subprocess.STDOUT)
    print(design,result.returncode,flush=True)
    return result.returncode

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    outcomes=list(pool.map(run,['inslope_bd','inslope_rd','outslope_rutted','unrutted-positive','unrutted-negative']))
raise SystemExit(int(any(outcomes)))
