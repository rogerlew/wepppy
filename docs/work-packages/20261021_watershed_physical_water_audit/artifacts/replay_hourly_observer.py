"""Require hill scientific parity before interpreting infiltration probes."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
BIN=ROOT/'hourly-observer-source/src/wepp_hill'

def execute(task):
    name,mode=task;base=ROOT/'release-matrix'/name;dest=ROOT/'hourly-observer'/mode/name
    shutil.copytree(base/'runs',dest/'runs');(dest/'output').mkdir()
    if mode=='on':(dest/'runs/water_audit.on').touch()
    with (dest/'runs/p1.run').open('rb') as inp,(dest/'stdout').open('wb') as out,(dest/'stderr').open('wb') as err:
        p=subprocess.run([str(BIN)],stdin=inp,stdout=out,stderr=err,cwd=dest/'runs',timeout=1800)
    success=p.returncode==0 and 'SIMULATION SUCCESSFULLY' in (dest/'stdout').read_text(errors='replace')
    if mode=='on':assert (dest/'runs/water_audit_hourly.txt').stat().st_size>0
    differences=[p.name for p in (dest/'output').glob('H1.*') if p.read_bytes()!=(base/'output'/p.name).read_bytes()]
    r=dict(case=name,mode=mode,success=success,differences=differences,binary_sha256=hashlib.sha256(BIN.read_bytes()).hexdigest())
    (dest/'parity.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True);return r
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:r=list(pool.map(execute,[(n,m) for n in ['hourly-single','hourly-upper60','hourly-three'] for m in ['off','on']]))
    (ROOT/'hourly-observer/parity.json').write_text(json.dumps(r,indent=2)+'\n')
    if not all(x['success'] and not x['differences'] for x in r):raise SystemExit(1)
