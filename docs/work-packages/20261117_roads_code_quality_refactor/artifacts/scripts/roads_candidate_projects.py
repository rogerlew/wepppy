from pathlib import Path
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import shlex
sys.path.insert(0, '/home/workdir/wepppy-roads-code-quality')
from tools.wctl2.checkout_identity import checked_test_command
root = Path('/home/workdir/wepppy-roads-code-quality')
out = Path('/tmp/roads-refactor-validation')
label = 'candidate-20261117b'
source_paths = sorted((root/'wepppy/nodb/mods/roads').glob('*.py')) + sorted((root/'tests/roads').glob('*.py'))
source_hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
receipt = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), 'source_sha256': source_hashes}
(out/('candidate-project-source-'+label+'.json')).write_text(json.dumps(receipt, indent=2))


def run(design):
    command = 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy /opt/venv/bin/python /tmp/roads-refactor-validation/candidate_project_parity.py ' + shlex.join([label, '--design', design])
    with checked_test_command(root, command) as checked:
        invocation = ['wctl', 'run', '--rm', '--no-deps', '--pull', 'never', '-T', '--volume', str(root)+':/workdir/wepppy', '--volume', str(out)+':'+str(out), '--entrypoint', '/bin/bash', 'weppcloud', '-lc', checked]
        with (out/('project-'+label+'-'+design+'.log')).open('w') as log:
            result = subprocess.run(invocation, cwd=root, stdout=log, stderr=subprocess.STDOUT)
    print(design, result.returncode, flush=True)
    return result.returncode


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    outcomes = list(pool.map(run, ['inslope_bd', 'inslope_rd', 'outslope_rutted', 'unrutted-positive', 'unrutted-negative']))
assert source_hashes == {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}, 'Candidate source changed during project qualification'
raise SystemExit(int(any(outcomes)))
