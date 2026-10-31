"""Replay committed-input diagnostic: expected native failure is not model acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent
FIXTURE=HERE/'daily-coupling-fixture'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,default=FIXTURE)
    parser.add_argument('--binary',type=Path,default=Path('/workdir/wepppy/wepp_runner/bin/wepp_261029'))
    args=parser.parse_args()
    fixture=args.fixture
    manifest=json.loads((fixture/'manifest.json').read_text())
    if digest(args.binary)!=manifest['binary_sha256'] or digest(fixture/'inputs.tar.gz')!=manifest['archive_sha256']:
        raise ValueError('Frozen fixture/binary drift')
    args.root.mkdir(parents=True,exist_ok=False)
    results={}
    with tarfile.open(fixture/'inputs.tar.gz','r:gz') as archive:
        for lane,receipt in manifest['cases'].items():
            folder=args.root/lane;runs=folder/'runs';out=folder/'output';runs.mkdir(parents=True);out.mkdir()
            for name,sha in receipt['inputs'].items():
                if Path(name).name!=name:raise ValueError('Nonflat fixture name')
                prefix=lane if manifest.get('archive_layout')=='per_case' or name=='p1.sol' else 'shared'
                member=archive.getmember(f'{prefix}/{name}')
                if not member.isfile():raise ValueError('Nonregular fixture member')
                content=archive.extractfile(member).read()
                if hashlib.sha256(content).hexdigest()!=sha:raise ValueError('Fixture input drift')
                (runs/name).write_bytes(content)
            with (runs/'p1.run').open() as inp,(runs/'stdout').open('w') as stdout,(runs/'stderr').open('w') as stderr:
                proc=subprocess.run([str(args.binary)],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=300)
            actual={p.name:digest(p) for p in out.iterdir()}
            stdout=(runs/'stdout').read_text()
            expected_stop='HOURLY_WATER_UNMET' in stdout if receipt['expected_exit_code']!=0 else 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in stdout
            results[lane]=dict(returncode=proc.returncode,expected_stop=expected_stop,all_outputs_equal=actual==receipt['outputs'],outputs=actual)
            if proc.returncode!=receipt['expected_exit_code'] or not expected_stop or actual!=receipt['outputs']:
                raise ValueError(f'Diagnostic reproduction mismatch: {lane}')
    (args.root/'receipt.json').write_text(json.dumps(dict(cases=results,binary_sha256=digest(args.binary),fixture_manifest_sha256=digest(fixture/'manifest.json'),script_sha256=digest(Path(__file__))),indent=2)+'\n')
    __import__('shutil').copy2(__file__,args.root/'executed-replay.py')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
