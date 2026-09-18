"""Read-only content check for the disposable Rithet acceptance runs."""
import hashlib
import json
import math
import shlex
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from wepppy.wepp.management import Management, get_management_summary
from wepppy.wepp.soils.utils import WeppSoilUtil

root = Path(sys.argv[1])
landuse_only = '--landuse-only' in sys.argv[2:]
state = json.loads((root / 'landuse.nodb').read_text())['py/state']
assignments = state['domlc_mofe_d']
mapping = state['_mapping']
classes = sorted({str(v) for segments in assignments.values() for v in segments.values()})
expected = {}
expected_sources = {}
for key in classes:
    summary = get_management_summary(key, mapping)
    expected_sources[key] = summary.man_fn
    saved = state['managements'][key]
    saved = saved.get('py/state', saved)
    override = saved.get('cancov_override')
    expected[key] = (summary.cancov if override is None else override,
                     summary.inrcov, summary.rilcov)

def read_covers(path):
    obj = Management(Key='acceptance', ManagementFile=path.name,
                     ManagementDir=str(path.parent), Description='readback',
                     Color=(0, 0, 0, 255))
    return [(ini.data.cancov, ini.data.inrcov, ini.data.rilcov) for ini in obj.inis]

def manifest(pattern):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.glob(pattern)) if p.is_file()}

def same_values(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same_values(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_values(a, b) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return (math.isfinite(left) and math.isfinite(right)
                and math.isclose(left, right, rel_tol=1e-5, abs_tol=1e-5))
    return left == right

def soil_scientific_tokens(text):
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        row = []
        for token in shlex.split(line):
            try:
                value = float(token)
            except ValueError:
                value = token
            else:
                if not math.isfinite(value):
                    raise ValueError(f'Non-finite soil token: {token}')
            row.append(value)
        rows.append(row)
    return rows

table = pd.read_parquet(root / 'watershed/hillslopes.parquet')
wepp_ids = {str(int(row.topaz_id)): int(row.wepp_id) for row in table.itertuples()}
failures = []
if '--snapshot' in sys.argv:
    before = json.loads(Path(sys.argv[sys.argv.index('--snapshot') + 1]).read_text())['states']['landuse']
    for field in ('domlc_d', 'domlc_mofe_d', '_mapping'):
        if state[field] != before[field]:
            failures.append({'stage': 'persisted_intent_changed', 'field': field})
    for key in classes:
        prior = before['managements'][key]
        current = state['managements'][key]
        for field in ('cancov_override', 'inrcov_override', 'rilcov_override'):
            if prior.get('py/state', prior).get(field) != current.get('py/state', current).get(field):
                failures.append({'stage': 'cover_intent_changed', 'class': key, 'field': field})
observations = []
serialized_soil_cache = {}
for topaz, segments in sorted(assignments.items()):
    keys = [str(v) for _, v in sorted(segments.items(), key=lambda kv: int(kv[0]))]
    wanted = [expected[key] for key in keys]
    land = root / f'landuse/hill_{topaz}.mofe.man'
    prepared = root / f'wepp/runs/p{wepp_ids[topaz]}.man'
    generated = read_covers(land)
    sources = None  # Single-segment files have no synthesis provenance header.
    if len(keys) > 1:
        header = land.read_text().split('# Source Stack:\n', 1)[1].split('\n\n', 1)[0]
        sources = [line.removeprefix('# ') for line in header.splitlines()]
        if sources != [expected_sources[key] for key in keys]:
            failures.append({'topaz': topaz, 'stage': 'source_stack', 'actual': sources})
    actual_prepared = read_covers(prepared) if prepared.exists() else None
    stages = [('landuse', generated)]
    if not landuse_only:
        stages.append(('prepared', actual_prepared))
    for label, actual in stages:
        if actual is None or len(actual) != len(wanted) or any(
            not (math.isfinite(a) and math.isfinite(b)
                 and math.isclose(a, b, rel_tol=0, abs_tol=1e-5))
            for av, bv in zip(actual, wanted) for a, b in zip(av, bv)
        ):
            failures.append({'topaz': topaz, 'stage': label, 'wanted': wanted, 'actual': actual})
    soil = None
    if not landuse_only:
        expected_soil = WeppSoilUtil(str(root / f'soils/hill_{topaz}.mofe.sol'))
        soil = json.loads(json.dumps(expected_soil.obj['ofes']))
        # Match the source project's existing prep options, without writing files.
        expected_soil.modify_kslast(.0001)
        expected_soil.modify_initial_sat(.75)
        prepared_soil = WeppSoilUtil(str(root / f'wepp/runs/p{wepp_ids[topaz]}.sol')).obj['ofes']
        if len(soil) != len(keys) or not same_values(expected_soil.obj['ofes'], prepared_soil):
            failures.append({'topaz': topaz, 'stage': 'soil_propagation'})
        # Canonical prep serializes the transformed object, recomputing the 9002
        # hydraulic columns that WeppSoilUtil.obj does not retain when parsing.
        scientific_key = json.dumps(
            {key: value for key, value in expected_soil.obj.items() if key != 'header'},
            sort_keys=True,
        )
        if scientific_key not in serialized_soil_cache:
            serialized_soil_cache[scientific_key] = soil_scientific_tokens(str(expected_soil))
        if serialized_soil_cache[scientific_key] != soil_scientific_tokens(
            (root / f'wepp/runs/p{wepp_ids[topaz]}.sol').read_text()
        ):
            failures.append({'topaz': topaz, 'stage': 'soil_serialized_propagation'})
        if any(not math.isclose(ofe['sat'], .75) for ofe in prepared_soil):
            failures.append({'topaz': topaz, 'stage': 'initial_saturation'})
    observations.append({'topaz': topaz, 'wepp_id': wepp_ids[topaz], 'classes': keys,
                         'sources': sources, 'landuse': generated, 'prepared': actual_prepared,
                         'soil': soil})
result = {'runid': root.name, 'stage': 'landuse' if landuse_only else 'landuse+prepared',
          'mapping': mapping, 'expected_cover': expected,
          'class_counts': Counter(str(v) for s in assignments.values() for v in s.values()),
          'hillslope_count': len(assignments), 'failures': failures, 'observations': observations,
          'manifests': {pattern: manifest(pattern) for pattern in
                        ['landuse/hill_*.mofe.man', 'soils/hill_*.mofe.sol',
                         'wepp/runs/*.man', 'wepp/runs/*.sol']}}
print(json.dumps(result, indent=2))
sys.exit(bool(failures))
