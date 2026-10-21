"""Move the same hillslope from top to side; preserve climate/geometry/PASS."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
from replay_cases import BIN,PRIOR
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
def execute(mode):
    base=ROOT/'networks'/f'{mode}-short';root=ROOT/'networks'/f'{mode}-side'
    shutil.copytree(base/'runs',root/'runs');shutil.copytree(base/'output',root/'output')
    (root/'runs/pw0.str').write_text('99.1\n2 1 0 0 0 0 0 0 0 0\n')
    (root/'input_manifest.json').write_text(json.dumps(PRIOR.manifest(root/'runs'),indent=2)+'\n')
    with (root/'runs/pw0.run').open('rb') as inp,(root/'pw0.run.stdout').open('wb') as out,(root/'pw0.run.stderr').open('wb') as err:
        p=subprocess.run([str(BIN)],cwd=root/'runs',stdin=inp,stdout=out,stderr=err,timeout=1800)
    success=p.returncode==0 and 'SIMULATION SUCCESSFULLY' in (root/'pw0.run.stdout').read_text(errors='replace')
    r=dict(case=root.name,success=success,returncode=p.returncode,paired_hillslope_source=str(base),outputs=PRIOR.manifest(root/'output'))
    (root/'execution.json').write_text(json.dumps(r,indent=2)+'\n');print(root.name,success,flush=True)
    assert success
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(execute,['daily','hourly']))
