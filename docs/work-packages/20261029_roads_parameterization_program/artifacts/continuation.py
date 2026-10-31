"""Frozen repaired-engine rebaseline. No production changes or withheld outcomes."""
from concurrent.futures import ProcessPoolExecutor
import calendar
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('engineered', HERE / 'engineered_surface_screen.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
b = e.b
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261030')
BATCH = ROOT / 'rebaseline-v1'
BINARY = Path('/workdir/wepppy/wepp_runner/bin/wepp_261029')
SHA = '53628775e0e97d03f3f8c12e0d99b0f25842efa429d3ce869bf37ee382974461'
PRIOR = ROOT.with_name('roads-parameterization-program-20261029')


def audit(folder, case, record):
    """Three-OFE accounting without a generated-only profile-depth assumption."""
    import pyarrow.parquet as pq
    from wepppy.wepp.interchange.hill_element_interchange import run_wepp_hillslope_element_interchange as element
    from wepppy.wepp.interchange.hill_wat_interchange import run_wepp_hillslope_wat_interchange as wat
    from wepppy.wepp.interchange.hill_ebe_interchange import run_wepp_hillslope_ebe_interchange as ebe
    from wepppy.wepp.soils.utils import WeppSoilUtil
    e.a.s.check_files(folder, record)
    e.a.validate_runtime(folder, case, record)
    if WeppSoilUtil(str(folder/'runs/p1.sol')).obj['ofes'] != record['soil_readback']:
        raise ValueError('Soil readback drift')
    climate = json.loads((BATCH/'inputs/manifest.json').read_text())['climates'][case['climate']]
    first, last = (int(climate[k].split('-')[0]) for k in ('first', 'last'))
    years = last-first+1
    dates = {(y,j) for y in range(first,last+1) for j in range(1,366+calendar.isleap(y))}
    erows = pq.read_table(element(folder/'output', start_year=first, expected_hillslopes=1)).to_pylist()
    wrows = pq.read_table(wat(folder/'output', expected_hillslopes=1)).to_pylist()
    brows = pq.read_table(ebe(folder/'output', start_year=first, expected_hillslopes=1)).to_pylist()
    sediment, days = e.a.sediment_diagnostics(erows, record['width_m'], years, record['metrics']['sediment_export_kg_yr'])
    if not set(days) <= dates:
        raise ValueError('ELEMENT calendar outside climate')
    events = e.a.a.ebe_check(brows, days, strict=False)
    lines = [line for line in (folder/'runs/p1.slp').read_text().splitlines() if line and not line.startswith('#')]
    width = float(lines[2].split()[1])
    areas = [width*float(lines[i].split()[1]) for i in (3,5,7)]
    water = e.a.a.water_budget(wrows, areas, dates, years)
    invalid = []
    for line in (folder/'output/H1.wat.dat').read_text().splitlines():
        fields = line.split()
        if fields and fields[0].isdigit():
            row = list(map(float, fields))
            if any(v < 0 or not math.isfinite(v) for v in row[3:]):
                invalid.append(row)
    return dict(sediment=sediment, ebe=events, water=water, invalid_water_rows=invalid,
                physical_pass=not invalid and not sediment['negative_fluxes'] and sediment['report_reconciled'] and not events['mismatches'])


def execute(task):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    source, case, lane = task
    source = Path(source)
    oldfile = source/('record.json' if (source/'record.json').exists() else 'failure.json')
    old = json.loads(oldfile.read_text())
    case = dict(case, variant=lane)
    folder = BATCH/'matrix-v1'/'-'.join(case.values())
    runs, out = folder/'runs', folder/'output'
    runs.mkdir(parents=True, exist_ok=False)
    out.mkdir()
    for file, sha in old['inputs'].items():
        if b.digest(source/'runs'/file) != sha:
            raise ValueError('Source input drift')
        shutil.copy2(source/'runs'/file, runs/file)
    shutil.copy2(source/'runs/reference.sol', runs/'reference.sol')
    if lane == 'legacy_soil':
        shutil.copy2(runs/'reference.sol', runs/'p1.sol')
    inputs = {p.name:b.digest(p) for p in runs.iterdir() if p.name != 'reference.sol'}
    readback = WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
    if b.digest(BINARY) != SHA:
        raise ValueError('Binary drift')
    with (runs/'p1.run').open() as inp, (runs/'stdout').open('w') as stdout, (runs/'stderr').open('w') as stderr:
        proc = subprocess.run([str(BINARY)], cwd=runs, stdin=inp, stdout=stdout, stderr=stderr, timeout=300)
    record = dict(case=case, inputs=inputs, soil_readback=readback, source_record_sha256=b.digest(oldfile),
                  reference_soil_sha256=b.digest(runs/'reference.sol'), outputs={p.name:b.digest(p) for p in out.iterdir()}, returncode=proc.returncode)
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        record.update(status='native_failure', physical_pass=False, within=False, tail=(runs/'stdout').read_text()[-1500:])
        b.dump(folder/'failure.json', record)
        return record
    _, width, length = b.slope_text(case['design'])
    climate = json.loads((BATCH/'inputs/manifest.json').read_text())['climates'][case['climate']]
    record.update(status='completed', width_m=width, profile_length_m=length,
                  metrics=b.parse_loss(out/'H1.loss.dat',width), wat_rows=b.validate_wat(out/'H1.wat.dat',climate))
    b.dump(folder/'record.json',record)
    record['audit'] = audit(folder, case, record)
    profile = '-'.join(case[k] for k in ('climate','soil','design','surface','traffic'))
    ref_folder = b.DEFAULT_ROOT/'validation-v4'/f'{profile}-legacy-legacy'
    reference = json.loads((ref_folder/'record.json').read_text())
    e.a.s.check_files(ref_folder, reference)
    for key in ('p1.man','p1.slp','p1.cli','p1.run'):
        if inputs[key] != reference['inputs'][key]:
            raise ValueError(f'Unmatched reference input: {key}')
    ref = b.parse_loss(ref_folder/'output/H1.loss.dat',width)['sediment_export_kg_yr']
    value = record['metrics']['sediment_export_kg_yr']
    record.update(reference_kg_yr=ref, reference_sha256=b.digest(ref_folder/'record.json'), export_kg_yr=value,
                  within=.1<=value/ref<=10 if ref>1 else value<=max(1,10*ref), physical_pass=record['audit']['physical_pass'])
    b.dump(folder/'record.json',record)
    return record


def main():
    ROOT.mkdir(exist_ok=True)
    BATCH.mkdir(exist_ok=False)
    (BATCH/'inputs').symlink_to(PRIOR/'engineered-surface-screen-v1/inputs', target_is_directory=True)
    old = json.loads((HERE/'design-v1.json').read_text())
    for row in old['development'] + old['withheld_validation']:
        if b.digest(row['path']) != row['sha256']:
            raise ValueError('Material source drift')
    design = dict(old, version=2, modern_binary='wepp_261029', modern_sha256=SHA,
                  numerical_gate_status='Frozen unchanged for continuation 2026-10-30',
                  predecessor_sha256=b.digest(HERE/'design-v1.json'), acceptance_sha256=b.digest(HERE.parent/'acceptance.md'),
                  human_gate='Explicit owner approval of configuration specification and layout before product implementation',
                  script_sha256=b.digest(__file__))
    b.dump(ROOT/'design-v2.json',design)
    b.dump(HERE/'design-v2.json',design)
    tasks = []
    for r in json.loads((PRIOR/'project-runtime-screen-v2/results.json').read_text()):
        if r['case']['variant'] in ('roles','erosion'):
            tasks.append((str(PRIOR/'project-runtime-screen-v2/matrix-v1'/'-'.join(r['case'].values())), r['case'], r['case']['variant']))
    for r in json.loads((PRIOR/'engineered-surface-screen-v1/results.json').read_text()):
        if r['case']['variant'] == 'erosion_road_cap':
            source = str(PRIOR/'engineered-surface-screen-v1/matrix-v1'/'-'.join(r['case'].values()))
            tasks.extend((source,r['case'],lane) for lane in ('erosion_road_cap','legacy_soil'))
    if len(tasks) != 384:
        raise ValueError('Incomplete rebaseline')
    b.dump(BATCH/'declaration.json',dict(tasks=tasks,binary=dict(path=str(BINARY),sha256=SHA),
        script_sha256=b.digest(__file__),design_sha256=b.digest(ROOT/'design-v2.json'),
        limits='Three-OFE development rebaseline, fixed site runtime sidecars across climates; not production-builder or regional calibration evidence.'))
    shutil.copy2(__file__, BATCH/'executed-continuation.py')
    results=[]
    with ProcessPoolExecutor(max_workers=8) as pool:
        for result in pool.map(execute,tasks):
            results.append(result)
            b.dump(BATCH/'partial-results.json',results)
            print(len(results),len(tasks),result['case'],result['status'],result.get('within'),result.get('physical_pass'),flush=True)
    b.dump(BATCH/'results.json',results)
    summary={}
    for lane in ('roles','erosion','erosion_road_cap','legacy_soil'):
        rows=[r for r in results if r['case']['variant']==lane]
        summary[lane]=dict(cases=len(rows),numerical_pass=sum(r['within'] for r in rows),physical_pass=sum(r['physical_pass'] for r in rows))
    b.dump(BATCH/'summary.json',summary)
    b.dump(HERE/'rebaseline-v1-summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
