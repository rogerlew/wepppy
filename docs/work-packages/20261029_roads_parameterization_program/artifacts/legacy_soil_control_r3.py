"""Diagnostic control: exact revision-3 runtime/engine with the full legacy soil deck.

Covers every development miss plus one passing case per climate/design. Legacy
soils are controls only, never a proposed generated-soil parameterization.
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import shutil
import subprocess

import continuation as c
import role_boundary_assessment_r3 as role
from wepppy.wepp.soils.utils import WeppSoilUtil

ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/legacy-soil-control-r3')
BINARY = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
HERE = Path(__file__).resolve().parent


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def declare():
    scores = json.loads((role.MATRIX / 'magnitude-scores.json').read_text())
    selected = [row for row in scores if not row['within']]
    controls = {}
    for row in scores:
        key = row['case']['climate'], row['case']['design']
        if row['within']:
            controls.setdefault(key, row)
    assert len(selected) == 96 and len(controls) == 20
    selected += list(controls.values())
    assert len(selected) == 116
    ROOT.mkdir(parents=True, exist_ok=False)
    declaration = dict(script_sha256=role.digest(Path(__file__)), binary_sha256=role.SHA,
                       source_scores_sha256=role.digest(role.MATRIX / 'magnitude-scores.json'),
                       selection='All 96 frozen development misses plus first passing case in frozen score order per climate/design (20 controls).',
                       hypothesis='The generated-soil versus legacy-template treatment contributes to downstream differences; fixed modern engine/runtime controls identify the full-profile soil contribution before role-specific interventions.',
                       changed_input='Only p1.sol, replaced with hash-verified full FSWEPP2 legacy reference deck.',
                       retained='Exact revision-3 climate, geometry, management, run file and project runtime sidecars; no parameter or acceptance changes; withheld materials untouched.',
                       limitation='Legacy control is not an accepted parameter set. Versus WEPP2010, engine and runtime differ together. Role attribution remains net exchange rather than tagged particle origin.',
                       cases=selected)
    dump(ROOT / 'declaration.json', declaration)
    dump(HERE / 'legacy-soil-control-r3-declaration.json', declaration)
    shutil.copy2(__file__, ROOT / 'executed-study.py')
    print('Declared', len(selected), 'controls', flush=True)


def execute(score):
    case = score['case']; name = '-'.join(case.values())
    source = role.MATRIX / 'matrix-v1' / name
    old = json.loads((source / 'record.json').read_text())
    ref_name = '-'.join((case['climate'], role.TEXTURES[case['soil']], case['design'],
                         case['surface'], case['traffic'], 'legacy', 'legacy'))
    ref_folder = role.REFERENCE / ref_name
    ref = json.loads((ref_folder / 'record.json').read_text())
    folder = ROOT / 'matrix-v1' / name
    runs, out = folder / 'runs', folder / 'output'
    runs.mkdir(parents=True); out.mkdir()
    for filename, sha in old['inputs'].items():
        assert role.digest(source / 'runs' / filename) == sha
        shutil.copy2(source / 'runs' / filename, runs / filename)
    legacy = ref_folder / 'runs/p1.sol'
    assert role.digest(legacy) == ref['inputs']['p1.sol']
    shutil.copy2(legacy, runs / 'p1.sol')
    shutil.copy2(legacy, runs / 'reference.sol')
    inputs = {name: role.digest(runs / name) for name in old['inputs']}
    assert [name for name in inputs if inputs[name] != old['inputs'][name]] == ['p1.sol']
    assert role.digest(BINARY) == role.SHA
    with (runs / 'p1.run').open() as inp, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
        proc = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=stdout, stderr=stderr, timeout=300)
    record = dict(case=case, group=role.classify(score), inputs=inputs,
                  outputs={p.name: role.digest(p) for p in out.iterdir()},
                  binary_sha256=role.SHA, source_record_sha256=role.digest(source / 'record.json'),
                  reference_record_sha256=role.digest(ref_folder / 'record.json'),
                  reference_kg_yr=score['reference_kg_yr'], generated_kg_yr=score['export_kg_yr'],
                  width_m=old['width_m'], profile_length_m=old['profile_length_m'],
                  returncode=proc.returncode, physical_pass=False, status='native_failure')
    if proc.returncode == 0 and 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in (runs / 'stdout').read_text():
        record.update(status='completed', metrics=c.b.parse_loss(out / 'H1.loss.dat', old['width_m']),
                      soil_readback=WeppSoilUtil(str(runs / 'p1.sol')).obj['ofes'])
        record['audit'] = c.audit(folder, case, record)
        record['physical_pass'] = record['audit']['physical_pass']
        value = record['metrics']['sediment_export_kg_yr']; reference = record['reference_kg_yr']
        record['within'] = .1 <= value / reference <= 10 if reference > 1 else value <= max(1, 10 * reference)
    dump(folder / 'record.json', record)
    return record


def run():
    declaration = json.loads((ROOT / 'declaration.json').read_text())
    assert declaration['script_sha256'] == role.digest(Path(__file__))
    assert declaration['binary_sha256'] == role.digest(BINARY)
    records = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for record in pool.map(execute, declaration['cases']):
            records.append(record)
            if len(records) % 10 == 0:
                print(len(records), 'of', len(declaration['cases']), flush=True)
    dump(ROOT / 'results.json', records)
    summary = dict(cases=len(records), completed=sum(r['status'] == 'completed' for r in records),
                   physical_pass=sum(r['physical_pass'] for r in records),
                   groups={group: dict(cases=sum(r['group'] == group for r in records),
                                       within=sum(r.get('within', False) for r in records if r['group'] == group))
                           for group in sorted({r['group'] for r in records})},
                   results_sha256=role.digest(ROOT / 'results.json'),
                   declaration_sha256=role.digest(ROOT / 'declaration.json'))
    dump(ROOT / 'summary.json', summary)
    dump(HERE / 'legacy-soil-control-r3-summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--declare', action='store_true')
    if parser.parse_args().declare:
        declare()
    else:
        run()
