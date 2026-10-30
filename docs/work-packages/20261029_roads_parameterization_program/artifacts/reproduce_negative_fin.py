"""Replay the pinned native defect without requiring the original project/study."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True,type=Path)
    args=parser.parse_args()
    binary=REPO/'wepp_runner/bin/wepp_261026'
    with zipfile.ZipFile(HERE/'negative-fin-reproducer.zip') as archive:
        manifest=json.loads(archive.read('manifest.json'))
        if digest(binary)!=manifest['binary_sha256']:raise ValueError('Pinned binary drift')
        if set(archive.namelist())!=set(manifest['inputs'])|{'manifest.json'}:
            raise ValueError('Unrecorded fixture member')
        if any(Path(n).name!=n or n in ('.','..') for n in manifest['inputs']):
            raise ValueError('Fixture names must be local basenames')
        args.root.mkdir(parents=True,exist_ok=False)
        runs=args.root/'runs';out=args.root/'output';runs.mkdir();out.mkdir()
        for name,sha in manifest['inputs'].items():
            (runs/name).write_bytes(archive.read(name))
            if digest(runs/name)!=sha:raise ValueError('Fixture input drift')
    with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
        proc=subprocess.run([str(binary)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=180)
    checks={name:(out/name).exists() and digest(out/name)==sha for name,sha in manifest['expected_outputs'].items()}
    guard=(runs/'stdout').read_text().splitlines()[-1].strip()
    report=dict(returncode=proc.returncode,guard=guard,outputs_byte_identical=checks,
                fixture_sha256=digest(HERE/'negative-fin-reproducer.zip'),binary_sha256=digest(binary))
    (args.root/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    if proc.returncode!=manifest['expected_returncode'] or guard!=manifest['expected_guard'] or not all(checks.values()):
        raise ValueError('Expected native defect did not reproduce exactly')
    print('Expected HOURLY_WATER_UNMET reproduced; all seven native files byte-identical.')


if __name__=='__main__':main()
