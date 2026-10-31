"""Frozen role-coefficient and runtime-factor diagnostics; no production changes."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
import argparse
import itertools
import json
import math
import shutil
import subprocess

import continuation as c
import role_boundary_assessment as prior
from wepppy.wepp.soils.utils import WeppSoilUtil

HERE = Path(__file__).resolve().parent
ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031')
LEGACY = ROOT / 'legacy-soil-control-v2'
BINARY = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
FIELDS = ('ki', 'kr', 'shcrit')
ROLES = {'fill': (1,), 'buffer': (2,), 'both': (1, 2)}
FACTORS = ('wepp_ui.txt', 'pmetpara.txt', 'snow.txt')


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def directory(study):
    return ROOT / f'{study}-ablation-v1'


def declare(study):
    old_declaration = json.loads((LEGACY / 'declaration.json').read_text())
    legacy_rows = json.loads((LEGACY / 'results.json').read_text())
    tasks = []
    if study == 'erosion':
        for score in old_declaration['cases']:
            case = score['case']; name = '-'.join(case.values())
            for lane in ROLES:
                tasks.append(dict(case=case, group=prior.classify(score), lane=lane,
                                  source=str(prior.MATRIX / 'matrix-v1' / name),
                                  legacy=str(LEGACY / 'matrix-v1' / name), reference_kg_yr=score['reference_kg_yr']))
        assert len(tasks) == 333
    else:
        unique = {}
        for row in legacy_rows:
            if not row['within']:
                unique.setdefault(tuple(sorted(row['inputs'].items())), row)
        assert len(unique) == 9
        controls = {}
        for row in legacy_rows:
            if row['within'] and row['group'] in ('meaningful_pass', 'small_pass'):
                controls.setdefault(row['case']['climate'], row)
        assert len(controls) == 5
        for row in list(unique.values()) + list(controls.values()):
            case = row['case']; name = '-'.join(case.values())
            for bits in itertools.product((False, True), repeat=3):
                if all(bits):
                    continue
                tasks.append(dict(case=case, group='residual' if not row['within'] else 'passing_control',
                                  lane=''.join(str(int(bit)) for bit in bits),
                                  keep=dict(zip(FACTORS, bits)), source=str(LEGACY / 'matrix-v1' / name),
                                  reference_kg_yr=row['reference_kg_yr']))
        assert len(tasks) == 98
    for task in tasks:
        task['source_record_sha256'] = prior.digest(Path(task['source']) / 'record.json')
    dest = directory(study); dest.mkdir(exist_ok=False)
    declaration = dict(study=study, tasks=tasks, script_sha256=prior.digest(Path(__file__)),
                       dependency_sha256={p: prior.digest(HERE / p) for p in ('continuation.py', 'role_boundary_assessment.py')},
                       binary_sha256=prior.SHA, baseline='Previously verified exact source inputs and output records; no reclassification of earlier failures.',
                       erosion_contract='Replace only ki (kg s/m4), kr (s/m), shcrit (N/m2) in declared fill/buffer OFEs with the corresponding legacy-template values. All generated horizons, 200 mm breaks, restriction data, road settings and hydraulic parameters remain exact. Require byte-identical WAT output.',
                       runtime_contract='Full 2x2x2 factor panel with existing 111 baseline reused: hourly mode, PMET presence, snow presence. PMET absence selects original Penman; snow absence uses rst=0 C, densities100/250 rather than fixture rst=-2 C. Legacy soils and all other consumed inputs remain exact.',
                       limits='Diagnostic anchors only, not physically accepted new defaults. No withheld outcomes, threshold changes or runtime/default adoption. Coefficient effects may interact with generated hydraulics.')
    if study == 'erosion':
        values = {role: {field: [] for field in FIELDS} for role in ('fill', 'buffer')}
        for task in tasks[::3]:
            legacy = json.loads((Path(task['legacy']) / 'record.json').read_text())
            for role, index in (('fill', 1), ('buffer', 2)):
                for field in FIELDS:
                    value = float(legacy['soil_readback'][index][field]); assert math.isfinite(value) and value > 0
                    values[role][field].append(value)
        declaration['anchor_ranges'] = {role: {field: [min(v), max(v)] for field, v in fields.items()} for role, fields in values.items()}
    dump(dest / 'declaration.json', declaration)
    dump(HERE / f'{study}-ablation-v1-declaration.json', declaration)
    shutil.copy2(__file__, dest / 'executed-study.py')
    print(study, len(tasks), 'declared', flush=True)


def execute(pair):
    study, task = pair
    source = Path(task['source']); old = json.loads((source / 'record.json').read_text())
    assert prior.digest(source / 'record.json') == task['source_record_sha256']
    folder = directory(study) / task['lane'] / source.name
    runs, output = folder / 'runs', folder / 'output'
    runs.mkdir(parents=True, exist_ok=False); output.mkdir()
    for name, sha in old['inputs'].items():
        assert prior.digest(source / 'runs' / name) == sha
        shutil.copy2(source / 'runs' / name, runs / name)
    shutil.copy2(source / 'runs/reference.sol', runs / 'reference.sol')
    case = dict(task['case'])
    before = WeppSoilUtil(str(runs / 'p1.sol')).obj
    if study == 'erosion':
        soil = WeppSoilUtil(str(runs / 'p1.sol')); desired = deepcopy(soil.obj)
        legacy = json.loads((Path(task['legacy']) / 'record.json').read_text())['soil_readback']
        for index in ROLES[task['lane']]:
            for field in FIELDS:
                desired['ofes'][index][field] = legacy[index][field]
        soil.obj = desired; soil.write(str(runs / 'p1.sol'))
        actual = WeppSoilUtil(str(runs / 'p1.sol')).obj
        assert actual == desired, 'Unexpected soil serialization change'
        restored = deepcopy(actual)
        for index in ROLES[task['lane']]:
            for field in FIELDS:
                restored['ofes'][index][field] = before['ofes'][index][field]
        assert restored == before and actual['ofes'][0] == before['ofes'][0]
        assert all(200 in [h['solthk'] for h in ofe['horizons']] for ofe in actual['ofes'])
    else:
        for name, keep in task['keep'].items():
            if not keep:
                (runs / name).unlink()
        if not task['keep']['wepp_ui.txt']:
            case.pop('runtime')
    inputs = {p.name: prior.digest(p) for p in runs.iterdir() if p.name != 'reference.sol'}
    changed = {name for name in old['inputs'] if inputs.get(name) != old['inputs'][name]}
    expected = {'p1.sol'} if study == 'erosion' else {name for name, keep in task['keep'].items() if not keep}
    assert changed <= expected and (study == 'erosion' or changed == expected)
    assert prior.digest(BINARY) == prior.SHA
    with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
        proc = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=stdout, stderr=stderr, timeout=300)
    record = dict(case=case, original_case=task['case'], study=study, lane=task['lane'], group=task['group'],
                  source_record_sha256=task['source_record_sha256'], binary_sha256=prior.SHA,
                  inputs=inputs, outputs={p.name: prior.digest(p) for p in output.iterdir()},
                  width_m=old['width_m'], profile_length_m=old['profile_length_m'], returncode=proc.returncode,
                  physical_pass=False, status='native_failure', reference_kg_yr=task['reference_kg_yr'],
                  baseline_kg_yr=old['metrics']['sediment_export_kg_yr'])
    if proc.returncode == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text():
        record.update(status='completed', soil_readback=WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes'],
                      metrics=c.b.parse_loss(output / 'H1.loss.dat', old['width_m']))
        if study == 'runtime':
            pmet_banner = 'FAO Penman-Monteith ET Method Implemented' in (runs / 'stdout').read_text()
            assert pmet_banner == task['keep']['pmetpara.txt']
        record['audit'] = c.audit(folder, case, record)
        record['water_output_unchanged'] = record['outputs']['H1.wat.dat'] == old['outputs']['H1.wat.dat']
        record['physical_pass'] = record['audit']['physical_pass'] and (study != 'erosion' or record['water_output_unchanged'])
        value, ref = record['metrics']['sediment_export_kg_yr'], record['reference_kg_yr']
        record['within'] = .1 <= value / ref <= 10 if ref > 1 else value <= max(1, 10 * ref)
    dump(folder / 'record.json', record)
    return record


def run(study):
    dest = directory(study); declaration = json.loads((dest / 'declaration.json').read_text())
    assert declaration['script_sha256'] == prior.digest(Path(__file__))
    for name, sha in declaration['dependency_sha256'].items():
        assert prior.digest(HERE / name) == sha
    records = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for record in pool.map(execute, ((study, task) for task in declaration['tasks'])):
            records.append(record)
            if len(records) % 20 == 0:
                print(study, len(records), '/', len(declaration['tasks']), flush=True)
                dump(dest / 'partial-results.json', records)
    dump(dest / 'results.json', records)
    summary = dict(cases=len(records), completed=sum(r['status'] == 'completed' for r in records),
                   physical_pass=sum(r['physical_pass'] for r in records),
                   results_sha256=prior.digest(dest / 'results.json'),
                   lanes={lane: {group: dict(cases=len(items := [r for r in records if r['lane'] == lane and r['group'] == group]),
                                               within=sum(r.get('within', False) for r in items),
                                               physical_pass=sum(r['physical_pass'] for r in items))
                                 for group in sorted({r['group'] for r in records})}
                          for lane in sorted({r['lane'] for r in records})})
    dump(dest / 'summary.json', summary); dump(HERE / f'{study}-ablation-v1-summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('study', choices=('erosion', 'runtime')); parser.add_argument('--declare', action='store_true')
    args = parser.parse_args()
    declare(args.study) if args.declare else run(args.study)
