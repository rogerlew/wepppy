"""Replay the retained split/unsplit inputs with the exact study executable."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',type=Path,required=True)
args=parser.parse_args()
source=Path(__file__).resolve().parent
repo=source.parents[4]
binary=repo/'wepp_runner/bin/wepp_261026'
manifest=json.loads((source/'manifest.json').read_text())
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if digest(binary)!=manifest['binary_sha256']:raise ValueError('Study binary identity changed')
for name,sha in manifest['inputs'].items():
    if digest(source/name)!=sha:raise ValueError(f'Reproducer input changed: {name}')
args.destination.mkdir(parents=True,exist_ok=False)
for label in ('unsplit','split'):
    runs=args.destination/label/'runs'
    shutil.copytree(source/label/'runs',runs)
    (runs.parent/'output').mkdir()
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as out,(runs/'stderr').open('w') as err:
        subprocess.run([str(binary)],stdin=inp,stdout=out,stderr=err,cwd=runs,timeout=120,check=True)
    if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        raise ValueError(f'Native completion missing: {label}')
    print(label, runs.parent/'output/H1.loss.dat',flush=True)
