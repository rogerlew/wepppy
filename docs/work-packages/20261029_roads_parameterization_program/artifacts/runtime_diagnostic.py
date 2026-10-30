"""Separate project runtime effects from rejected surface treatments."""
from concurrent.futures import ProcessPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ROOT = Path('/wc1/runs/ro/roads-parameterization-program-20261029/runtime-diagnostic-v1')
SOURCE = ROOT.parent/'surface-screen-v4'
SHARED = REPO/'tests/roads/data/shared'
spec = importlib.util.spec_from_file_location('runtime_screen', HERE/'screen.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
a = s.a
b = s.b
PROFILES = ('site-sand-inbare-gravel-high-roles-ui-only',
            'site-loam-inbare-gravel-high-roles-ui-only',
            'site-loam-inbare-paved-high-compact3-ui-only',
            'birmingham-clay-inbare-gravel-high-rock-ui-only',
            'birmingham-sand-inbare-gravel-none-compact1-ui-only')
BUNDLES = dict(pmet=('pmetpara.txt',), snow=('snow.txt',),
               pmet_snow=('pmetpara.txt','snow.txt'),
               project=tuple(sorted(p.name for p in SHARED.iterdir() if p.is_file())))


def execute(task):
    profile, bundle = task
    old = SOURCE/'matrix-v1'/profile
    record_file = old/('record.json' if (old/'record.json').exists() else 'failure.json')
    previous = json.loads(record_file.read_text())
    for name, sha in previous['inputs'].items():
        if b.digest(old/'runs'/name) != sha:
            raise ValueError('Source input drift')
    case = previous['case'].copy()
    case['runtime'] = bundle
    name = '-'.join(case.values())
    folder = ROOT/'matrix-v1'/name
    runs = folder/'runs'; out = folder/'output'
    runs.mkdir(parents=True, exist_ok=False); out.mkdir()
    for file in previous['inputs']:
        shutil.copy2(old/'runs'/file, runs/file)
    shutil.copy2(old/'runs/reference.sol', runs/'reference.sol')
    declaration = json.loads((ROOT/'declaration.json').read_text())
    for file in BUNDLES[bundle]:
        if b.digest(SHARED/file) != declaration['sidecars'][file]:
            raise ValueError('Sidecar drift')
        shutil.copy2(SHARED/file, runs/file)
    binary = declaration['binary']
    if b.digest(binary['path']) != binary['sha256']:
        raise ValueError('Binary drift')
    inputs = {p.name:b.digest(p) for p in runs.iterdir() if p.name != 'reference.sol'}
    with (runs/'p1.run').open() as inp, (runs/'stdout').open('w') as stdout, (runs/'stderr').open('w') as stderr:
        proc = subprocess.run([binary['path']], cwd=runs, stdin=inp, stdout=stdout, stderr=stderr, timeout=180)
    common = dict(case=case, name=name, inputs=inputs, outputs={p.name:b.digest(p) for p in out.iterdir()},
                  source_record_sha256=b.digest(record_file))
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        result = dict(common, status='native_failure', returncode=proc.returncode,
                      reason=(runs/'stdout').read_text().splitlines()[-1],
                      stdout_sha256=b.digest(runs/'stdout'), stderr_sha256=b.digest(runs/'stderr'))
        b.dump(folder/'failure.json', result)
        return result
    from wepppy.wepp.soils.utils import WeppSoilUtil
    _, width, length = b.slope_text(case['design'])
    manifest = json.loads((ROOT/'inputs/manifest.json').read_text())
    record = dict(common, status='completed', width_m=width, profile_length_m=length,
        soil_readback=WeppSoilUtil(str(runs/'p1.sol')).obj['ofes'],
        metrics=b.parse_loss(out/'H1.loss.dat', width),
        wat_rows=b.validate_wat(out/'H1.wat.dat', manifest['climates'][case['climate']]))
    b.dump(folder/'record.json', record)
    audit = a.analyze_case((ROOT,case,ROOT/'analysis'))
    return dict(case=case, status='completed', export_kg_yr=record['metrics']['sediment_export_kg_yr'],
                negative_fluxes=audit['sediment']['negative_fluxes'],
                report_reconciled=audit['sediment']['report_reconciled'],
                ebe_mismatch_events=len(audit['ebe']['mismatches']),
                pmet_fallback_notices=(runs/'stdout').read_text().count('No Penman-Monteith ET parameters'))


def main():
    ROOT.mkdir(exist_ok=False)
    (ROOT/'matrix-v1').mkdir(); (ROOT/'analysis/cases').mkdir(parents=True)
    (ROOT/'inputs').symlink_to(SOURCE/'inputs', target_is_directory=True)
    tasks = [(profile,bundle) for profile in PROFILES for bundle in BUNDLES]
    b.dump(ROOT/'declaration.json', dict(tasks=tasks, bundles=BUNDLES,
        binary=json.loads((SOURCE/'declaration.json').read_text())['binary'],
        sidecars={p.name:b.digest(p) for p in SHARED.iterdir() if p.is_file()},
        script_sha256=b.digest(Path(__file__)), auditor_sha256=b.digest(Path(a.__file__)),
        purpose='Development runtime sensitivity; same candidate soils, no tuning or withheld outputs',
        limits='Site coefficients intentionally transplanted to Birmingham as controlled sensitivity, not calibrated climate settings; no candidate acceptance'))
    shutil.copy2(__file__, ROOT/'executed-runtime-diagnostic.py')
    with ProcessPoolExecutor(max_workers=4) as pool:
        results=[]
        for result in pool.map(execute,tasks):
            results.append(result)
            print(result, flush=True)
    b.dump(ROOT/'results.json',results)
    b.dump(HERE/'runtime-diagnostic.json',results)


if __name__ == '__main__':
    main()
