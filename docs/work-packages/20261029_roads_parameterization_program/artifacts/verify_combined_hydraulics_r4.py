"""Fresh artifact/runtime/accounting readback for the completed revision-4 factorial.

Uses the frozen execution declaration; never modifies its records or waives flags.
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
import hashlib

import combined_hydraulics_r4 as study


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(task):
    folder = Path(task['folder'])
    record = folder / 'record.json'
    row = json.loads(record.read_text())
    assert all(row[k] == v for k, v in task.items())
    assert row['binary_sha256'] == sha(study.BINARY) == study.SHA
    study.verify_files(folder, row)
    source = Path(task['source'])
    assert sha(source / 'record.json') == task['source_record_sha256']
    # Logs are required artifacts for BOTH fresh and reused records, including preflight.
    logs = {name: sha(folder / 'runs' / name) for name in ('stdout', 'stderr')}
    study.c.e.a.validate_runtime(folder, row['case'], row)
    completed = 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (folder / 'runs/stdout').read_text()
    assert completed == row['completed']
    particles = None
    if completed:
        assert row['returncode'] == 0
        assert study.c.b.parse_loss(folder / 'output/H1.loss.dat', row['width_m']) == row['metrics']
        assert study.c.audit(folder, row['case'], row) == row['audit']
        particles = study.particles.audit(record)
        assert particles == json.loads((folder / 'particle-audit.json').read_text())
    return dict(folder=str(folder), record_sha256=sha(record), execution_log_sha256=logs,
                actual_runtime_verified=True, physical_pass=row['physical_pass'],
                completed=completed, particle_flags=particles['flags'] if particles else None)


def main():
    root = study.ROOT
    declaration = root / 'declaration.json'
    d = json.loads(declaration.read_text())
    assert sha(root / 'executed-study.py') == d['script_sha256'] == sha(study.__file__)
    assert d['effective_dependencies'] == study.effective_dependencies()
    assert sha(study.HERE / 'combined-hydraulics-r4-plan.md') == d['plan_sha256']
    source_results = json.loads((root / 'results.json').read_text())
    assert len(source_results) == len(d['tasks']) == 928
    assert {r['folder'] for r in source_results} == {r['folder'] for r in d['tasks']}
    for row in source_results:
        assert row == json.loads((Path(row['folder']) / 'record.json').read_text())
    rows = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(verify, d['tasks']):
            rows.append(row)
            if len(rows) % 80 == 0:
                print(len(rows), '/928 freshly verified', flush=True)
    result = dict(declaration_sha256=sha(declaration), results_sha256=sha(root / 'results.json'),
        verifier_sha256=sha(__file__), frozen_script_sha256=d['script_sha256'],
        cells=len(rows), actual_runtime_verified=sum(r['actual_runtime_verified'] for r in rows),
        completed=sum(r['completed'] for r in rows), physical_pass=sum(r['physical_pass'] for r in rows),
        strict_particle_flagged_events=sum(len(r['particle_flags'] or []) for r in rows),
        acceptance='Artifact/runtime/accounting verification only; scientific and parameter acceptance separate',
        rows=rows)
    study.save(root / 'verification.json', result)
    study.save(study.HERE / 'combined-hydraulics-r4-verification.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
