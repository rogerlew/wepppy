"""Read-only, bounded soil-reuse proof for the eight authorized production runs.

Reapply the existing disturbed conversion to preserved base soils in memory.
Compare every scientific token, including 9002 hydraulic columns omitted by the
soil object's parser. No controller getters, schema upgrades, or file writes.
"""
import hashlib
import json
import math
import shlex
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from wepppy.nodb.mods.disturbed.disturbed import (
    lookup_disturbed_class,
    read_disturbed_land_soil_lookup,
)
from wepppy.wepp.soils.utils import WeppSoilUtil, simple_texture

RUNIDS = {
    'ventilated-gag', 'equestrian-bonheur', 'tactful-aging',
    'incorporate-cerebrum', 'choice-feminist', 'neoliberal-dictate',
    'acetic-surprise', 'uncrowned-bolt',
}
runid = sys.argv[1]
assert runid in RUNIDS, runid
root = Path('/wc1/runs') / runid[:2] / runid
input_hashes = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retain(path):
    input_hashes[str(path.relative_to(root))] = sha(path)
    return path


def tokens(text):
    return [shlex.split(line) for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def same_rows(left, right):
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if len(a) != len(b):
            return False
        for x, y in zip(a, b):
            try:
                fx, fy = float(x), float(y)
            except ValueError:
                if x != y:
                    return False
            else:
                if not (math.isfinite(fx) and math.isfinite(fy)
                        and math.isclose(fx, fy, rel_tol=1e-10, abs_tol=1e-12)):
                    return False
    return True


states = {key: json.loads(retain(root / f'{key}.nodb').read_text())['py/state']
          for key in ('landuse', 'soils', 'disturbed', 'wepp')}
landuse, soils, disturbed, wepp = [states[key] for key in
                                 ('landuse', 'soils', 'disturbed', 'wepp')]
assert soils['_ssurgo_db'] == 'isric'
assert disturbed['_sol_ver'] == 9002.0
assert soils['_initial_sat'] == .75 and wepp['_kslast'] == .0001
assert not soils['_clip_soils'] and not soils['_clip_soils_minimum']
assert not wepp.get('_kslast_map')
assignments = landuse['domlc_mofe_d']
assert len(assignments) == 455
assert sum(map(len, assignments.values())) == 1065
assert set(assignments) == set(soils['ssurgo_domsoil_d']) == set(soils['domsoil_d'])

# Mirror active_lookup_variant/active_lookup_fn without controller access.
base_csv = root / 'disturbed/disturbed_land_soil_lookup.csv'
extended_csv = root / 'disturbed/disturbed_land_soil_lookup_extended.csv'
variant = disturbed.get('_active_lookup_variant')
variant = variant.strip().lower() if isinstance(variant, str) else None
if variant not in ('base', 'extended'):
    variant = 'extended' if extended_csv.exists() else 'base'
lookup_path = extended_csv if variant == 'extended' and extended_csv.exists() else base_csv
lookup = read_disturbed_land_soil_lookup(str(retain(lookup_path)))

base_cache, expected_cache, fallback_combinations = {}, {}, []
combinations, failures, generated_hashes = Counter(), [], {}
for topaz, segments in sorted(assignments.items()):
    assert sorted(map(int, segments)) == list(range(1, len(segments) + 1))
    assert soils['domsoil_d'][topaz] == f'hill_{topaz}.mofe'
    base_key = soils['ssurgo_domsoil_d'][topaz]
    if base_key not in base_cache:
        summary = soils['soils'][base_key]
        summary = summary.get('py/state', summary)
        base_path = retain(root / 'soils' / summary['fname'])
        base = WeppSoilUtil(str(base_path))
        assert base.obj['ntemp'] == 1
        base_cache[base_key] = base
    base = base_cache[base_key]
    texture = simple_texture(clay=base.clay, sand=base.sand)
    # SoilMultipleOfeSynth.write uses ksflag=0, independent of segment ksflag.
    expected = [['9002'], ['Any', 'comments:'], [str(len(segments)), '0']]
    for _, dom in sorted(segments.items(), key=lambda item: int(item[0])):
        management = landuse['managements'][str(dom)]
        management = management.get('py/state', management)
        disturbed_class = management['disturbed_class']
        key = (base_key, texture, disturbed_class)
        combinations[str(key)] += 1
        if key not in expected_cache:
            replacement = lookup.get((texture, lookup_disturbed_class(disturbed_class)))
            if replacement is None:
                # Preserve the existing 9002 lookup-miss branch exactly
                # (Disturbed._modify_mofe_soils_impl), not a generic thinning row.
                assert disturbed_class in ('', 'thinning_40_75'), key
                replacement = dict(luse=disturbed_class, stext=texture,
                                   ksatfac=0.0, ksatrec=0.0)
                fallback_combinations.append(key)
            generated = base.to_over9000(
                replacement,
                h0_max_om=(disturbed.get('_h0_max_om')
                           if disturbed_class and 'fire' in disturbed_class else None),
                version=disturbed['_sol_ver'],
                recompute_wp_fc_using_rosetta_on_bd_override=soils.get(
                    '_rosetta_wc_fc_from_disturbed_bd_override', False),
            )
            expected_cache[key] = tokens(str(generated))[3:]
        expected.extend(expected_cache[key])
    path = root / f'soils/hill_{topaz}.mofe.sol'
    generated_hashes[str(path.relative_to(root))] = sha(path)
    actual = tokens(path.read_text())
    if not same_rows(expected, actual):
        differences = [{'row': i, 'expected': a, 'actual': b}
                       for i, (a, b) in enumerate(zip(expected, actual))
                       if not same_rows([a], [b])]
        failures.append({'topaz': topaz, 'expected_rows': len(expected),
                         'actual_rows': len(actual), 'differences': differences[:3]})

for path, digest in {**input_hashes, **generated_hashes}.items():
    if sha(root / path) != digest:
        failures.append({'stage': 'changed_during_read', 'path': path})
print(json.dumps({
    'runid': runid, 'checked_at': datetime.now(timezone.utc).isoformat(),
    'hillslope_count': len(assignments), 'segment_count': sum(combinations.values()),
    'lookup': str(lookup_path.relative_to(root)), 'combinations': combinations,
    'canonical_9002_lookup_misses': fallback_combinations,
    'options': {key: value for key, value in (
        ('sol_ver', disturbed['_sol_ver']), ('h0_max_om', disturbed.get('_h0_max_om')),
        ('rosetta_bd_override', soils.get('_rosetta_wc_fc_from_disturbed_bd_override', False)),
        ('initial_sat', soils['_initial_sat']), ('kslast', wepp['_kslast']),
        ('clip_soils', soils['_clip_soils']), ('clip_soils_minimum', soils['_clip_soils_minimum']),
    )},
    'input_sha256': input_hashes, 'generated_sha256': generated_hashes,
    'failures': failures,
}, indent=2))
sys.exit(bool(failures))
