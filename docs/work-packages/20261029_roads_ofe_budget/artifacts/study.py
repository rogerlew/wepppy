"""Frozen, isolated hydraulic factorial; no production parameter changes."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PRIOR = REPO / 'docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py'
spec = importlib.util.spec_from_file_location('prior_prepared_experiment', PRIOR)
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)
b = e.b
ROOT = Path('/wc1/runs/ro/roads-ofe-budget-20261029')
PANEL = [
    ('site', 'sand', 'outunrut', 'gravel', 'high'),
    ('site', 'clay', 'outunrut', 'paved', 'high'),
    ('birmingham', 'clay', 'outunrut', 'paved', 'low'),
    ('site', 'sand', 'outrut', 'gravel', 'high'),
    ('denver', 'loam', 'outrut', 'gravel', 'low'),
    ('charleston', 'silt', 'inveg', 'gravel', 'low'),
]
HYDRAULIC_KEYS = ('ksatadj', 'ksatfac', 'ksatrec')
SOURCE_COMMIT = 'b73e93b19a724d1991d341d38a18d11e742231bd'


def assemble(root, soil_key, variant, output):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary

    base = root / 'inputs/prepared' / soil_key
    formatted = WeppSoilUtil(str(base / 'format.sol'))
    if variant == 'format':
        ofes = [deepcopy(formatted.obj['ofes'][0]) for _ in range(3)]
    else:
        if len(variant) != 3 or set(variant) - {'0', '1'}:
            raise ValueError('Unknown factorial treatment')
        ofes = []
        for enabled, role in zip(variant, ('bare', 'bare', 'forest')):
            ofe = deepcopy(WeppSoilUtil(str(base / f'{role}.sol')).obj['ofes'][0])
            neutral = formatted.obj['ofes'][0]
            if [h['solthk'] for h in ofe['horizons']] != [h['solthk'] for h in neutral['horizons']]:
                raise ValueError('Factorial horizon mismatch')
            if enabled == '0':
                for key in HYDRAULIC_KEYS:
                    ofe[key] = neutral[key]
                for horizon, original in zip(ofe['horizons'], neutral['horizons']):
                    horizon['ksat'] = original['ksat']
            ofes.append(ofe)
    formatted.obj['ofes'] = ofes
    formatted.obj['ntemp'] = 3
    formatted.write(str(output))
    text = output.read_text()
    if ensure_200mm_boundary(text) != text:
        raise ValueError('Unnormalized emitted soil')
    actual = WeppSoilUtil(str(output)).obj['ofes']
    if any(200 not in [h['solthk'] for h in o['horizons']] for o in actual):
        raise ValueError('Missing 200 mm boundary')
    return actual


def stage(root):
    root.mkdir(exist_ok=False)
    shutil.copytree(e.ROOT / 'inputs', root / 'inputs')
    shutil.copytree(e.ROOT / 'reference', root / 'reference')
    manifest = json.loads((root / 'inputs/manifest.json').read_text())
    for key, modes in manifest['prepared'].items():
        for mode, metadata in modes.items():
            if b.digest(root / 'inputs/prepared' / key / f'{mode}.sol') != metadata['sha256']:
                raise ValueError('Frozen prepared soil drift')
    for key, metadata in manifest['climates'].items():
        if b.digest(root / 'inputs/climates' / f'{key}.cli') != metadata['sha256']:
            raise ValueError('Frozen climate drift')
    source = root / 'native-source'
    source.mkdir()
    for name in ('sedout.for', 'sloss.for', 'contin.for', 'watbal.for', 'watbal_hourly.for', 'outfil.for', 'cavloss.inc'):
        content = subprocess.check_output(['git', '-C', '/workdir/wepp-forest', 'show', f'{SOURCE_COMMIT}:src/{name}'])
        (source / name).write_bytes(content)
    source_files = [Path(__file__), PRIOR, Path(b.__file__),
                    REPO / 'wepppy/wepp/soils/utils/wepp_soil_util.py',
                    REPO / 'wepppy/wepp/soils/horizon_boundary.py',
                    REPO / 'wepp_runner/wepp_runner.py',
                    REPO / 'wepp_runner/templates/hillslope.template']
    declaration = {'panel': PANEL, 'variants': [''.join(bits) for bits in itertools.product('01', repeat=3)] + ['format'],
                   'factor_order': ['road', 'fill', 'buffer'], 'hydraulic_fields': [*HYDRAULIC_KEYS, 'horizon.ksat'],
                   'fixed_erosion': 'bare road, bare fill, forest buffer; format anchor separate',
                   'source_commit': SOURCE_COMMIT,
                   'native_source_sha256': {p.name: b.digest(p) for p in source.iterdir()},
                   'source_sha256': {str(p.relative_to(REPO)): b.digest(p) for p in source_files}}
    b.dump(root / 'declaration.json', declaration)
    print('Staged frozen inputs and six-profile 66-run declaration', flush=True)


def execute(task):
    root, batch, case = task
    from wepp_runner import make_hillslope_run
    manifest = json.loads((root / 'inputs/manifest.json').read_text())
    name = '-'.join(case.values())
    folder = root / batch / name
    runs, output = folder / 'runs', folder / 'output'
    runs.mkdir(parents=True, exist_ok=False)
    output.mkdir()
    b.reference_soil(root, case['soil'], case['design'], case['surface'], case['traffic'], runs / 'reference.sol')
    if case['variant'] == 'legacy':
        shutil.copyfile(runs / 'reference.sol', runs / 'p1.sol')
        soil = None
    else:
        soil = assemble(root, case['soil'], case['variant'], runs / 'p1.sol')
    man = {'outunrut': '3outunr', 'outrut': '3outrut', 'inveg': '3inslope'}[case['design']] + '.man'
    shutil.copyfile(root / 'reference/api/db/wepproad/managements' / man, runs / 'p1.man')
    slope, width, length = b.slope_text(case['design'])
    (runs / 'p1.slp').write_text(slope)
    shutil.copyfile(root / 'inputs/climates' / f"{case['climate']}.cli", runs / 'p1.cli')
    make_hillslope_run(1, 16, str(runs), reveg=False, wepp_bin='wepp_261026')
    runfile = runs / 'p1.run'
    lines = runfile.read_text().splitlines()
    if lines[6] != '1':
        raise ValueError('Run-prompt drift')
    lines[6] = '2'
    runfile.write_text('\n'.join(lines) + '\n')
    binary = manifest['binaries'][case['binary']]
    if b.digest(binary['path']) != binary['sha256']:
        raise ValueError('Binary drift')
    record = {'case': case, 'name': name, 'status': 'prepared', 'width_m': width, 'profile_length_m': length,
              'soil_readback': soil, 'binary': binary, 'inputs': {p.name: b.digest(p) for p in runs.iterdir()}}
    b.dump(folder / 'record.json', record)
    start = time.monotonic()
    with runfile.open() as stdin, (runs / 'stdout').open('w') as stdout, (runs / 'stderr').open('w') as stderr:
        result = subprocess.run([binary['path']], cwd=runs, stdin=stdin, stdout=stdout, stderr=stderr, timeout=180)
    record['elapsed_s'] = time.monotonic() - start
    if result.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs / 'stdout').read_text():
        raise ValueError(f'Native execution failed: {name}')
    record['metrics'] = b.parse_loss(output / 'H1.loss.dat', width)
    record['wat_rows'] = b.validate_wat(output / 'H1.wat.dat', manifest['climates'][case['climate']])
    for name in ('p1.run', 'p1.sol', 'p1.man', 'p1.cli', 'p1.slp'):
        if b.digest(runs / name) != record['inputs'][name]:
            raise ValueError('Consumed input changed')
    record['outputs'] = {p.name: b.digest(p) for p in output.iterdir()}
    record['status'] = 'completed'
    b.dump(folder / 'record.json', record)
    return record


def run(root, batch, workers):
    declaration = json.loads((root / 'declaration.json').read_text())
    for path, expected in declaration['source_sha256'].items():
        if b.digest(REPO / path) != expected:
            raise ValueError(f'Staged source changed: {path}')
    dest = root / batch
    dest.mkdir(exist_ok=False)
    shutil.copyfile(__file__, dest / 'executed-study.py')
    tasks = []
    for row in PANEL:
        common = dict(zip(('climate', 'soil', 'design', 'surface', 'traffic'), row))
        tasks.extend((root, batch, dict(common, binary='modern', variant=v)) for v in declaration['variants'])
        tasks.extend((root, batch, dict(common, binary=binary, variant='legacy')) for binary in ('legacy', 'modern'))
    b.dump(dest / 'cases.json', [t[2] for t in tasks])
    records = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for record in pool.map(execute, tasks):
            records.append(record)
            print(f'{len(records)}/{len(tasks)} complete', flush=True)
    b.dump(dest / 'summary.json', records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage', 'run'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--batch', default='factorial-v1')
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    if args.command == 'stage':
        stage(args.root)
    else:
        run(args.root, args.batch, args.workers)
