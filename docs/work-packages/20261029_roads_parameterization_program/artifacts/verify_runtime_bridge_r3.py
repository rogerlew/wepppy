"""Verify all128 factorial cells from actual decks and fresh native readbacks."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import json
import math

import continuation as c
import role_boundary_assessment_r3 as role

HERE = Path(__file__).resolve().parent
ROOT = Path('/workdir/wepppy/out/roads-parameterization-program-20261031/runtime-bridge-r3')
FACTORS = ('wepp_ui.txt', 'pmetpara.txt', 'snow.txt')


def check(task):
    source = Path(task['source'])
    assert role.digest(source / 'record.json') == task['source_record_sha256']
    old = json.loads((source / 'record.json').read_text())
    lane = task['lane']
    folder = source if lane == '111' else ROOT / lane / source.name
    record = json.loads((folder / 'record.json').read_text())
    assert record['binary_sha256'] == role.SHA
    if lane != '111':
        assert record['original_case'] == task['case'] and record['lane'] == lane
    for section, subdir in [('inputs', 'runs'), ('outputs', 'output')]:
        for name, sha in record[section].items():
            assert role.digest(folder / subdir / name) == sha
    expected = {name: sha for name, sha in old['inputs'].items() if task['keep'].get(name, True)}
    assert record['inputs'] == expected
    assert role.digest(folder / 'runs/p1.sol') == old['inputs']['p1.sol']
    assert all((folder / 'runs' / name).is_file() == task['keep'][name] for name in FACTORS)
    within = False
    if record['status'] == 'completed':
        assert ('FAO Penman-Monteith ET Method Implemented' in (folder / 'runs/stdout').read_text()) == task['keep']['pmetpara.txt']
        metrics = c.b.parse_loss(folder / 'output/H1.loss.dat', record['width_m'])
        assert metrics == record['metrics']
        audit = c.audit(folder, record['case'], record)
        assert audit == record['audit'] and audit['physical_pass'] == record['physical_pass']
        value, ref = metrics['sediment_export_kg_yr'], task['reference_kg_yr']
        within = .1 <= value / ref <= 10 if ref > 1 else value <= max(1, 10 * ref)
        assert within == record['within']
    return dict(case=task['case'], group=task['group'], lane=lane, physical_pass=record['physical_pass'],
                status=record['status'], within=within,
                export_kg_yr=record.get('metrics', {}).get('sediment_export_kg_yr'),
                runoff_mm_yr=record.get('metrics', {}).get('runoff_mm_yr'),
                reference_kg_yr=task['reference_kg_yr'], record_sha256=role.digest(folder / 'record.json'),
                water_ofes=record.get('audit', {}).get('water', {}).get('ofes'),
                sediment_ofes=record.get('audit', {}).get('sediment', {}).get('ofes'))


def main():
    declaration = json.loads((ROOT / 'declaration.json').read_text())
    design_path = HERE / 'runtime-bridge-r3-design.json'
    assert role.digest(design_path) == declaration['design_sha256']
    assert role.digest(ROOT / 'executed-study.py') == declaration['script_sha256']
    design = json.loads(design_path.read_text())
    tasks = declaration['tasks'] + [dict(item, lane='111', keep={f: True for f in FACTORS}) for item in design['cases']]
    assert len(tasks) == 128
    assert len({(str(t['case']), t['lane']) for t in tasks}) == 128
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, tasks))
    lanes = {}
    for lane in sorted({r['lane'] for r in rows}):
        lanes[lane] = {group: dict(cases=len(items := [r for r in rows if r['lane'] == lane and r['group'] == group]),
                                  within=sum(r['within'] for r in items), physical_pass=sum(r['physical_pass'] for r in items))
                       for group in ('residual', 'passing_control')}
    result = dict(cells=128, new_runs=112, reused_baselines=16, physical_pass=sum(r['physical_pass'] for r in rows),
                  all_recorded_hashes_verified=True, retained_inputs_byte_exact=True,
                  native_audits_and_scores_recomputed=True, lanes=lanes, rows=rows,
                  declaration_sha256=role.digest(ROOT / 'declaration.json'), results_sha256=role.digest(ROOT / 'results.json'),
                  verifier_sha256=role.digest(Path(__file__)))
    (HERE / 'runtime-bridge-r3-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
