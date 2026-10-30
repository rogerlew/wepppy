"""Predeclared isolated buffer-drainage matrix; never changes production defaults."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ROOT = Path('/wc1/runs/ro/roads-drainage-validation-20261029-v2')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


e = module('drainage_preparation', REPO/'docs/work-packages/20261029_roads_prepared_soil_hydraulics/artifacts/experiment.py')
a = module('drainage_accounting', REPO/'docs/work-packages/20261029_roads_ofe_budget/artifacts/accounting.py')
b = e.b
NEW = {'new_lithic': '/wc1/runs/ad/addicted-reservist/soils/1856573.sol',
       'new_lowk': '/wc1/runs/ad/addicted-reservist/soils/53949.sol',
       'new_open': '/wc1/runs/ad/addicted-reservist/soils/1718494.sol'}
SOILS = dict(e.SOURCES, **NEW)
TEXTURES = {**{s:s for s in b.SPECIMENS}, 'holdout':'loam', **{s:'loam' for s in NEW}}
CLASS = {s: ('bedrock' if s in ('sand','new_lithic') else
             'mineral' if s in ('clay','new_lowk') else 'unidentified') for s in SOILS}
SOURCE_K = {'sand':1.512, 'clay':3.276, 'new_lithic':0.126, 'new_lowk':3.276}
CLIMATES = (*b.CLIMATES, 'site')
DESIGNS = ('inbare','inveg','outrut','outunrut')


def cases():
    for values in itertools.product(CLIMATES, SOILS, DESIGNS, ('gravel','paved'), ('high','low','none'), ('current','source')):
        yield dict(zip(('climate','soil','design','surface','traffic','drainage'), values))


def policy(soil):
    return 'current' if CLASS[soil] == 'bedrock' else 'source'


def comparison(value, reference):
    if not all(math.isfinite(x) and x >= 0 for x in (value, reference)):
        raise ValueError('Invalid sediment comparison')
    if reference == 0:
        return dict(ratio=None, within=None, zero_reference=True, zero_match=value == 0)
    ratio = value/reference
    return dict(ratio=ratio, within=0.1 <= ratio <= 10, zero_reference=False, zero_match=None)


def buffer_change(ofes, conductivity):
    if not math.isfinite(conductivity) or conductivity <= 0:
        raise ValueError('Invalid conductivity')
    result = deepcopy(ofes)
    if len(result) != 3 or any(200 not in [h['solthk'] for h in o['horizons']] for o in result):
        raise ValueError('Expected three normalized OFEs')
    result[2]['res_lyr']['kslast'] = conductivity
    return result


def signature(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False).encode()).hexdigest()


def check_files(folder, record):
    for sub, key in (('runs','inputs'),('output','outputs')):
        for name, sha in record[key].items():
            if b.digest(folder/sub/name) != sha:
                raise ValueError(f'Artifact drift: {folder/sub/name}')


def stage(root):
    e.SOURCES = SOILS
    e.stage(root)
    freeze(root)


def freeze(root):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    if (root/'declaration.json').exists() or (root/'matrix-v1').exists():
        raise ValueError('Already frozen or executed')
    manifest = json.loads((root/'inputs/manifest.json').read_text())
    for key, info in manifest['soils'].items():
        if b.digest(root/'inputs/soils'/f'{key}.sol') != info['sha256']:
            raise ValueError('Staged original soil drift')
    for key, modes in manifest['prepared'].items():
        for mode, info in modes.items():
            if b.digest(root/'inputs/prepared'/key/f'{mode}.sol') != info['sha256']:
                raise ValueError('Staged prepared soil drift')
    endpoints = {}; signatures = {}
    for soil in SOILS:
        original = WeppSoilUtil(str(root/'inputs/soils'/f'{soil}.sol')).obj['ofes'][0]
        # Exclude names/metadata; compare actual horizon material and boundary parameters.
        signatures[soil] = signature(dict(horizons=original['horizons'], restriction=original['res_lyr']))
        buffer = WeppSoilUtil(str(root/'inputs/prepared'/soil/'forest.sol')).obj['ofes'][0]
        source = SOURCE_K[soil] if soil in SOURCE_K else buffer['horizons'][-1]['ksat']
        endpoints[soil] = dict(current=buffer['res_lyr']['kslast'], source=source,
                               classification=CLASS[soil], policy=policy(soil), texture=TEXTURES[soil],
                               input_bottom_mm=buffer['horizons'][-1]['solthk'])
        if soil not in NEW:
            for mode in ('bare','forest','format'):
                if WeppSoilUtil(str(root/'inputs/prepared'/soil/f'{mode}.sol')).obj['ofes'] != WeppSoilUtil(str(e.ROOT/'inputs/prepared'/soil/f'{mode}.sol')).obj['ofes']:
                    raise ValueError('Original specimen preparation drift')
    for key in NEW:
        if sum(value == signatures[key] for value in signatures.values()) != 1:
            raise ValueError('Additional specimen duplicates a semantic soil profile')
    sources = [Path(__file__),Path(e.__file__),Path(b.__file__),Path(a.__file__),
               REPO/'wepppy/wepp/soils/utils/wepp_soil_util.py',
               REPO/'wepppy/wepp/soils/horizon_boundary.py',
               HERE.parent/'package.md', HERE.parent/'prompts/completed/study_execplan.md']
    b.dump(root/'declaration.json',dict(cases=list(cases()), endpoints=endpoints,
            semantic_soil_signatures=signatures, source_sha256={str(p.relative_to(REPO)):b.digest(p) for p in sources},
            binaries=manifest['binaries'], reference_root=str(b.DEFAULT_ROOT/'validation-v4'),
            old_controls=str(e.ROOT/'confirmation-v1'), expected_cases=1920,
            acceptance='Every positive reference within factor ten; zeros separate; physical validity requires independent evidence'))
    shutil.copy2(__file__, root/'executed-study.py')
    print(json.dumps(endpoints, indent=2), flush=True)


def execute(task):
    from wepp_runner import make_hillslope_run
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from wepppy.wepp.soils.horizon_boundary import ensure_200mm_boundary
    root, case = task
    declaration = json.loads((root/'declaration.json').read_text())
    manifest = json.loads((root/'inputs/manifest.json').read_text())
    name = '-'.join(case.values()); folder = root/'matrix-v1'/name
    runs = folder/'runs'; out = folder/'output'
    runs.mkdir(parents=True, exist_ok=False); out.mkdir()
    b.reference_soil(root,TEXTURES[case['soil']],case['design'],case['surface'],case['traffic'],runs/'reference.sol')
    prepared = e.build_soil(root,case['soil'],'roles',runs/'reference.sol',runs/'p1.sol')
    soil = WeppSoilUtil(str(runs/'p1.sol'))
    target = declaration['endpoints'][case['soil']][case['drainage']]
    expected = buffer_change(prepared['ofes'],target)
    soil.obj['ofes'] = expected; soil.write(str(runs/'p1.sol'))
    actual = WeppSoilUtil(str(runs/'p1.sol')).obj['ofes']
    if actual != expected:
        raise ValueError('Emitted soil readback differs from declared treatment')
    soil_text = (runs/'p1.sol').read_text()
    if ensure_200mm_boundary(soil_text) != soil_text:
        raise ValueError('Unnormalized consumed soil')
    man = {'inbare':'3inslope','inveg':'3inslope','outrut':'3outrut','outunrut':'3outunr'}[case['design']]
    man += 'n.man' if case['traffic']=='none' else '.man'
    shutil.copy2(root/'reference/api/db/wepproad/managements'/man,runs/'p1.man')
    slope,width,length = b.slope_text(case['design']); (runs/'p1.slp').write_text(slope)
    shutil.copy2(root/'inputs/climates'/f"{case['climate']}.cli",runs/'p1.cli')
    make_hillslope_run(1,16,str(runs),reveg=False,wepp_bin='wepp_261026')
    lines = (runs/'p1.run').read_text().splitlines()
    if lines[6]!='1' or lines[5]!='../output/H1.pass.dat':
        raise ValueError('Runner prompt drift')
    lines[6]='2'; (runs/'p1.run').write_text('\n'.join(lines)+'\n')
    binary = declaration['binaries']['modern']
    if b.digest(binary['path']) != binary['sha256']:
        raise ValueError('Binary drift')
    inputs = {p.name:b.digest(p) for p in runs.iterdir() if p.name.startswith('p1.')}
    with (runs/'p1.run').open() as inp, (runs/'stdout').open('w') as stdout, (runs/'stderr').open('w') as stderr:
        proc = subprocess.run([binary['path']],cwd=runs,stdin=inp,stdout=stdout,stderr=stderr,timeout=180)
    if proc.returncode or 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' not in (runs/'stdout').read_text():
        raise ValueError(f'Native execution failed: {name}')
    record = dict(case=case,name=name,status='completed',width_m=width,profile_length_m=length,
                  soil_readback=actual, inputs=inputs,outputs={p.name:b.digest(p) for p in out.iterdir()},
                  metrics=b.parse_loss(out/'H1.loss.dat',width),
                  wat_rows=b.validate_wat(out/'H1.wat.dat',manifest['climates'][case['climate']]))
    check_files(folder,record)
    b.dump(folder/'record.json',record)
    return name


def run(root,workers):
    declaration=json.loads((root/'declaration.json').read_text())
    for path,sha in declaration['source_sha256'].items():
        if b.digest(REPO/path)!=sha: raise ValueError(f'Staged source drift: {path}')
    manifest=json.loads((root/'inputs/manifest.json').read_text())
    for soil,modes in manifest['prepared'].items():
        for mode,info in modes.items():
            if b.digest(root/'inputs/prepared'/soil/f'{mode}.sol')!=info['sha256']:
                raise ValueError('Prepared input drift')
    for climate,info in manifest['climates'].items():
        if b.digest(root/'inputs/climates'/f'{climate}.cli')!=info['sha256']:
            raise ValueError('Climate drift')
    (root/'matrix-v1').mkdir(exist_ok=False)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index,name in enumerate(pool.map(execute,((root,c) for c in declaration['cases'])),1):
            print(f'{index}/1920 {name}',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('stage','freeze','run'))
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--workers',type=int,default=12)
    args=parser.parse_args()
    if args.action=='stage': stage(args.root)
    elif args.action=='freeze': freeze(args.root)
    else: run(args.root,args.workers)


if __name__=='__main__': main()
