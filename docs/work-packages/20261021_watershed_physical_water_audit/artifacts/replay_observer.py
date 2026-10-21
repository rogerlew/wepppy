"""Replay fixed PASS inputs through off/on observational watershed builds."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
ROOT=Path('/workdir/watershed-physical-water-audit-20261021')
BIN=ROOT/'observer-source-v2/src/wepp'
SOURCE_GROUP='release-matrix'
DEST_GROUP='observer-v2'

def hashes(case):
    paths=list((case/'output').glob('*'))+[p for p in (case/'runs').glob('*') if not p.name.startswith('water_audit')]
    return {str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}

def execute(task):
    name,mode=task
    base=ROOT/SOURCE_GROUP/name;dest=ROOT/DEST_GROUP/mode/name
    shutil.copytree(base/'runs',dest/'runs');shutil.copytree(base/'output',dest/'output')
    if mode=='on':(dest/'runs/water_audit.on').touch()
    start=time.monotonic()
    with (dest/'runs/pw0.run').open('rb') as inp,(dest/'stdout').open('wb') as out,(dest/'stderr').open('wb') as err:
        p=subprocess.run([str(BIN)],stdin=inp,stdout=out,stderr=err,cwd=dest/'runs',timeout=1800)
    if mode=='on' and not (dest/'runs/water_audit_channel.txt').is_file():
        raise RuntimeError('Observation hook not reached')
    success=p.returncode==0 and 'SIMULATION SUCCESSFULLY' in (dest/'stdout').read_text(errors='replace')
    bh=hashes(base);dh=hashes(dest)
    result=dict(case=name,mode=mode,success=success,seconds=time.monotonic()-start,binary_sha256=hashlib.sha256(BIN.read_bytes()).hexdigest(),differences=[k for k,v in bh.items() if dh.get(k)!=v],hashes=dh)
    (dest/'parity.json').write_text(json.dumps(result,indent=2)+'\n');print(name,mode,success,result['differences'],flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-group',default='release-matrix');p.add_argument('--dest-group',default='observer-v2');p.add_argument('--cases',nargs='+',default=['daily-upper60','hourly-upper60']);a=p.parse_args()
    SOURCE_GROUP=a.source_group;DEST_GROUP=a.dest_group
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(execute,[(n,m) for n in a.cases for m in ['off','on']]))
    (ROOT/DEST_GROUP/'parity.json').write_text(json.dumps(results,indent=2)+'\n')
    if not all(r['success'] and not r['differences'] for r in results):raise SystemExit(1)
