"""Complete a fixed-PMET/snow soil-by-hourly factorial on 111 diagnostic cases."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import json
import shutil
import role_runtime_ablation as base

HERE = Path(__file__).resolve().parent
ROOT = base.ROOT / 'soil-hourly-interaction-v1'

def directory(study):
    return ROOT

base.directory = directory

def read(path):
    return json.loads(path.read_text())

def verify(folder, record):
    assert record['binary_sha256'] == base.prior.SHA
    assert record['status'] == 'completed' and record['physical_pass']
    for category, subdir in (('inputs', 'runs'), ('outputs', 'output')):
        for name, sha in record[category].items():
            assert base.prior.digest(folder / subdir / name) == sha, (folder, name)

def declare():
    scores = read(base.LEGACY / 'declaration.json')['cases']
    prior_root = base.ROOT / 'runtime-ablation-v1'
    reused = {'-'.join(r['original_case'].values()): r for r in read(prior_root / 'results.json') if r['lane'] == '011'}
    tasks, cells = [], []
    for score in scores:
        case = score['case']; name = '-'.join(case.values())
        assert case['soil'] in base.prior.TEXTURES
        for soil in ('generated', 'legacy'):
            source = (base.prior.MATRIX / 'matrix-v1' if soil == 'generated' else base.LEGACY / 'matrix-v1') / name
            old = read(source / 'record.json'); verify(source, old)
            common = dict(case=case, group=base.prior.classify(score), soil=soil, reference_kg_yr=score['reference_kg_yr'])
            cells.append(dict(common, hourly=True, folder=str(source), record_sha256=base.prior.digest(source / 'record.json'), reused=True))
            if soil == 'legacy' and name in reused:
                off = prior_root / '011' / name
                verify(off, reused[name])
                assert reused[name]['inputs'] == {k:v for k,v in old['inputs'].items() if k != 'wepp_ui.txt'}
                cells.append(dict(common, hourly=False, folder=str(off), record_sha256=base.prior.digest(off / 'record.json'), reused=True))
            else:
                task = dict(case=case, group=common['group'], lane=f'{soil}-off', source=str(source),
                            source_record_sha256=base.prior.digest(source / 'record.json'),
                            reference_kg_yr=common['reference_kg_yr'],
                            keep={'wepp_ui.txt':False, 'pmetpara.txt':True, 'snow.txt':True})
                tasks.append(task)
                cells.append(dict(common, hourly=False, folder=str(ROOT / task['lane'] / name), reused=False))
    assert len(cells) == 444 and len(tasks) == 208
    ROOT.mkdir(exist_ok=False)
    declaration = dict(cases=111, cells=cells, tasks=tasks, new_runs=208, reused_cells=236,
        binary_sha256=base.prior.SHA, script_sha256=base.prior.digest(Path(__file__)),
        dependencies={name:base.prior.digest(HERE / name) for name in ('role_runtime_ablation.py','continuation.py','role_boundary_assessment.py')},
        source_legacy_results_sha256=base.prior.digest(base.LEGACY / 'results.json'),
        contract='Complete 2x2 soil/hourly panel. Remove only wepp_ui.txt; preserve PMET, snow, all soils and other inputs. Retain failures. Existing 111 cases are a selected diagnostic subset; no withheld inspection or new default. Use unchanged physical and magnitude checks.',
        analysis='Report each cell, grouped recovery and regressions, role boundary sediment and water response; interaction is (generated-off minus generated-on) minus (legacy-off minus legacy-on). Signed differences, not ratios with zero denominators. No causal attribution to a single soil property.')
    base.dump(ROOT / 'declaration.json', declaration)
    base.dump(HERE / 'soil-hourly-interaction-v1-declaration.json', declaration)
    shutil.copy2(__file__, ROOT / 'executed-study.py')
    print('Declared 444 cells: 208 new runs, 236 reused.', flush=True)

def execute(task):
    return base.execute(('runtime', task))

def run():
    declaration = read(ROOT / 'declaration.json')
    assert declaration['script_sha256'] == base.prior.digest(Path(__file__))
    for name, sha in declaration['dependencies'].items():
        assert base.prior.digest(HERE / name) == sha
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for row in pool.map(execute, declaration['tasks']):
            rows.append(row)
            if len(rows) % 20 == 0:
                base.dump(ROOT / 'partial-results.json', rows)
                print(len(rows), '/', len(declaration['tasks']), flush=True)
    base.dump(ROOT / 'results.json', rows)
    summary = dict(new_runs=len(rows), completed=sum(r['status']=='completed' for r in rows), physical_pass=sum(r['physical_pass'] for r in rows), results_sha256=base.prior.digest(ROOT / 'results.json'))
    base.dump(ROOT / 'summary.json', summary)
    base.dump(HERE / 'soil-hourly-interaction-v1-summary.json', summary)
    print(json.dumps(summary), flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--declare', action='store_true'); args=parser.parse_args()
    declare() if args.declare else run()
