"""Exact revision-4 whole-legacy-soil anchors; no format or parameter edits."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import shutil
import subprocess

import combined_hydraulics_r4 as common

HERE = Path(__file__).resolve().parent
ROOT = common.PARENT / 'legacy-soil-anchors-r4'
PRIOR = common.PARENT / 'legacy-soil-control-r3'
BINARY, SHA = common.BINARY, common.SHA
sha, save = common.sha, common.save


def declare():
    assert sha(BINARY) == SHA
    rows = json.loads((PRIOR / 'results.json').read_text())
    modern = {common.key(r['case']): r for r in json.loads((common.FROZEN / 'roads-results.json').read_text())}
    assert len(rows) == 116
    ROOT.mkdir(exist_ok=False)
    tasks = []
    for old in rows:
        name = '-'.join(old['case'].values())
        source = PRIOR / 'matrix-v1' / name
        m = modern[common.key(old['case'])]
        assert old['physical_pass'] and m['binary_sha256'] == SHA
        common.verify_files(source, old)
        assert set(old['inputs']) == set(m['inputs'])
        assert {n for n in old['inputs'] if old['inputs'][n] != m['inputs'][n]} == {'p1.sol'}
        folder = ROOT / 'cases' / name
        runs = folder / 'runs'
        runs.mkdir(parents=True, exist_ok=False)
        (folder / 'output').mkdir()
        for n in old['inputs']:
            shutil.copy2(source / 'runs' / n, runs / n)
        shutil.copy2(source / 'runs/reference.sol', runs / 'reference.sol')
        tasks.append(dict(case=old['case'], group=old['group'], source=str(source),
            source_record_sha256=sha(source / 'record.json'), source_outputs=old['outputs'],
            modern_source=m['folder'], modern_record_sha256=sha(Path(m['folder']) / 'record.json'),
            folder=str(folder), inputs=old['inputs'], auxiliary_inputs={'reference.sol': sha(runs / 'reference.sol')},
            soil_readback=old['soil_readback'], width_m=old['width_m'], profile_length_m=old['profile_length_m'],
            reference_kg_yr=old['reference_kg_yr'], prior_export_kg_yr=old['metrics']['sediment_export_kg_yr']))
    declaration = dict(tasks=tasks, cases=116, binary_sha256=SHA, script_sha256=sha(__file__),
        common_script_sha256=sha(common.__file__), effective_dependencies=common.effective_dependencies(),
        plan_sha256=sha(HERE / 'event-supply-retention-r4-plan.md'),
        source_panel_sha256=sha(PRIOR / 'results.json'),
        scope='Whole legacy soil rebaseline only. Every nonsoil input matches modern U12. No mixed-role substitution, parameter edits or withheld materials.')
    save(ROOT / 'declaration.json', declaration)
    save(HERE / 'legacy-soil-anchors-r4-declaration.json', declaration)
    shutil.copy2(__file__, ROOT / 'executed-study.py')
    print('Declared116 exact input copies; only soil differs from matched modern U12', flush=True)


def check_declaration():
    d = json.loads((ROOT / 'declaration.json').read_text())
    assert d['script_sha256'] == sha(__file__)
    assert d['common_script_sha256'] == sha(common.__file__)
    assert d['effective_dependencies'] == common.effective_dependencies()
    assert d['plan_sha256'] == sha(HERE / 'event-supply-retention-r4-plan.md')
    assert sha(BINARY) == d['binary_sha256'] == SHA
    return d


def execute(task):
    assert sha(BINARY) == SHA
    folder = Path(task['folder'])
    runs, output = folder / 'runs', folder / 'output'
    assert not list(output.iterdir()) and not (folder / 'record.json').exists()
    common.verify_files(folder, task)
    assert sha(Path(task['source']) / 'record.json') == task['source_record_sha256']
    assert sha(Path(task['modern_source']) / 'record.json') == task['modern_record_sha256']
    with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
        try:
            code = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=stdout,
                                  stderr=stderr, timeout=300).returncode
        except subprocess.TimeoutExpired:
            code = None
    completed = code == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text()
    row = dict(task, binary_sha256=SHA, returncode=code, completed=completed, physical_pass=False,
        outputs={p.name: sha(p) for p in output.iterdir() if p.is_file()},
        execution_logs={n: sha(runs / n) for n in ('stdout', 'stderr')})
    if completed:
        row['metrics'] = common.c.b.parse_loss(output / 'H1.loss.dat', row['width_m'])
        row['audit'] = common.c.audit(folder, row['case'], row)
        row['physical_pass'] = row['audit']['physical_pass']
        value, ref = row['metrics']['sediment_export_kg_yr'], row['reference_kg_yr']
        row['within'] = row['physical_pass'] and (.1 <= value / ref <= 10 if ref > 1 else value <= max(1, 10 * ref))
    common.verify_files(folder, row)
    save(folder / 'record.json', row)
    if completed:
        save(folder / 'particle-audit.json', common.particles.audit(folder / 'record.json'))
    return row


def verify(row):
    assert row['binary_sha256'] == sha(BINARY) == SHA
    folder = Path(row['folder'])
    assert json.loads((folder / 'record.json').read_text()) == row
    common.verify_files(folder, row)
    for n, digest in row['execution_logs'].items(): assert sha(folder / 'runs' / n) == digest
    common.c.e.a.validate_runtime(folder, row['case'], row)
    if row['completed']:
        assert common.c.b.parse_loss(folder / 'output/H1.loss.dat', row['width_m']) == row['metrics']
        assert common.c.audit(folder, row['case'], row) == row['audit']
        pa = common.particles.audit(folder / 'record.json')
        assert pa == json.loads((folder / 'particle-audit.json').read_text())
    return row


def preflight():
    d = check_declaration()
    row = execute(d['tasks'][0])
    verify(row)
    assert row['completed'] and row['physical_pass']
    pa = json.loads((Path(row['folder']) / 'particle-audit.json').read_text())
    assert pa['passed']
    save(ROOT / 'preflight.json', dict(declaration_sha256=sha(ROOT / 'declaration.json'),
        record_sha256=sha(Path(row['folder']) / 'record.json'), execution_logs=row['execution_logs']))
    print('Actual legacy anchor preflight passed', flush=True)


def run():
    d = check_declaration()
    p = json.loads((ROOT / 'preflight.json').read_text())
    assert p['declaration_sha256'] == sha(ROOT / 'declaration.json')
    path = Path(d['tasks'][0]['folder']) / 'record.json'
    assert sha(path) == p['record_sha256']
    first = verify(json.loads(path.read_text()))
    assert all(first[k] == v for k, v in d['tasks'][0].items())
    assert first['execution_logs'] == p['execution_logs']
    rows = [first]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute, d['tasks'][1:]):
            rows.append(row)
            if len(rows) % 20 == 0: print(len(rows), '/116', flush=True)
    save(ROOT / 'results.json', rows)
    with ProcessPoolExecutor(max_workers=4) as pool:
        verified = list(pool.map(verify, rows))
    pa = [json.loads(p.read_text()) for p in ROOT.glob('cases/*/particle-audit.json')]
    summary = dict(cases=len(verified), completed=sum(r['completed'] for r in rows),
        physical_pass=sum(r['physical_pass'] for r in rows), within=sum(r.get('within', False) for r in rows),
        strict_particle_flagged_events=sum(len(r['flags']) for r in pa),
        particle_flags=[r for r in pa if r['flags']],
        declaration_sha256=sha(ROOT / 'declaration.json'), results_sha256=sha(ROOT / 'results.json'),
        all_execution_logs_and_runtime_reverified=True, status='Diagnostic whole-profile comparison; no parameter acceptance')
    save(ROOT / 'verification.json', summary)
    save(HERE / 'legacy-soil-anchors-r4-verification.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'particle_flags'}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('declare', 'preflight', 'run'))
    action = parser.parse_args().action
    {'declare': declare, 'preflight': preflight, 'run': run}[action]()
