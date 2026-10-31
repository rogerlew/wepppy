"""Bind completed local U10 gates to the frozen actual dated pair; no promotion."""
import hashlib
import json
import re
from pathlib import Path

RAW = Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
NATIVE = Path('/workdir/wepp-forest-release-20261009')
ARTIFACTS = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    provenance = json.loads((RAW / 'U10-provenance.json').read_text())
    declaration = provenance['declaration']
    for name, expected in declaration['source_sha256'].items():
        assert sha(NATIVE / name) == expected, name
    pair = {}
    sidecars = {}
    for profile, dated in [('wepp', 'wepp_261029'), ('wepp_hill', 'wepp_261029_hill')]:
        expected = provenance['binary_sha256'][profile]
        for path in [NATIVE / 'src' / profile, NATIVE / 'release' / dated,
                     RAW / 'U10-build' / 'src' / profile]:
            assert sha(path) == expected, str(path)
        sidecar = NATIVE / 'release' / (dated + '.json')
        metadata = json.loads(sidecar.read_text())
        assert metadata['source_commit'] == declaration['source_commit']
        assert metadata['sha256'] == expected
        assert metadata['artifact_revision'] == 2
        pair[dated] = expected
        sidecars[sidecar.name] = sha(sidecar)
    preflight = json.loads((ARTIFACTS / 'native-build-preflight.json').read_text())
    installed = Path('/workdir/wepppy/wepp_runner/bin')
    for name, expected in preflight['installed_sha256'].items():
        assert sha(installed / name) == expected, name

    logs = {}
    for name in ['U10-native-tests.log', 'U10-watchlist.log', 'U10-smokes.log',
                 'U10-binary-provenance.log', 'U10-artifact-policy.log']:
        source = RAW / name
        target = ARTIFACTS / name
        target.write_bytes(source.read_bytes())
        logs[name] = sha(target)
    native = (RAW / 'U10-native-tests.log').read_text()
    assert re.search(r'1059 passed, 2 warnings in 615\.74s', native)
    assert 'FAILED ' not in native
    watchlist = (RAW / 'U10-watchlist.log').read_text()
    assert 'summary\tpassed=18\tfailed=0' in watchlist
    cases = [line for line in watchlist.splitlines() if '\tincident=' in line]
    assert len(cases) == 18
    assert all('\trc=0\tsuccess=1\terror_sig=0\ttimeout=0\tyears=[' in line
               for line in cases)
    smokes = (RAW / 'U10-smokes.log').read_text()
    assert smokes.count('rc=0\tsuccess=1\texpected_year=3\tyears=[1 2 3]') == 2
    binary_log = (RAW / 'U10-binary-provenance.log').read_text()
    assert binary_log.count('interpreter=/lib64/ld-linux-x86-64.so.2') == 2
    assert all(value in binary_log for value in pair.values())
    assert 'not found' not in binary_log
    assert 'ablation artifact policy OK' in (RAW / 'U10-artifact-policy.log').read_text()

    receipt = dict(
        source_commit=declaration['source_commit'],
        source_files_verified=len(declaration['source_sha256']),
        provenance_sha256=sha(RAW / 'U10-provenance.json'),
        binary_sha256=pair,
        sidecar_sha256=sidecars,
        logs_sha256=logs,
        gates=dict(native=1059, watchlist=18, paired_smokes=2,
                   provenance='pass', artifact_policy='pass'),
        native_elapsed_seconds=615.74,
        warnings='Two existing tarfile extraction deprecation warnings',
        focused_test_commit='2934a24b8',
        focused_test_sha256=sha(NATIVE / 'tests/test_yalin_stable_capacity.py'),
        installed_original_unchanged=True,
        verifier_sha256=sha(Path(__file__)),
        acceptance='Local actual-byte gates pass; scientific acceptance remains separate. No vendoring.',
    )
    target = ARTIFACTS / 'native-U10-gates.json'
    target.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt['gates']))


if __name__ == '__main__':
    main()
