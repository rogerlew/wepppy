"""Complete the predeclared generated-soil hydraulic factorial on revision 4."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

import continuation as c
import road_pore_screen_r3 as pore
import audit_particle_closure as particles
from wepppy.wepp.soils.utils import WeppSoilUtil

HERE = Path(__file__).resolve().parent
PARENT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
FROZEN = PARENT / 'param-sign-u12-combined'
ROOT = PARENT / 'combined-hydraulics-r4-v2'
BINARY = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
SHA = '2a3f9f2b9efd202365c6ef27222bc9f4836918bd16e865c1e3cd54b14c297b48'
KEYS = ('climate', 'soil', 'design', 'surface', 'traffic')
LANES = ('baseline', 'fill_fixed', 'buffer_cap', 'both')
DEPENDENCIES = ('road_pore_screen_r3.py', 'continuation.py',
                'audit_particle_closure.py', 'role_boundary_assessment_r3.py')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def key(case):
    return tuple(case[k] for k in KEYS)


def verify_files(folder, row):
    for section, subdir in [('inputs', 'runs'), ('auxiliary_inputs', 'runs'),
                            ('reused_execution_logs', 'runs'), ('outputs', 'output')]:
        for name, digest in row.get(section, {}).items():
            assert sha(folder / subdir / name) == digest, (folder, name)


def effective_dependencies():
    """Bind dynamically loaded audit helpers and the actual native reader package."""
    import importlib
    import types
    import wepppyo3
    modules = [c, pore, particles, wepppyo3]
    modules.extend(importlib.import_module(n) for n in (
        'wepppy.wepp.soils.utils', 'wepppy.wepp.interchange.hill_element_interchange',
        'wepppy.wepp.interchange.hill_wat_interchange',
        'wepppy.wepp.interchange.hill_ebe_interchange'))
    seen, files = set(), {}
    repo = Path('/workdir/wepppy').resolve()
    while modules:
        module = modules.pop()
        if id(module) in seen:
            continue
        seen.add(id(module))
        name = getattr(module, '__file__', None)
        if not name:
            continue
        path = Path(name).resolve()
        if not (path.is_relative_to(repo) or module.__name__.startswith('wepppyo3')):
            continue
        files[str(path)] = sha(path)
        modules.extend(v for v in vars(module).values() if isinstance(v, types.ModuleType))
    # Readers import their Rust entry points lazily; bind their owned packages too.
    roots = (repo / 'wepppy/wepp/interchange', repo / 'wepppy/wepp/soils/utils',
             Path(wepppyo3.__file__).resolve().parent)
    for root in roots:
        for path in root.rglob('*'):
            if path.is_file() and path.suffix in ('.py', '.so'):
                files[str(path.resolve())] = sha(path)
    manifest = c.BATCH / 'inputs/manifest.json' 
    files[str(manifest.resolve())] = sha(manifest)
    return files


def declare():
    assert sha(BINARY) == SHA
    panel_path = PARENT / 'legacy-soil-control-r3/results.json'
    panel = json.loads(panel_path.read_text())
    assert len(panel) == len({key(r['case']) for r in panel}) == 116
    roads = {key(r['case']): r for r in json.loads((FROZEN / 'roads-results.json').read_text())}
    downstream = {(key(r['case']), r['case']['variant']): r
                  for r in json.loads((FROZEN / 'downstream-results.json').read_text())}
    assert len(roads) == 840 and len(downstream) == 348
    ROOT.mkdir(exist_ok=False)
    tasks = []
    for selected in panel:
        k = key(selected['case'])
        assert k[1] in {'1718465', '2711184', '2711250', '1718510', '1856573', '53949', '1718494'}
        base = roads[k]
        for lane in LANES:
            old = base if lane == 'baseline' else downstream[(k, lane)]
            source = Path(old['folder'])
            assert old['binary_sha256'] == SHA and old['physical_pass']
            assert old['soil_readback'][0] == base['soil_readback'][0]
            verify_files(source, old)
            for road_on in (False, True):
                label = ('road_on_' if road_on else 'road_off_') + lane
                folder = ROOT / 'cases' / label / '-'.join(k)
                runs, output = folder / 'runs', folder / 'output'
                runs.mkdir(parents=True, exist_ok=False)
                output.mkdir()
                for name in old['inputs']:
                    shutil.copy2(source / 'runs' / name, runs / name)
                shutil.copy2(source / 'runs/reference.sol', runs / 'reference.sol')
                auxiliary = {'reference.sol': sha(runs / 'reference.sol')}
                execution_logs = {}
                if not road_on:
                    for name in ('stdout', 'stderr'):
                        shutil.copy2(source / 'runs' / name, runs / name)
                        execution_logs[name] = sha(runs / name)
                source_text = (runs / 'p1.sol').read_text()
                changes = []
                if road_on:
                    text, changes = pore.transform(source_text, old['soil_readback'], 'coupled')
                    (runs / 'p1.sol').write_text(text)
                else:
                    for name in old['outputs']:
                        shutil.copy2(source / 'output' / name, output / name)
                actual = WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes']
                assert actual[1:] == old['soil_readback'][1:]
                for after, before in zip(actual[0]['horizons'], old['soil_readback'][0]['horizons']):
                    if before['solthk'] > 200:
                        assert after == before
                inputs = {name: sha(runs / name) for name in old['inputs']}
                assert {n for n in inputs if inputs[n] != old['inputs'][n]} == ({'p1.sol'} if road_on else set())
                tasks.append(dict(case=dict(old['case'], variant=label), lane=label,
                    road_on=road_on, downstream_lane=lane, group=selected['group'],
                    reference_kg_yr=selected['reference_kg_yr'], folder=str(folder),
                    source=str(source), source_record_sha256=sha(source / 'record.json'),
                    inputs=inputs, auxiliary_inputs=auxiliary, reused_execution_logs=execution_logs,
                    soil_readback=actual, road_changes=changes,
                    width_m=old['width_m'], profile_length_m=old['profile_length_m'],
                    reused_outputs={} if road_on else old['outputs']))
    declaration = dict(tasks=tasks, cells=928, new_runs=464, reused_runs=464,
        binary_sha256=SHA, script_sha256=sha(__file__), source_panel_sha256=sha(panel_path),
        dependencies={n: sha(HERE / n) for n in DEPENDENCIES},
        effective_dependencies=effective_dependencies(),
        plan_sha256=sha(HERE / 'combined-hydraulics-r4-plan.md'),
        status='Predeclared diagnostic factorial; no parameter acceptance')
    assert len(tasks) == 928
    save(ROOT / 'declaration.json', declaration)
    save(HERE / 'combined-hydraulics-r4-declaration.json', declaration)
    shutil.copy2(__file__, ROOT / 'executed-study.py')
    print('Declared 928 cells: 464 exact-U12 reuses, 464 new executions', flush=True)


def execute(task):
    folder = Path(task['folder'])
    if (folder / 'record.json').exists():
        approved = verified_preflight_records()
        assert str(folder) in approved, 'Only the two verified preflight records may be reused'
        assert sha(folder / 'record.json') == approved[str(folder)]
        row = json.loads((folder / 'record.json').read_text())
        assert all(row[k] == v for k, v in task.items())
        assert row['binary_sha256'] == sha(BINARY) == SHA
        verify_files(folder, row)
        if row['completed']:
            assert particles.audit(folder / 'record.json') == json.loads((folder / 'particle-audit.json').read_text())
        return row
    runs, output = folder / 'runs', folder / 'output'
    assert sha(BINARY) == SHA
    verify_files(folder, task)
    source = Path(task['source'])
    assert sha(source / 'record.json') == task['source_record_sha256']
    old = json.loads((source / 'record.json').read_text())
    expected, _ = pore.transform((source / 'runs/p1.sol').read_text(), old['soil_readback'], 'coupled') if task['road_on'] else ((source / 'runs/p1.sol').read_text(), [])
    assert (runs / 'p1.sol').read_text() == expected
    assert WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes'] == task['soil_readback']
    if task['road_on']:
        assert not list(output.iterdir()), 'New simulations require empty output folders'
        with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
            try:
                code = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=stdout,
                                      stderr=stderr, timeout=300).returncode
            except subprocess.TimeoutExpired:
                code = None
        completed = code == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text()
    else:
        code, completed = 0, True
        for name, digest in task['reused_outputs'].items():
            assert sha(output / name) == digest
    row = dict(task, binary_sha256=SHA, returncode=code, completed=completed,
               physical_pass=False, within=False,
               outputs={p.name: sha(p) for p in output.iterdir() if p.is_file()})
    if completed:
        row['metrics'] = c.b.parse_loss(output / 'H1.loss.dat', task['width_m'])
        row['audit'] = c.audit(folder, row['case'], row)
        row['physical_pass'] = row['audit']['physical_pass']
        value, ref = row['metrics']['sediment_export_kg_yr'], task['reference_kg_yr']
        row.update(export_kg_yr=value, within=row['physical_pass'] and
                   (.1 <= value / ref <= 10 if ref > 1 else value <= max(1, 10 * ref)))
    verify_files(folder, row)
    save(folder / 'record.json', row)
    if completed:
        # Separate certificate: no circular record hash and no hidden flag waiver.
        save(folder / 'particle-audit.json', particles.audit(folder / 'record.json'))
    return row


def verified_preflight_records():
    d = json.loads((ROOT / 'declaration.json').read_text())
    p = json.loads((ROOT / 'preflight.json').read_text())
    assert p['script_sha256'] == d['script_sha256'] == sha(__file__)
    assert p['declaration_sha256'] == sha(ROOT / 'declaration.json')
    expected = d['tasks'][:2]
    assert [r['road_on'] for r in expected] == [False, True]
    assert set(p['records']) == {r['folder'] for r in expected}
    for task in expected:
        folder = Path(task['folder'])
        assert sha(folder / 'record.json') == p['records'][str(folder)]
        row = json.loads((folder / 'record.json').read_text())
        assert all(row[k] == v for k, v in task.items())
        assert row['completed'] and row['physical_pass'] and row['returncode'] == 0
        assert row['binary_sha256'] == sha(BINARY) == SHA
        verify_files(folder, row)
        audit = particles.audit(folder / 'record.json')
        assert audit['passed'] and audit == json.loads((folder / 'particle-audit.json').read_text())
    return p['records']


def preflight():
    d = json.loads((ROOT / 'declaration.json').read_text())
    assert d['script_sha256'] == sha(__file__) and d['effective_dependencies'] == effective_dependencies()
    selected = d['tasks'][:2]
    assert [r['road_on'] for r in selected] == [False, True]
    rows = [execute(r) for r in selected]
    assert all(r['completed'] and r['physical_pass'] for r in rows)
    audits = [json.loads((Path(r['folder']) / 'particle-audit.json').read_text()) for r in rows]
    assert all(r['passed'] for r in audits)
    save(ROOT / 'preflight.json', dict(script_sha256=sha(__file__),
        declaration_sha256=sha(ROOT / 'declaration.json'),
        records={r['folder']: sha(Path(r['folder']) / 'record.json') for r in rows},
        reused_and_fresh_actual_audits_pass=True))
    print('Reused and fresh native/runtime/physical/particle preflight passed', flush=True)


def run():
    d = json.loads((ROOT / 'declaration.json').read_text())
    assert sha(__file__) == d['script_sha256'] and sha(BINARY) == d['binary_sha256']
    assert sha(HERE / 'combined-hydraulics-r4-plan.md') == d['plan_sha256']
    for n, digest in d['dependencies'].items():
        assert sha(HERE / n) == digest
    assert effective_dependencies() == d['effective_dependencies']
    assert (ROOT / 'preflight.json').exists(), 'Run reused/fresh preflight before broad execution'
    verified_preflight_records()
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute, d['tasks']):
            rows.append(row)
            if len(rows) % 40 == 0:
                print(len(rows), '/928', flush=True)
    save(ROOT / 'results.json', rows)
    report(rows)


def report(rows):
    import itertools
    import math
    import statistics

    by_case = {}
    for row in rows:
        bits = (int(row['road_on']), int(row['downstream_lane'] in ('fill_fixed', 'both')),
                int(row['downstream_lane'] in ('buffer_cap', 'both')))
        by_case.setdefault(key(row['case']), {})[bits] = row
    assert len(by_case) == 116 and all(len(v) == 8 for v in by_case.values())
    particle_by_folder = {}
    for path in ROOT.glob('cases/*/*/particle-audit.json'):
        particle_by_folder[str(path.parent)] = json.loads(path.read_text())

    def counts(items):
        meaningful = [r for r in items if r['reference_kg_yr'] > 1]
        small = [r for r in items if r['reference_kg_yr'] <= 1]
        controls = [r for r in items if r['group'].endswith('_pass')]
        misses = [r for r in items if not r['group'].endswith('_pass')]
        flags = sum(bool(particle_by_folder.get(r['folder'], {}).get('flags')) for r in items)
        logs = [math.log10(r['export_kg_yr'] / r['reference_kg_yr']) for r in meaningful
                if r['completed'] and r['export_kg_yr'] > 0]
        return dict(cases=len(items), completed=sum(r['completed'] for r in items),
            existing_physical_audit_pass=sum(r['physical_pass'] for r in items),
            meaningful_cases=len(meaningful), meaningful_within=sum(r['within'] for r in meaningful),
            small_cases=len(small), small_within=sum(r['within'] for r in small),
            original_misses=len(misses), recovered_original_misses=sum(r['within'] for r in misses),
            passing_controls=len(controls), control_regressions=sum(not r['within'] for r in controls),
            strict_particle_flagged_cases=flags,
            zero_export_meaningful=sum(r['completed'] and r['export_kg_yr'] == 0 for r in meaningful),
            mean_positive_meaningful_log10_ratio=statistics.mean(logs) if logs else None,
            reviewed_physical_acceptance='pending independent review; flags require exact applicability or new explanation')

    def vector(row):
        values = {n: row['metrics'][n] for n in ('sediment_export_kg_yr', 'runoff_mm_yr')}
        for i, role_name in enumerate(('road', 'fill', 'buffer')):
            for n in ('boundary_kg_yr', 'net_kg_yr'):
                values[role_name + '_' + n] = row['audit']['sediment']['ofes'][i][n]
            for n in ('surface_out_m3_yr', 'lateral_out_m3_yr', 'deep_percolation_m3_yr'):
                values[role_name + '_' + n] = row['audit']['water']['ofes'][i][n]
        return values

    groups, strata = {}, {}
    for lane in sorted({r['lane'] for r in rows}):
        items = [r for r in rows if r['lane'] == lane]
        groups[lane] = counts(items)
        strata[lane] = {field: {value: counts([r for r in items if r['case'][field] == value])
                        for value in sorted({r['case'][field] for r in items})} for field in KEYS}
        strata[lane]['original_group'] = {value: counts([r for r in items if r['group'] == value])
                                         for value in sorted({r['group'] for r in items})}
    contrasts, paired = [], []
    factors = ('road_coupled', 'fill_fixed', 'buffer_cap')
    for k, cells in sorted(by_case.items()):
        base = cells[(0, 0, 0)]
        paired.append(dict(case=dict(zip(KEYS, k)), reference_kg_yr=base['reference_kg_yr'],
            group=base['group'], cells={r['lane']: dict(within=r['within'], physical_audit=r['physical_pass'],
            completed=r['completed'], values=vector(r) if r['completed'] else None,
            strict_particle_flags=particle_by_folder.get(r['folder'], {}).get('flags', []))
            for r in cells.values()}))
        # Finite differences in original units; every background configuration retained.
        for size in (1, 2, 3):
            for active in itertools.combinations(range(3), size):
                rest = [i for i in range(3) if i not in active]
                for background in itertools.product((0, 1), repeat=len(rest)):
                    terms = []
                    for states in itertools.product((0, 1), repeat=size):
                        bits = [0, 0, 0]
                        for i, value in zip(rest, background): bits[i] = value
                        for i, value in zip(active, states): bits[i] = value
                        terms.append(((-1) ** (size - sum(states)), cells[tuple(bits)]))
                    complete = all(r['completed'] for _, r in terms)
                    values = None
                    if complete:
                        vectors = [(sign, vector(r)) for sign, r in terms]
                        values = {n: sum(sign * v[n] for sign, v in vectors) for n in vectors[0][1]}
                    contrasts.append(dict(case=dict(zip(KEYS, k)), factors=[factors[i] for i in active],
                        background={factors[i]: value for i, value in zip(rest, background)},
                        complete=complete, differences=values))
    save(ROOT / 'paired-cells.json', paired)
    save(ROOT / 'continuous-contrasts.json', contrasts)
    pa = list(particle_by_folder.values())
    summary = dict(cells=len(rows), groups=groups, strata=strata,
        particle_events=sum(r['events'] for r in pa),
        strict_particle_flagged_events=sum(len(r['flags']) for r in pa),
        particle_flags=[r for r in pa if r['flags']],
        acceptance='No candidate accepted. Every combination must retain all20controls; particle findings require review. Coupled road factor cannot separate pore from K causality.',
        results_sha256=sha(ROOT / 'results.json'), paired_cells_sha256=sha(ROOT / 'paired-cells.json'),
        continuous_contrasts_sha256=sha(ROOT / 'continuous-contrasts.json'))
    save(ROOT / 'summary.json', summary)
    save(HERE / 'combined-hydraulics-r4-summary.json', summary)
    print(json.dumps({'groups': groups, 'strict_particle_flagged_events': summary['strict_particle_flagged_events']}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('declare', 'preflight', 'run'))
    action = parser.parse_args().action
    {'declare': declare, 'preflight': preflight, 'run': run}[action]()
