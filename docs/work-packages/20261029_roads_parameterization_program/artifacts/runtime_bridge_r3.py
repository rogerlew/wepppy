"""Execute the frozen revision-3 same-soil runtime factorial; no defaults change."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import itertools
import json
import shutil
import subprocess

import continuation as c
import role_boundary_assessment_r3 as role
from wepppy.wepp.soils.utils import WeppSoilUtil

HERE = Path(__file__).resolve().parent
ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/runtime-bridge-r3')
BINARY = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
FACTORS = ('wepp_ui.txt', 'pmetpara.txt', 'snow.txt')


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def declare():
    design_path = HERE / 'runtime-bridge-r3-design.json'
    design = json.loads(design_path.read_text())
    assert design['new_runs'] == 112 and len(design['cases']) == 16
    assert role.digest(BINARY) == design['engine_sha256'] == role.SHA
    legacy = ROOT.parent / 'legacy-soil-control-r3/results.json'
    assert role.digest(legacy) == design['source_results_sha256']
    tasks = []
    for item in design['cases']:
        source = Path(item['source'])
        assert role.digest(source / 'record.json') == item['source_record_sha256']
        old = json.loads((source / 'record.json').read_text())
        assert old['physical_pass'] and old['binary_sha256'] == role.SHA
        assert all(name in old['inputs'] for name in FACTORS)
        for name, sha in old['inputs'].items():
            assert role.digest(source / 'runs' / name) == sha
        for bits in itertools.product((False, True), repeat=3):
            if all(bits):
                continue
            tasks.append(dict(item, lane=''.join(str(int(b)) for b in bits), keep=dict(zip(FACTORS, bits))))
    assert len(tasks) == 112
    ROOT.mkdir(exist_ok=False)
    declaration = dict(tasks=tasks, design_sha256=role.digest(design_path),
                       binary_sha256=role.SHA, script_sha256=role.digest(Path(__file__)),
                       dependencies={name: role.digest(HERE / name) for name in ('continuation.py', 'role_boundary_assessment_r3.py')},
                       baseline_cells=16, new_cells=112,
                       contract='Only declared runtime sidecar removals; every retained input byte exact. All failures retained; no threshold/default/soil changes.')
    dump(ROOT / 'declaration.json', declaration)
    dump(HERE / 'runtime-bridge-r3-declaration.json', declaration)
    shutil.copy2(__file__, ROOT / 'executed-study.py')
    print('Declared112 new cells and16 retained baselines', flush=True)


def execute(task):
    source = Path(task['source'])
    assert role.digest(source / 'record.json') == task['source_record_sha256']
    old = json.loads((source / 'record.json').read_text())
    folder = ROOT / task['lane'] / source.name
    runs, output = folder / 'runs', folder / 'output'
    runs.mkdir(parents=True, exist_ok=False); output.mkdir()
    for name, sha in old['inputs'].items():
        assert role.digest(source / 'runs' / name) == sha
        if task['keep'].get(name, True):
            shutil.copy2(source / 'runs' / name, runs / name)
    shutil.copy2(source / 'runs/p1.sol', runs / 'reference.sol')
    inputs = {name: role.digest(runs / name) for name in old['inputs'] if (runs / name).is_file()}
    removed = {name for name, keep in task['keep'].items() if not keep}
    assert set(old['inputs']) - set(inputs) == removed
    assert all(sha == old['inputs'][name] for name, sha in inputs.items())
    assert role.digest(BINARY) == role.SHA
    case = dict(task['case'])
    if not task['keep']['wepp_ui.txt']:
        case.pop('runtime')
    timeout = False
    with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
        try:
            result = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=stdout, stderr=stderr, timeout=300)
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            timeout, returncode = True, None
    record = dict(case=case, original_case=task['case'], lane=task['lane'], group=task['group'],
                  source_record_sha256=task['source_record_sha256'], binary_sha256=role.SHA,
                  inputs=inputs, outputs={p.name: role.digest(p) for p in output.iterdir()},
                  width_m=old['width_m'], profile_length_m=old['profile_length_m'],
                  returncode=returncode, timed_out=timeout, status='native_failure', physical_pass=False,
                  reference_kg_yr=task['reference_kg_yr'], baseline_kg_yr=old['metrics']['sediment_export_kg_yr'])
    if returncode == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text():
        assert ('FAO Penman-Monteith ET Method Implemented' in (runs / 'stdout').read_text()) == task['keep']['pmetpara.txt']
        record.update(status='completed', metrics=c.b.parse_loss(output / 'H1.loss.dat', old['width_m']),
                      soil_readback=WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes'])
        record['audit'] = c.audit(folder, case, record)
        record['physical_pass'] = record['audit']['physical_pass']
        value, ref = record['metrics']['sediment_export_kg_yr'], record['reference_kg_yr']
        record['within'] = .1 <= value / ref <= 10 if ref > 1 else value <= max(1, 10 * ref)
    dump(folder / 'record.json', record)
    return record


def run():
    declaration = json.loads((ROOT / 'declaration.json').read_text())
    assert role.digest(Path(__file__)) == declaration['script_sha256']
    for name, sha in declaration['dependencies'].items():
        assert role.digest(HERE / name) == sha
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute, declaration['tasks']):
            rows.append(row)
            if len(rows) % 16 == 0:
                dump(ROOT / 'partial-results.json', rows)
                print(len(rows), '/112', flush=True)
    dump(ROOT / 'results.json', rows)
    summary = dict(cases=len(rows), completed=sum(r['status'] == 'completed' for r in rows),
                   physical_pass=sum(r['physical_pass'] for r in rows), results_sha256=role.digest(ROOT / 'results.json'),
                   lanes={lane: {group: dict(cases=len(items := [r for r in rows if r['lane'] == lane and r['group'] == group]),
                                             within=sum(r.get('within', False) for r in items),
                                             physical_pass=sum(r['physical_pass'] for r in items))
                                 for group in ('residual', 'passing_control')} for lane in sorted({r['lane'] for r in rows})})
    dump(ROOT / 'summary.json', summary); dump(HERE / 'runtime-bridge-r3-summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--declare', action='store_true')
    declare() if ap.parse_args().declare else run()
