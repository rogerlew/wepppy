"""Isolated embedded-baseline feasibility/parity; NOT Roads persistence wiring."""
from pathlib import Path
from itertools import product
import argparse
import hashlib
import json
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[4]
ARTIFACTS = Path(__file__).resolve().parent
TEMPLATES = ROOT / 'wepppy/nodb/mods/roads/legacy_templates'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def baseline_id(assets):
    manifest = {'resolver_version': 1, 'assets': {key: value['sha256'] for key, value in assets.items()}}
    return 'roads-legacy-v1-' + digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode())


def validate(baseline, allowed):
    if baseline['resolver_version'] != 1 or set(baseline['assets']) != allowed:
        raise ValueError('Unsupported resolver or invalid asset set')
    for key, value in baseline['assets'].items():
        if digest(value['text'].encode()) != value['sha256']:
            raise ValueError(f'Asset hash mismatch: {key}')
    if baseline['id'] != baseline_id(baseline['assets']):
        raise ValueError('Baseline identity mismatch')


def write_pair(roads, soil, management, out, order, surface, traffic):
    out.mkdir(parents=True)
    args = dict(template_path=soil, output_path=out/'profile.sol', surface=surface, traffic=traffic, rfg_pct=15.)
    man = dict(template_path=management, output_path=out/'profile.man')
    if order == (1,):
        roads._build_single_ofe_soil_file(**args)
        roads._build_single_ofe_management_file(**man)
    elif order == (1, 3):
        roads._build_routed_two_ofe_soil_file(**args)
        roads._build_routed_two_ofe_management_file(**man)
    elif order == (1, 2, 3):
        roads._build_routed_three_ofe_soil_file(**args)
        shutil.copyfile(management, man['output_path'])
    else:
        roads._build_routed_mofe_soil_file(**args, ofe_order=order)
        roads._build_routed_mofe_management_file(**man, ofe_order=order)


def main(root):
    from wepppy.nodb.mods.roads import Roads
    from wepppy.wepp.soils.utils import WeppSoilUtil
    from tests.roads.roads_matrix import ARRANGEMENTS, read_management

    root.mkdir(parents=True, exist_ok=False)
    paths = sorted([*TEMPLATES.glob('soils/*.sol'), *TEMPLATES.glob('managements/*.man')])
    inventory_path = ARTIFACTS/'parameterization-baseline-inventory.json'
    inventory = json.loads(inventory_path.read_text())
    inventory_hashes = {row['path']: row['sha256'] for row in inventory['templates']}
    for path in paths:
        assert inventory_hashes[str(path.relative_to(ROOT))] == digest(path.read_bytes())
    assets = {str(p.relative_to(TEMPLATES)): {'text': p.read_bytes().decode('utf-8'), 'sha256': digest(p.read_bytes())} for p in paths}
    baseline = dict(id=baseline_id(assets), resolver_version=1, assets=assets)
    saved = root/'embedded-baseline.json'
    saved.write_text(json.dumps(baseline, indent=2)+'\n')
    restored = json.loads(saved.read_text())
    allowed = set(assets)
    validate(restored, allowed)
    assert restored == baseline
    rejected = []
    for label in ('text_tamper', 'asset_path', 'baseline_id', 'resolver_version'):
        invalid = json.loads(saved.read_text())
        if label == 'text_tamper':
            invalid['assets'][next(iter(assets))]['text'] += '\n'
        elif label == 'asset_path':
            invalid['assets']['../escape.sol'] = invalid['assets'].pop(next(iter(assets)))
        elif label == 'baseline_id':
            invalid['id'] += '0'
        else:
            invalid['resolver_version'] = 99
        try:
            validate(invalid, allowed)
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError(f'Accepted invalid {label}')
    retained = root/'retained-templates'
    for key, value in restored['assets'].items():
        path = retained/key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value['text'].encode())
    sandbox = root/'sandbox-repository-templates'
    shutil.copytree(TEMPLATES, sandbox)
    sandbox_keys = sorted(assets)
    (sandbox/sandbox_keys[0]).write_text('changed in sandbox only\n')
    (sandbox/sandbox_keys[1]).unlink()
    assert all(digest((retained/k).read_bytes()) == v['sha256'] for k,v in assets.items())
    # Standard file archive/copy feasibility only; not application archive/fork API coverage.
    archive = root/'baseline.tar'
    with tarfile.open(archive, 'w') as stream:
        stream.add(saved, arcname='embedded-baseline.json')
    with tarfile.open(archive) as stream:
        handle = stream.extractfile('embedded-baseline.json')
        assert handle is not None
        assert json.loads(handle.read()) == restored
    shutil.copyfile(saved, root/'copied-baseline.json')
    assert (root/'copied-baseline.json').read_bytes() == saved.read_bytes()
    roads = Roads.__new__(Roads)
    cases = []
    for arrangement, texture, surface, traffic in product(ARRANGEMENTS, ('clay','loam','sand','silt'), ('gravel','paved'), ('high','low','none')):
        design, order = ARRANGEMENTS[arrangement]
        selected_design = 'outslope_rutted' if design == 'outslope_unrutted' else design
        source_soil = roads._resolve_legacy_soil_template_path(design=selected_design, surface=surface, soil_texture=texture)
        source_man = roads._resolve_legacy_management_template_path(traffic=traffic)
        name = '-'.join((arrangement,texture,surface,traffic))
        current, bound = root/'cases'/name/'repository', root/'cases'/name/'bound'
        write_pair(roads, source_soil, source_man, current, order, surface, traffic)
        bound_soil, bound_man = retained/source_soil.relative_to(TEMPLATES), retained/source_man.relative_to(TEMPLATES)
        write_pair(roads, bound_soil, bound_man, bound, order, surface, traffic)
        hashes = {}
        for suffix in ('sol','man'):
            left, right = current/f'profile.{suffix}', bound/f'profile.{suffix}'
            assert left.read_bytes() == right.read_bytes(), name
            hashes[suffix] = digest(right.read_bytes())
        parsed = WeppSoilUtil(str(bound/'profile.sol')).obj['ofes']
        assert len(parsed) == len(order)
        management = read_management(bound/'profile.man', bound_man, order)
        cases.append(dict(name=name, role_order=order, template=str(source_soil.relative_to(TEMPLATES)), sha256=hashes, soil_roles=[dict(role=role, ki=o['ki'], kr=o['kr']) for role,o in zip(order,parsed)], management_readback=management))
    result = dict(status='passed', prototype_only=True, no_native_execution=True,
        no_production_persistence_wiring=True, no_canonical_fork_archive_claim=True,
        baseline_id=restored['id'], asset_count=len(assets), source_bytes=sum(len(v['text'].encode()) for v in assets.values()), serialized_bytes=saved.stat().st_size,
        inventory_sha256=digest(inventory_path.read_bytes()), script_sha256=digest(Path(__file__).read_bytes()),
        roads_source_sha256=digest((ROOT/'wepppy/nodb/mods/roads/roads.py').read_bytes()),
        exact_json_roundtrip=True, rejected_invalid_cases=rejected,
        sandbox_repository_edit_and_delete_preserved_bound_bytes=True,
        ordinary_file_copy_and_tar_member_roundtrip=True,
        cases=len(cases), byte_identical_pairs=len(cases)*2,
        matrix_reader_sha256=digest((ROOT/'tests/roads/roads_matrix.py').read_bytes()),
        raw_root=str(root), case_results=cases)
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'case_results'},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    main(parser.parse_args().root)
