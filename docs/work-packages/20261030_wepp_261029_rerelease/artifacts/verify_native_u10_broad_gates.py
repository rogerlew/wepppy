"""Read-only retained-output verification for the completed U10 broad gates."""
import hashlib
import json
import math
from pathlib import Path

RAW = Path('/workdir/wepppy/out/roads-channel-accounting-20261030')
ARTIFACTS = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    provenance = json.loads((RAW / 'U10-provenance.json').read_text())
    binary = provenance['binary_sha256']['wepp']
    assert sha(RAW / 'U10-build/src/wepp') == binary
    matrix = RAW / 'U10-matrix840'
    declaration = json.loads((matrix / 'declaration.json').read_text())
    assert declaration['binary_sha256'] == binary
    assert declaration['script_sha256'] == sha(RAW / 'replay_U10_840.py')
    source = Path(declaration['source'])
    names = declaration['cases']
    assert len(names) == len(set(names)) == 840
    assert set(names) == {p.name for p in source.iterdir() if p.is_dir()}
    assert set(names) == {p.name for p in (matrix / 'matrix-v1').iterdir() if p.is_dir()}
    rows = json.loads((matrix / 'results.json').read_text())
    assert len(rows) == 840
    inputs = outputs = 0
    for name, row in zip(names, rows, strict=True):
        oldfile = source / name / 'record.json'
        if not oldfile.exists():
            oldfile = source / name / 'failure.json'
        old = json.loads(oldfile.read_text())
        folder = matrix / 'matrix-v1' / name
        assert row == json.loads((folder / 'record.json').read_text())
        assert row['case'] == old['case']
        assert row['source_record_sha256'] == sha(oldfile)
        assert row['inputs'] == old['inputs']
        assert row['binary_sha256'] == binary
        assert row['returncode'] == 0 and row['status'] == 'completed'
        assert row['physical_pass'] and row['audit']['physical_pass']
        for filename, expected in row['inputs'].items():
            assert sha(source / name / 'runs' / filename) == expected
            assert sha(folder / 'runs' / filename) == expected
            inputs += 1
        assert set(row['outputs']) == {p.name for p in (folder / 'output').iterdir() if p.is_file()}
        for filename, expected in row['outputs'].items():
            assert sha(folder / 'output' / filename) == expected
            outputs += 1
    references = json.loads((source.parent / 'results.json').read_text())
    key = lambda row: tuple(sorted(row['case'].items()))
    reference = {key(row): row for row in references}
    assert len(reference) == 840
    assert set(reference) == {key(row) for row in rows}
    within = 0
    groups = {'meaningful': {'cases': 0, 'within': 0}, 'small': {'cases': 0, 'within': 0}}
    for row in rows:
        ref = reference[key(row)]['reference_kg_yr']
        value = row['metrics']['sediment_export_kg_yr']
        assert math.isfinite(ref) and ref >= 0
        assert math.isfinite(value) and value >= 0
        passed = (0.1 <= value / ref <= 10) if ref > 1 else value <= max(1, 10 * ref)
        within += passed
        group = groups['meaningful' if ref > 1 else 'small']
        group['cases'] += 1
        group['within'] += passed
    magnitude = json.loads((RAW / 'U10-magnitude-summary.json').read_text())
    assert within == magnitude['within'] == 749
    assert groups == {'meaningful': {'cases': 766, 'within': 719}, 'small': {'cases': 74, 'within': 30}}
    assert magnitude['parameterization_acceptance'] is False

    disturbed_log = (RAW / 'disturbed-U10.log').read_text()
    assert 'WEPP_DISTURBED_BINARY=' + str(RAW / 'U10-build/src/wepp') in disturbed_log
    assert '99 passed, 2 warnings in 505.95s' in disturbed_log
    disturbed = RAW / 'disturbed-U10/disturbed_matrix0/output'
    suffixes = ['element', 'ebe', 'grph', 'loss', 'pass', 'plot', 'soil', 'wat']
    expected = {f'H{i}.{suffix}.dat' for i in range(1, 97) for suffix in suffixes}
    assert {p.name for p in disturbed.iterdir() if p.is_file()} == expected
    manifest = {name: sha(disturbed / name) for name in sorted(expected)}
    (ARTIFACTS / 'U10-disturbed-output-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    evidence = ['U10-matrix840.log', 'disturbed-U10.log', 'U10-magnitude-summary.json',
                'U10-matrix840/declaration.json', 'U10-matrix840/results.json',
                'U10-matrix840/summary.json', 'U10-matrix840/magnitude-scores.json']
    for name in ['U10-matrix840.log', 'disturbed-U10.log', 'U10-magnitude-summary.json']:
        (ARTIFACTS / name).write_bytes((RAW / name).read_bytes())
    receipt = dict(
        review='Independent AI retained-output verification; no simulation rerun',
        binary_sha256=binary, source_commit=provenance['declaration']['source_commit'],
        roads_cases=840, roads_completed=840, roads_physical_pass=840,
        roads_inputs_verified=inputs, roads_outputs_verified=outputs,
        roads_magnitude_within=within, roads_magnitude_groups=groups,
        roads_parameterization_accepted=False,
        disturbed_tests_passed=99, disturbed_simulations=96, disturbed_outputs_retained=len(manifest),
        disturbed_manifest_sha256=sha(ARTIFACTS / 'U10-disturbed-output-manifest.json'),
        evidence_sha256={name: sha(RAW / name) for name in evidence},
        verifier_sha256=sha(Path(__file__)),
        scope='U10 actual dated bytes; full Cedar sign/scientific review remains separate.',
    )
    (ARTIFACTS / 'native-U10-broad-gates.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({name: value for name, value in receipt.items() if name not in ['evidence_sha256']}))


if __name__ == '__main__':
    main()
