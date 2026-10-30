"""Frozen development-only road surface screen; never edits project defaults."""
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PRIOR = Path('/wc1/runs/ro/roads-drainage-validation-20261029-v2')
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261029/surface-screen-v4')
REUSE = ROOT.parent/'surface-screen-v3'
spec = importlib.util.spec_from_file_location('prior_audit', REPO/'docs/work-packages/20261029_roads_drainage_validation/artifacts/analyze.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
b = a.b
VARIANTS = ('roles', 'erosion', 'rock', 'compact1', 'compact3', 'compact10')


def transform(ofes, reference, variant):
    """Only road erosion, surface rock and upper-200mm conductivity may change."""
    if variant not in VARIANTS:
        raise ValueError('Unknown variant')
    result = deepcopy(ofes)
    road = result[0]
    if variant != 'roles':
        for key in ('ki', 'kr', 'shcrit'):
            road[key] = reference[key]
    if variant == 'rock' or variant.startswith('compact'):
        for horizon in road['horizons']:
            if horizon['solthk'] <= 200:
                horizon['rfg'] = reference['horizons'][0]['rfg']
    if variant.startswith('compact'):
        # The 9002 parser represents these three metadata fields as strings.
        road.update(ksatadj='0', ksatfac='1.0', ksatrec='0.0')
        for horizon in road['horizons']:
            if horizon['solthk'] <= 200:
                horizon['ksat'] = float(variant.removeprefix('compact'))
    if 200 not in [h['solthk'] for h in road['horizons']]:
        raise ValueError('Missing normalized treatment boundary')
    if result[1:] != ofes[1:]:
        raise ValueError('Treatment leaked into fill or buffer')
    return result


def execute(case):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary
    profile = '-'.join(case[k] for k in ('climate','soil','design','surface','traffic'))
    source = PRIOR/'matrix-v1'/f'{profile}-current'
    previous = json.loads((source/'record.json').read_text())
    a.s.check_files(source, previous)
    name = '-'.join(case.values())
    folder = ROOT/'matrix-v1'/name
    runs = folder/'runs'
    out = folder/'output'
    runs.mkdir(parents=True, exist_ok=False)
    out.mkdir()
    for file in previous['inputs']:
        shutil.copy2(source/'runs'/file, runs/file)
    shutil.copy2(source/'runs/reference.sol', runs/'reference.sol')
    (runs/'wepp_ui.txt').write_bytes(b'')
    soil = WeppSoilUtil(str(runs/'p1.sol'))
    reference = WeppSoilUtil(str(runs/'reference.sol')).obj['ofes'][0]
    expected = transform(soil.obj['ofes'], reference, case['variant'])
    soil.obj['ofes'] = expected
    soil.write(str(runs/'p1.sol'))
    actual = WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
    if actual != expected:
        raise ValueError('Treatment readback mismatch')
    ref_folder = b.DEFAULT_ROOT/'validation-v4'/f'{profile}-legacy-legacy'
    ref_record = json.loads((ref_folder/'record.json').read_text())
    a.s.check_files(ref_folder, ref_record)
    for file in ('p1.cli','p1.man','p1.slp','p1.run'):
        if b.digest(runs/file) != ref_record['inputs'][file]:
            raise ValueError('Reference geometry/management/climate/prompt mismatch')
    # WEPP2010 reference predates the shared 200mm writer normalization.
    # Require exact bytes after that single documented normalization, not an
    # unrestricted semantic comparison that could hide parameter drift.
    if ensure_200mm_boundary((ref_folder/'runs/p1.sol').read_text()) != (runs/'reference.sol').read_text():
        raise ValueError('Reference parameterization mismatch')
    declaration = json.loads((ROOT/'declaration.json').read_text())
    binary = declaration['binary']
    if b.digest(binary['path']) != binary['sha256']:
        raise ValueError('Binary drift')
    inputs = {p.name:b.digest(p) for p in runs.iterdir() if p.name != 'reference.sol'}
    reused = REUSE/'matrix-v1'/name
    reused_record = reused/'record.json'
    reuse_sha = None
    if reused_record.exists():
        old = json.loads(reused_record.read_text())
        a.s.check_files(reused, old)
        if old['case'] != case or old['inputs'] != inputs or old['soil_readback'] != actual:
            raise ValueError('Reuse declaration/input drift')
        for file in old['outputs']:
            shutil.copy2(reused/'output'/file, out/file)
        for file in ('stdout','stderr'):
            shutil.copy2(reused/'runs'/file, runs/file)
        code = 0
        reuse_sha = b.digest(reused_record)
    else:
        with (runs/'p1.run').open() as inp, (runs/'stdout').open('w') as stdout, (runs/'stderr').open('w') as stderr:
            proc = subprocess.run([binary['path']], cwd=runs, stdin=inp, stdout=stdout, stderr=stderr, timeout=180)
        code = proc.returncode
    if code or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        failure = dict(case=case, status='native_failure', returncode=code,
            inputs=inputs, outputs={p.name:b.digest(p) for p in out.iterdir()},
            stdout_sha256=b.digest(runs/'stdout'), stderr_sha256=b.digest(runs/'stderr'),
            reason=(runs/'stdout').read_text().splitlines()[-1], within=False,
            negative_fluxes=[], report_reconciled=False, ebe_mismatch_events=None)
        b.dump(folder/'failure.json', failure)
        return failure
    record = dict(case=case, name=name, status='completed', width_m=previous['width_m'],
        profile_length_m=previous['profile_length_m'], soil_readback=actual, inputs=inputs, reused_record_sha256=reuse_sha,
        outputs={p.name:b.digest(p) for p in out.iterdir()},
        metrics=b.parse_loss(out/'H1.loss.dat', previous['width_m']),
        wat_rows=b.validate_wat(out/'H1.wat.dat', json.loads((ROOT/'inputs/manifest.json').read_text())['climates'][case['climate']]))
    b.dump(folder/'record.json', record)
    audit = a.analyze_case((ROOT, case, ROOT/'analysis'))
    reference_metrics = b.parse_loss(ref_folder/'output/H1.loss.dat', previous['width_m'])
    ref = reference_metrics['sediment_export_kg_yr']
    value = record['metrics']['sediment_export_kg_yr']
    return dict(case=case, status='completed', reference_kg_yr=ref, export_kg_yr=value,
        ratio=value/ref if ref else None, meaningful=ref>1,
        within=(.1 <= value/ref <= 10) if ref>1 else value <= max(1, 10*ref),
        negative_fluxes=audit['sediment']['negative_fluxes'],
        report_reconciled=audit['sediment']['report_reconciled'],
        ebe_mismatch_events=len(audit['ebe']['mismatches']),
        reference_record_sha256=b.digest(ref_folder/'record.json'), record_sha256=b.digest(folder/'record.json'))


def main():
    cases = [dict(zip(('climate','soil','design','surface','traffic','variant','runtime'), values))
        for values in itertools.product(('site','birmingham','flagstaff'), ('sand','clay','loam','silt'),
            ('inbare','inveg'), ('gravel','paved'), ('high','none'), VARIANTS, ('ui-only',))]
    ROOT.mkdir(exist_ok=False)
    (ROOT/'matrix-v1').mkdir()
    (ROOT/'analysis/cases').mkdir(parents=True)
    (ROOT/'inputs').symlink_to(PRIOR/'inputs', target_is_directory=True)
    binary = json.loads((PRIOR/'declaration.json').read_text())['binaries']['modern']
    b.dump(ROOT/'declaration.json', dict(cases=cases, binary=binary,
        script_sha256=b.digest(Path(__file__)), auditor_sha256=b.digest(Path(a.__file__)),
        reuse_root=str(REUSE), reuse_declaration_sha256=b.digest(REUSE/'declaration.json'),
        scope='Development mechanism screen, not validation or production runtime parity',
        hypotheses={'erosion':'road Ki/Kr/tau from configuration-matched FSWEPP template',
            'rock':'erosion plus upper 200mm road rock parameter 65 gravel / 95 paved',
            'compact':'rock plus fixed upper200mm Ksat 1/3/10 mm/h, neutral dynamic adjustment; exploratory brackets, not measured values'},
        unchanged='Generated textures/deeper horizons and all fill/buffer properties, lower boundaries; no withheld outputs',
        runtime='UI only; project-specific snow, groundwater and PMET remain subsequent validation requirements'))
    shutil.copy2(__file__, ROOT/'executed-screen.py')
    results = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for index, result in enumerate(pool.map(execute, cases), 1):
            results.append(result)
            b.dump(ROOT/'partial-results.json', results)
            print(f'{index}/{len(cases)} {result["case"]} within={result["within"]}', flush=True)
    b.dump(ROOT/'results.json', results)
    b.dump(HERE/'surface-screen-v4.json', results)
    summary = {}
    for variant in VARIANTS:
        rows = [r for r in results if r['case']['variant'] == variant]
        summary[variant] = dict(cases=len(rows), within=sum(r['within'] for r in rows),
            native_failures=sum(r['status']=='native_failure' for r in rows),
            negative_cases=sum(bool(r['negative_fluxes']) for r in rows),
            unreconciled=sum(not r['report_reconciled'] for r in rows),
            ebe_mismatch_cases=sum((r['ebe_mismatch_events'] or 0)>0 for r in rows),
            groups={key:{value:dict(cases=len(group),within=sum(r['within'] for r in group))
                for value in sorted({r['case'][key] for r in rows})
                for group in [[r for r in rows if r['case'][key]==value]]}
                for key in ('climate','soil','design','surface','traffic')})
    b.dump(HERE/'surface-screen-summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
