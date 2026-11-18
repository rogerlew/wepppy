from pathlib import Path
import subprocess
import sys
import os
import shlex
sys.path.insert(0, '/home/workdir/wepppy-roads-code-quality')
from tools.wctl2.checkout_identity import checked_test_command
root = Path(os.environ.get('ROADS_TEST_CHECKOUT', '/home/workdir/wepppy-roads-code-quality'))
out = Path('/tmp/roads-refactor-validation')
out.mkdir(exist_ok=True)
selection = sys.argv[1]
output_label=os.environ.get('ROADS_OUTPUT_LABEL','')
log_name=selection+('-'+output_label if output_label else '')
native_root=out/('native-'+output_label if output_label else 'native-baseline')
if selection in ('focused', 'focused-aligned', 'focused-all'):
    args = [str(p.relative_to(root)) for p in sorted((root / 'tests/nodb/mods').glob('test_roads_*.py'))]
    args += ['tests/rq/test_roads_rq.py', 'tests/microservices/test_rq_engine_roads_routes.py', 'tests/weppcloud/routes/test_roads_bp.py']
    args += [str(p.relative_to(root)) for p in sorted((root / 'tests/wepp/interchange').glob('test_roads_*.py'))]
elif selection == 'fixture-repair':
    args = ['tests/weppcloud/routes/test_roads_bp.py', 'tests/wepp/interchange/test_roads_lifecycle.py']
elif selection == 'diagnostic':
    args = ['tests/weppcloud/routes/test_roads_bp.py::test_upload_geojson_multipart_file', '-p', 'response_diagnostic']
else:
    args = ['tests/roads/test_roads_contracts.py', 'tests/roads/test_roads_matrix.py', '--basetemp='+str(native_root)]
command = 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy:/tmp/roads-refactor-validation MYPY_CACHE_DIR=/tmp/mypy_cache /opt/venv/bin/pytest ' + shlex.join(args + ['--maxfail=1', '-q'])
if selection in ('focused-aligned', 'focused-all', 'fixture-repair'):
    command = command.replace('PYTHONPATH=', 'VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT=/tmp PYTHONPATH=', 1)
if selection == 'focused-all':
    command = command.replace('--maxfail=1', '--maxfail=0')
if selection == 'analysis':
    command = 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python -m tests.roads.roads_analysis '+shlex.quote(str(native_root/'roads_matrix0'))
if selection == 'native' and native_root.exists():
    raise RuntimeError('Refuse to overwrite retained native evidence: '+str(native_root))
with checked_test_command(root, command) as checked:
    invocation = ['wctl', 'run', '--rm', '--no-deps', '--pull', 'never', '-T', '--volume', str(root)+':/workdir/wepppy', '--volume',str(out)+':'+str(out), '--entrypoint','/bin/bash','weppcloud','-lc', checked]
    with (out / (log_name+'.log')).open('w') as log:
        result=subprocess.run(invocation,cwd=root,stdout=log,stderr=subprocess.STDOUT)
print('log:',out / (log_name+'.log'))
print('exit:',result.returncode)
raise SystemExit(result.returncode)
