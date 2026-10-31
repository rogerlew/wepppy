"""Complete the current generated/legacy × hourly/daily diagnostic panel."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

import continuation as c
import role_boundary_assessment_r3 as role
from wepppy.wepp.soils.utils import WeppSoilUtil

HERE = Path(__file__).resolve().parent
PARENT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
ROOT = PARENT / 'soil-hourly-r3'
BINARY = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def signature(inputs):
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()


def record(folder):
    return json.loads((folder / 'record.json').read_text())


def declare():
    legacy_path = PARENT / 'legacy-soil-control-r3/results.json'
    legacy = json.loads(legacy_path.read_text())
    bridge_path = PARENT / 'runtime-bridge-r3/results.json'
    bridge = json.loads(bridge_path.read_text())
    assert len(legacy) == 116 and role.digest(BINARY) == role.SHA
    cache = {}
    for row in bridge:
        if row['lane'] == '011':
            assert row['physical_pass']
            folder = PARENT / 'runtime-bridge-r3/011' / '-'.join(row['original_case'].values())
            cache[signature(row['inputs'])] = folder
    tasks, cells = {}, []
    for old in legacy:
        case = old['case']; name = '-'.join(case.values())
        for soil, source in [('generated', role.MATRIX / 'matrix-v1' / name), ('legacy', PARENT / 'legacy-soil-control-r3/matrix-v1' / name)]:
            original = record(source)
            assert original['physical_pass'] and original['binary_sha256'] == role.SHA
            assert all(n in original['inputs'] for n in ('wepp_ui.txt', 'pmetpara.txt', 'snow.txt'))
            for name2, sha in original['inputs'].items():
                assert role.digest(source / 'runs' / name2) == sha
            for hourly in (True, False):
                expected = {k: v for k, v in original['inputs'].items() if hourly or k != 'wepp_ui.txt'}
                key = signature(expected)
                if hourly:
                    destination, origin = source, 'retained_baseline'
                elif key in cache:
                    destination, origin = cache[key], 'retained_bridge'
                    assert record(destination)['inputs'] == expected
                else:
                    destination, origin = ROOT / 'cases' / key, 'new_unique_input'
                    tasks.setdefault(key, dict(key=key, soil=soil, source=str(source), case=case,
                                               source_record_sha256=role.digest(source / 'record.json'),
                                               expected_inputs=expected, reference_kg_yr=old['reference_kg_yr']))
                cells.append(dict(case=case, original_group=old['group'], soil=soil, hourly=hourly,
                                  lane=soil + ('-on' if hourly else '-off'), source=str(source),
                                  source_record_sha256=role.digest(source / 'record.json'),
                                  destination=str(destination), origin=origin, input_signature=key,
                                  reference_kg_yr=old['reference_kg_yr']))
    assert len(cells) == 464 and len(tasks) == 196
    assert sum(t['soil'] == 'generated' for t in tasks.values()) == 116
    assert sum(cel['origin'] == 'retained_bridge' for cel in cells) == 22
    ROOT.mkdir(exist_ok=False)
    declaration = dict(cells=cells, tasks=list(tasks.values()), new_unique_runs=196,
                       generated_new_runs=116, legacy_new_runs=80, labeled_cells=464,
                       retained_baseline_cells=232, retained_bridge_cells=22,
                       new_run_cell_references=210, new_run_aliases=14,
                       binary_sha256=role.SHA, script_sha256=role.digest(Path(__file__)),
                       dependencies={n: role.digest(HERE / n) for n in ('continuation.py', 'role_boundary_assessment_r3.py')},
                       legacy_results_sha256=role.digest(legacy_path), bridge_results_sha256=role.digest(bridge_path),
                       contract='Remove only wepp_ui.txt. PMET and snow remain present; all soil/climate/geometry/management bytes preserved. Reuse only exact full consumed-input signatures. No production/default/criteria/withheld/UI change.')
    dump(ROOT / 'declaration.json', declaration); dump(HERE / 'soil-hourly-r3-declaration.json', declaration)
    shutil.copy2(__file__, ROOT / 'executed-study.py')
    print('Declared196 unique new runs for464 labeled cells', flush=True)


def execute(task):
    source = Path(task['source']); old = record(source)
    assert role.digest(source / 'record.json') == task['source_record_sha256']
    folder = ROOT / 'cases' / task['key']; runs, output = folder / 'runs', folder / 'output'
    runs.mkdir(parents=True, exist_ok=False); output.mkdir()
    for name, sha in task['expected_inputs'].items():
        assert role.digest(source / 'runs' / name) == sha
        shutil.copy2(source / 'runs' / name, runs / name)
    shutil.copy2(source / 'runs/p1.sol', runs / 'reference.sol')
    assert not (runs / 'wepp_ui.txt').exists() and role.digest(BINARY) == role.SHA
    case = dict(task['case']); case.pop('runtime')
    timed_out = False
    with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as out, (runs / 'stderr').open('w') as err:
        try:
            proc = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=out, stderr=err, timeout=300)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out, code = True, None
    row = dict(case=case, original_case=task['case'], soil=task['soil'], input_signature=task['key'],
               binary_sha256=role.SHA, source_record_sha256=task['source_record_sha256'],
               inputs=task['expected_inputs'], outputs={p.name: role.digest(p) for p in output.iterdir()},
               width_m=old['width_m'], profile_length_m=old['profile_length_m'], returncode=code,
               timed_out=timed_out, status='native_failure', physical_pass=False, reference_kg_yr=task['reference_kg_yr'])
    if code == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text():
        assert 'FAO Penman-Monteith ET Method Implemented' in (runs / 'stdout').read_text()
        row.update(status='completed', metrics=c.b.parse_loss(output / 'H1.loss.dat', old['width_m']),
                   soil_readback=WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes'])
        row['audit'] = c.audit(folder, case, row); row['physical_pass'] = row['audit']['physical_pass']
    dump(folder / 'record.json', row)
    return row


def verify_cell(cell):
    folder, source = Path(cell['destination']), Path(cell['source'])
    assert role.digest(source / 'record.json') == cell['source_record_sha256']
    old, row = record(source), record(folder)
    expected = {n: sha for n, sha in old['inputs'].items() if cell['hourly'] or n != 'wepp_ui.txt'}
    assert row['inputs'] == expected and signature(expected) == cell['input_signature']
    assert row['binary_sha256'] == role.SHA
    for section, subdir in [('inputs', 'runs'), ('outputs', 'output')]:
        for name, sha in row[section].items():
            assert role.digest(folder / subdir / name) == sha
    assert (folder / 'runs/wepp_ui.txt').is_file() == cell['hourly']
    assert (folder / 'runs/pmetpara.txt').is_file() and (folder / 'runs/snow.txt').is_file()
    if row['status'] == 'completed':
        assert c.b.parse_loss(folder / 'output/H1.loss.dat', row['width_m']) == row['metrics']
        # Unique destinations are audited separately to avoid concurrent writes
        # to canonical reader artifacts when labeled cases alias the same deck.
    value, ref = row.get('metrics', {}).get('sediment_export_kg_yr'), cell['reference_kg_yr']
    within = value is not None and (.1 <= value / ref <= 10 if ref > 1 else value <= max(1, 10 * ref))
    return dict(cell, status=row['status'], physical_pass=row['physical_pass'], export_kg_yr=value,
                within=within, record_sha256=role.digest(folder / 'record.json'))


def audit_destination(path):
    folder = Path(path); row = record(folder)
    if row['status'] == 'completed':
        assert c.audit(folder, row['case'], row) == row['audit']
    return row['physical_pass']


def run():
    declaration = json.loads((ROOT / 'declaration.json').read_text())
    assert role.digest(Path(__file__)) == declaration['script_sha256']
    for name, sha in declaration['dependencies'].items():assert role.digest(HERE / name) == sha
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute, declaration['tasks']):
            rows.append(row)
            if len(rows) % 20 == 0:print(len(rows), '/196', flush=True)
    dump(ROOT / 'results.json', rows)
    print('Native executions complete', flush=True)


def verify():
    declaration = json.loads((ROOT / 'declaration.json').read_text())
    assert role.digest(ROOT / 'executed-study.py') == declaration['script_sha256']
    paths = sorted({x['destination'] for x in declaration['cells']})
    with ProcessPoolExecutor(max_workers=4) as pool:
        passed = list(pool.map(audit_destination, paths))
        cells = list(pool.map(verify_cell, declaration['cells']))
    groups = {}
    for group in sorted({r['original_group'] for r in cells}):
        groups[group] = {lane: dict(cases=len(items := [r for r in cells if r['original_group'] == group and r['lane'] == lane]),
                                   physical_pass=sum(r['physical_pass'] for r in items), within=sum(r['within'] for r in items))
                         for lane in sorted({r['lane'] for r in cells})}
    report = dict(cells=464, unique_destinations=len(paths), unique_destination_physical_pass=sum(passed),
                  labeled_physical_pass=sum(r['physical_pass'] for r in cells), new_unique_runs=196,
                  recorded_hashes_verified=True, native_audits_and_scores_recomputed=True, groups=groups, rows=cells,
                  declaration_sha256=role.digest(ROOT / 'declaration.json'), results_sha256=role.digest(ROOT / 'results.json'))
    dump(HERE / 'soil-hourly-r3-analysis.json', report)
    dump(ROOT / 'analysis.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('action', choices=('declare', 'run', 'verify'))
    {'declare': declare, 'run': run, 'verify': verify}[ap.parse_args().action]()
