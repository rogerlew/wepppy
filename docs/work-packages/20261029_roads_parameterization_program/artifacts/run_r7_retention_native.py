"""Bounded paired retention experiment with exact installed-observer replicas."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import time

import rebaseline_r7_seeds as seeds
import resumption_r7_retention_prepare as prep
import wepppy.soils.ssurgo.retention as retention
from wepppy.soils.ssurgo.retention import load_source_companion

ROOT = prep.BASE / 'retention-native-v1'
SCRATCH = Path('/tmp/roads-retention-native-v1')
PROTOCOL = seeds.ART / 'resumption-r7-retention-native-protocol.md'
REVIEW = seeds.ART / 'resumption-r7-retention-native-observation-review.md'


def dependencies():
    result = seeds.dependencies()
    for path in (Path(__file__), Path(prep.__file__), Path(retention.__file__), PROTOCOL, REVIEW):
        result[str(path.resolve())] = seeds.sha(path)
    return result


def local_inventory(root):
    return {str(path.relative_to(root)): seeds.sha(path)
            for path in sorted(root.rglob('*')) if path.is_file()}


def validate_policy(root, optional):
    proof = load_source_companion(root / 'runs/p1.sol', provenance_root=root)
    assert (proof is not None) == optional
    return proof


def declare(prepared):
    result = seeds.read(prepared / 'preparation-result.json')
    assert result['passed'] and result['native_calls'] == 0
    prep.verify(result['artifact_files'])
    declaration = seeds.read(prepared / 'declaration.json')
    prep.verify(declaration['input_files'])
    reference_files = dict(declaration['input_files'])
    assert result['declaration_sha256'] == seeds.sha(prepared / 'declaration.json')
    readback = seeds.read(prepared / 'case-readback.json')
    assert result['case_readback_sha256'] == seeds.sha(prepared / 'case-readback.json')
    assert set(declaration['cases']) == {'B2', 'B3', 'B4', 'B5'}
    assert shutil.disk_usage('/tmp').free > 5_000_000_000
    ROOT.mkdir(exist_ok=False)
    SCRATCH.mkdir(exist_ok=False)
    shutil.copyfile(__file__, ROOT / 'declared-driver.py')
    shutil.copyfile(PROTOCOL, ROOT / 'declared-protocol.md')
    (SCRATCH / 'bin').mkdir()
    shutil.copyfile(seeds.REPO / 'wepp_runner/bin/wepp_261029', SCRATCH / 'bin/r7')
    (SCRATCH / 'bin/r7').chmod(0o755)
    assert seeds.sha(SCRATCH / 'bin/r7') == seeds.EXPECTED['r7']
    seed_tasks = seeds.read(prep.SEEDS)['tasks']
    tasks = []
    for label, case in declaration['cases'].items():
        original = next(row for row in seed_tasks if row['stratum'] == case['stratum']
                        and row['version'] == 'r7' and row['lane'] == 'modern')
        assert original['case'] == case['case']
        assert original['folder'] == case['source_seed_folder']
        assert original['inputs'] == case['exact_inputs']
        assert original['auxiliary_inputs'] == case['auxiliary_inputs']
        seeds.verify_source(original)
        current_path = Path(original['folder']) / 'record.json'
        current = seeds.read(current_path)
        assert current['case'] == case['case'] and current['inputs'] == case['exact_inputs']
        assert current['binary_sha256'] == seeds.EXPECTED['r7']
        reference_files[str(current_path)] = seeds.sha(current_path)
        assert set(current['outputs']) == seeds.OUTPUTS
        for name, digest in current['outputs'].items():
            output = current_path.parent / 'output' / name
            assert seeds.sha(output) == digest
            reference_files[str(output)] = digest
        for arm in ('default', 'optional'):
            source = prepared / arm / label
            prep.verify(readback['artifacts'][arm][label]['files'])
            validate_policy(source, arm == 'optional')
            for mode in ('ordinary', 'observed'):
                folder = SCRATCH / mode / arm / label
                shutil.copytree(source, folder)
                assert local_inventory(source) == local_inventory(folder)
                runs = folder / 'runs'
                (folder / 'output').mkdir()
                for name, digest in original['inputs'].items():
                    if name == 'p1.sol':
                        continue
                    prep.copy_exclusive(Path(original['folder']) / 'runs' / name, runs / name, digest)
                for name, digest in original['auxiliary_inputs'].items():
                    prep.copy_exclusive(Path(original['folder']) / 'runs' / name, runs / name, digest)
                if mode == 'observed':
                    (runs / 'wepp_observe.on').write_bytes(b'')
                assert not (runs / 'wepp_observe_frost.on').exists()
                validate_policy(folder, arm == 'optional')
                task = dict(original, folder=str(folder), label=label, arm=arm, mode=mode,
                    lane=arm, prior_outputs=current['outputs'], prior_export_kg_yr=current['export_kg_yr'],
                    comparison_baseline='retained fixed-input r7 seed, not fresh default',
                    inputs={p.name: seeds.sha(p) for p in runs.iterdir() if p.name != 'reference.sol'},
                    soil_readback=seeds.WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes'],
                    staged_files=local_inventory(folder),
                    provenance_inputs=['p1.sol.retention.json'] if arm == 'optional' else [])
                # The inherited audit inventories every file in runs. A provenance
                # companion is bound as a workspace input, not a native-consumed field.
                assert set(task['inputs']) == set(original['inputs']) | set(task['provenance_inputs']) | ({'wepp_observe.on'} if mode == 'observed' else set())
                tasks.append(task)
    for label in declaration['cases']:
        for arm in ('default', 'optional'):
            pair = [task for task in tasks if task['label'] == label and task['arm'] == arm]
            assert pair[0]['mode'] == 'ordinary' and pair[1]['mode'] == 'observed'
            assert {k: v for k, v in pair[1]['staged_files'].items() if k != 'runs/wepp_observe.on'} == pair[0]['staged_files']
    seeds.save(ROOT / 'declaration.json', dict(tasks=tasks, dependencies=dependencies(),
        preparation_root=str(prepared), preparation_result_sha256=seeds.sha(prepared / 'preparation-result.json'),
        preparation_files=result['artifact_files'], reference_files=reference_files,
        scratch=str(SCRATCH), uid=os.getuid(), gid=os.getgid(),
        binary_sha256=seeds.EXPECTED['r7'], timeout_seconds=300, workers=1,
        ordinary_calls=8, observer_calls=8, scientific_acceptance=False))
    print('Declared16 calls, no execution', seeds.sha(ROOT / 'declaration.json'), flush=True)


def archive(folder, row):
    destination = ROOT / 'cases' / row['mode'] / row['arm'] / row['label']
    shutil.copytree(folder, destination)
    assert local_inventory(folder) == local_inventory(destination)
    validate_policy(destination, row['arm'] == 'optional')
    row = dict(row, execution_folder=str(folder), retained_folder=str(destination))
    seeds.save(destination / 'retention-receipt.json', row)
    return row


def ordinary(task):
    seeds.ROOT = SCRATCH
    started = time.monotonic()
    row = seeds.execute(task)
    row['elapsed_seconds'] = time.monotonic() - started
    return row


def observed(task, normal):
    folder = Path(task['folder'])
    runs = folder / 'runs'
    seeds.common.verify_files(folder, task)
    validate_policy(folder, task['arm'] == 'optional')
    binary = SCRATCH / 'bin/r7'
    assert seeds.sha(binary) == seeds.EXPECTED['r7']
    started = time.monotonic()
    code = None
    with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
        try:
            code = subprocess.run([str(binary)], cwd=runs, stdin=inp, stdout=stdout,
                                  stderr=stderr, timeout=300).returncode
        except subprocess.TimeoutExpired:
            pass  # Retained explicit failed replica; no retry or timeout increase.
    outputs = {p.name: seeds.sha(p) for p in (folder / 'output').iterdir() if p.is_file()}
    completed = code == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text()
    row = dict(task, returncode=code, completed=completed, outputs=outputs,
        elapsed_seconds=time.monotonic()-started, ordinary_outputs_identical=outputs == normal['outputs'],
        execution_logs={name: seeds.sha(runs / name) for name in ('stdout', 'stderr')})
    trace = runs / 'wepp_observe.log'
    row['trace'] = dict(sha256=seeds.sha(trace), bytes=trace.stat().st_size) if trace.exists() else None
    row['working_directory_expected'] = {p.name for p in runs.iterdir()} == set(task['inputs']) | {'reference.sol', 'stdout', 'stderr', 'wepp_observe.log'}
    seeds.common.verify_files(folder, row)
    validate_policy(folder, task['arm'] == 'optional')
    seeds.save(folder / 'observer-result.json', row)
    return row


def execute_retained(task, normal):
    folder = Path(task['folder'])
    try:
        assert local_inventory(folder) == task['staged_files']
        validate_policy(folder, task['arm'] == 'optional')
        row = ordinary(task) if task['mode'] == 'ordinary' else observed(task, normal)
        for relative, digest in task['staged_files'].items():
            assert seeds.sha(folder / relative) == digest
        validate_policy(folder, task['arm'] == 'optional')
        return archive(folder, row)
    except Exception as exc:
        # Deliberate experiment boundary: preserve partial native/auditor evidence
        # even when parsing, parity or companion validation cannot return a row.
        # Failed-evidence copying does not depend on accepting its provenance.
        destination = ROOT / 'failures' / task['mode'] / task['arm'] / task['label']
        files = local_inventory(folder)
        seeds.save(ROOT / 'failure.json', dict(label=task['label'], arm=task['arm'],
            mode=task['mode'], exception_type=type(exc).__name__, message=str(exc),
            scratch_retained=str(folder), intended_archive=str(destination), files=files))
        shutil.copytree(folder, destination)
        assert local_inventory(destination) == files
        raise


def run():
    path = ROOT / 'declaration.json'
    d = seeds.read(path)
    review = seeds.read(ROOT / 'execution-review.json')
    assert review['declaration_sha256'] == seeds.sha(path) and review['passed'] is True
    prep.verify(review['files'])
    assert d['dependencies'] == dependencies()
    prep.verify(d['preparation_files'])
    prep.verify(d['reference_files'])
    assert seeds.sha(Path(d['preparation_root']) / 'preparation-result.json') == d['preparation_result_sha256']
    assert (os.getuid(), os.getgid()) == (d['uid'], d['gid'])
    assert not (ROOT / 'execution-start.json').exists()
    for task in d['tasks']:
        assert local_inventory(Path(task['folder'])) == task['staged_files']
    seeds.save(ROOT / 'execution-start.json', dict(declaration_sha256=seeds.sha(path), review_sha256=seeds.sha(ROOT / 'execution-review.json')))
    rows, ordinary_rows = [], {}
    for task in sorted(d['tasks'], key=lambda t: (t['mode'] != 'ordinary', t['label'], t['arm'])):
        key = (task['label'], task['arm'])
        row = execute_retained(task, ordinary_rows.get(key))
        if task['mode'] == 'ordinary':
            passed = all(row.get(name) for name in ('completed', 'physical_pass', 'particle_pass', 'pass_completeness'))
            ordinary_rows[key] = row
        else:
            passed = row['completed'] and row['ordinary_outputs_identical'] and row['trace'] is not None and row['working_directory_expected']
        rows.append(row)
        seeds.save(ROOT / 'partial-results.json', rows)
        if not passed:
            seeds.save(ROOT / 'failure.json', dict(label=task['label'], arm=task['arm'],
                mode=task['mode'], reason='Declared native/audit/parity gate failed',
                retained_folder=row['retained_folder']))
            raise ValueError('Retained failed trial; stop before remaining calls')
        print('Completed', task['label'], task['arm'], task['mode'], flush=True)
    assert d['dependencies'] == dependencies()
    prep.verify(d['preparation_files'])
    prep.verify(d['reference_files'])
    assert seeds.sha(SCRATCH / 'bin/r7') == d['binary_sha256']
    seeds.save(ROOT / 'results.json', rows)
    print('16 calls complete; independent initialized-layer and science review required', flush=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action', choices=('declare', 'run'))
    cli.add_argument('--prepared', type=Path, default=prep.BASE / 'retention-preparation-v1')
    args = cli.parse_args()
    declare(args.prepared) if args.action == 'declare' else run()
