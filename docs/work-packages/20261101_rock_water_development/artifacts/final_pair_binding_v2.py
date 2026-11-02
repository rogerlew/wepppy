"""Bind an actual committed matched pair; never manufacture future identities."""
import json
from pathlib import Path
import subprocess
import replay_allocation as u


def validate_native_sidecar(metadata, dated, role, commit, branch, digest):
    expected_role = 'watershed' if role == 'wepp' else 'hillslope'
    if (metadata.get('binary_name'), metadata.get('binary_role'), metadata.get('source_branch'), metadata.get('source_commit'), metadata.get('sha256')) != (dated, expected_role, branch, commit, digest):
        raise ValueError('Native sidecar role/name/source/binary mismatch')


def reject_untracked(paths):
    if paths:
        raise ValueError('Uncommitted source/control inputs: ' + ', '.join(paths))


def bind_pair(pair, native):
    pair, native = Path(pair).resolve(), Path(native).resolve()
    receipt_path = pair / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('passed') is not True:
        raise ValueError('Final matched build has not passed')
    commit = subprocess.check_output(['git', '-C', str(native), 'rev-parse', 'HEAD'], text=True).strip()
    if receipt['source_commit'] != commit:
        raise ValueError('Pair does not bind current committed native source')
    untracked = subprocess.check_output(['git','-C',str(native),'ls-files','--others','--exclude-standard','src','fpm-src','tests','tools'],text=True).splitlines()
    reject_untracked(untracked)
    branch = subprocess.check_output(['git','-C',str(native),'branch','--show-current'],text=True).strip()
    subprocess.run(['git', '-C', str(native), 'diff', '--quiet', 'HEAD', '--', 'src', 'fpm-src', 'tests', 'tools'], check=True)
    dependencies = {str(receipt_path): u.sha(receipt_path), str(Path(__file__).resolve()): u.sha(__file__)}
    binaries, runtime, sidecars = {}, {}, {}
    for role, dated in [('wepp', 'wepp_261029'), ('wepp_hill', 'wepp_261029_hill')]:
        binary = pair / 'candidate/src' / role
        identity = receipt['binaries']['candidate/' + role]
        if u.sha(binary) != identity['sha256'] or u.runtime(binary) != identity['libraries']:
            raise ValueError('Retained final binary/runtime drift')
        release = native / 'release' / dated
        sidecar = Path(str(release) + '.json')
        metadata = json.loads(sidecar.read_text())
        sidecars[dated] = metadata
        validate_native_sidecar(metadata, dated, role, commit, branch, identity['sha256'])
        if metadata['source_commit'] != commit or metadata['sha256'] != identity['sha256']:
            raise ValueError('Final sidecar source/binary mismatch')
        for path in (binary, native / 'src' / role, release):
            if u.sha(path) != identity['sha256']:
                raise ValueError('Final pair copies differ')
            dependencies[str(path)] = identity['sha256']
        dependencies[str(sidecar)] = u.sha(sidecar)
        dependencies.update(identity['libraries'])
        binaries[role] = str(binary)
        runtime[role] = identity['libraries']
    return dict(source_commit=commit, dependencies=dependencies, binaries=binaries, runtime=runtime)
