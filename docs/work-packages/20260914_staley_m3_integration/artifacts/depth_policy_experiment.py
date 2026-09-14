"""Read-only research comparison; not a runtime adapter or production policy.

Run from the repository root with .venv/bin/python. JSON is printed to stdout.
Counterfactual copies reuse the unchanged offline helper: H/Cr are represented
as ordinary C only for numerical eligibility experiments, never in source data.
Endpoint policies suppress hzthk_r as an eligibility gate, retaining conflicts
in the audit. No builders, source acquisition, database writes or file writes.
"""
from __future__ import annotations

import ast
from collections import Counter
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace

import numpy as np
import rasterio

ROOT = Path.cwd()
MODULE = ROOT / 'wepppy/nodb/mods/postfire_debris_flow/soil_thickness.py'
SPEC = importlib.util.spec_from_file_location('offline_thickness', MODULE)
offline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(offline)
POLICIES = ('strict_v1', 'h_only', 'depth_no_r', 'all_recorded')


def evaluate(components, horizons, policy):
    # Check source ownership before any counterfactual row reduction.
    raw_components, _ = offline.derive_mapunits(components, horizons)
    conflicting_components = {
        str(r['cokey']) for r in raw_components
        if 'duplicate_id_conflict' in r['reason_codes']}
    copies = []
    pair_audits = []
    for raw in horizons:
        row = dict(raw)
        row['cokey'], row['chkey'] = offline._key(row['cokey']), offline._key(row['chkey'])
        if str(row['cokey']) in conflicting_components:
            copies.append(row)
            continue
        master, name = row['desgnmaster'] or '', row['hzname'] or ''
        legacy_h = master == 'H' and re.fullmatch(r'H[1-9][0-9]*', name)
        weathered = master == 'C' and re.fullmatch(r'\d*Cr[0-9]*', name)
        if policy != 'strict_v1' and legacy_h:
            row.update(desgnmaster='C', hzname='C')
        if policy == 'depth_no_r' and weathered:
            row.update(desgnmaster='C', hzname='C')
        if policy in ('depth_no_r', 'all_recorded'):
            row['hzthk_r'] = None
        copies.append(row)
    if policy == 'depth_no_r':
        groups = {}
        seen_ids = set()
        for row in copies:
            identity = (row['cokey'], row['chkey'])
            if row['cokey'] not in conflicting_components and identity in seen_ids:
                continue
            seen_ids.add(identity)
            key = (str(row['cokey']), offline._number(row['hzdept_r']),
                   offline._number(row['hzdepb_r']))
            groups.setdefault(key, []).append(row)
        reduced = []
        for (ck, top, bottom), group in groups.items():
            master, name = group[0]['desgnmaster'] or '', group[0]['hzname'] or ''
            pair = (ck not in conflicting_components and len(group) == 2 and
                    len({str(r['chkey']) for r in group}) == 2 and
                    top is not None and bottom is not None and 0 <= top < bottom and
                    re.fullmatch(r'[OAEBC]+(?:/| and )[OAEBC]+', master) and
                    ('/' in name or ' and ' in name) and
                    all(r['desgnmaster'] == master and r['hzname'] == name for r in group))
            reduced.extend(group[:1] if pair else group)
            if pair:
                pair_audits.append(dict(cokey=ck, source_chkeys=[r['chkey'] for r in group],
                                       top_cm=top, bottom_cm=bottom,
                                       reason='legacy_combination_pair'))
        copies = reduced
    mode = 'all_layers' if policy == 'all_recorded' else 'strict_soil'
    component_rows, mapunit_rows = offline.derive_mapunits(components, copies, policy=mode)
    counts = Counter(offline._key(r['cokey']) for r in horizons)
    for row in component_rows:
        row['source_row_count'] = counts[row['cokey']]
        row['pair_reductions'] = [a for a in pair_audits if a['cokey'] == row['cokey']]
    return component_rows, mapunit_rows


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_predicate():
    # Execute only the actual current predicate, without Horizon construction,
    # property estimation, imports, defaults, or builder selection side effects.
    helper = ast.parse((ROOT / 'wepppy/all_your_base/all_your_base.py').read_text())
    isfloat = next(n for n in helper.body if isinstance(n, ast.FunctionDef) and n.name == 'isfloat')
    source = ast.parse((ROOT / 'wepppy/soils/ssurgo/ssurgo.py').read_text())
    horizon = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'Horizon')
    valid = next(n for n in horizon.body if isinstance(n, ast.FunctionDef) and n.name == 'valid')
    tree = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), isfloat, valid], type_ignores=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(tree), '<current-source-predicates>', 'exec'), namespace)
    return namespace['valid']


def summarize(components, horizons, counts=None, raw_predicate=None):
    output = {'components': len(components), 'horizons': len(horizons), 'policies': {}}
    output['reported_thickness_conflicts'] = sum(
        h['hzthk_r'] not in (None, '') and
        float(h['hzthk_r']) != float(h['hzdepb_r']) - float(h['hzdept_r'])
        for h in horizons)
    _, baseline = evaluate(components, horizons, 'strict_v1')
    baseline_by_key = {r['mukey']: r for r in baseline}
    _, nonrock = evaluate(components, horizons, 'depth_no_r')
    nonrock_by_key = {r['mukey']: r for r in nonrock}
    for policy in POLICIES:
        cr, mr = evaluate(components, horizons, policy)
        record = {'component_status': dict(Counter(r['status'] for r in cr)),
                  'component_reasons': dict(Counter(r['reason_codes'] for r in cr)),
                  'mapunit_status': dict(Counter(r['status'] for r in mr))}
        common_deltas = [r['mean_cm'] - baseline_by_key[r['mukey']]['mean_cm']
                         for r in mr if r['mean_cm'] is not None and
                         baseline_by_key[r['mukey']]['mean_cm'] is not None]
        record['mapunit_mean_delta_on_common_keys_cm'] = {
            'minimum': min(common_deltas) if common_deltas else None,
            'maximum': max(common_deltas) if common_deltas else None,
            'changed_count': sum(v != 0 for v in common_deltas)}
        if policy == 'all_recorded':
            rock_deltas = [r['mean_cm'] - nonrock_by_key[r['mukey']]['mean_cm']
                           for r in mr if r['mean_cm'] is not None and
                           nonrock_by_key[r['mukey']]['mean_cm'] is not None]
            record['hard_r_effect_vs_depth_no_r_cm'] = {
                'changed_count': sum(v != 0 for v in rock_deltas),
                'minimum': min(rock_deltas), 'maximum': max(rock_deltas)}
        if counts is not None:
            available = [(counts.get(r['mukey'], 0), r) for r in mr if r['mean_cm'] is not None]
            cells = sum(n for n, r in available)
            record.update(valid_cells=cells, total_cells=sum(counts.values()),
                          mean_cm=sum(n*r['mean_cm'] for n, r in available)/cells if cells else None,
                          basin_mapunits=[{k: r[k] for k in ('mukey', 'mean_cm', 'valid_percentage')}
                                          for r in mr if r['mukey'] in counts])
        if raw_predicate is not None:
            eligible = {r['cokey'] for r in cr if r['status'] == 'valid'}
            cross = Counter()
            for h in horizons:
                cross[f"raw_WEPP={raw_predicate(SimpleNamespace(**h))},component_depth={str(h['cokey']) in eligible}"] += 1
            record['raw_predicate_cross_counts'] = dict(cross)
        output['policies'][policy] = record
    return output


def main():
    result = {'experiment': 'counterfactual_depth_policy_v1', 'offline_sha256': sha(MODULE),
              'sqlite_version': sqlite3.sqlite_version, 'sources': {}}
    fixtures = ROOT / 'tests/nodb/mods/fixtures/postfire_debris_flow_soils'
    for site in ('moscow_mountain', 'topanga', 'az_ponderosa'):
        paths = [fixtures / f'{site}_{table}.csv' for table in ('component', 'chorizon')]
        tables = []
        for path in paths:
            with path.open(newline='') as stream:
                tables.append(list(csv.DictReader(stream)))
        result['sources'][site] = summarize(*tables)
        result['sources'][site]['sha256'] = {p.name: sha(p) for p in paths}
    run = Path('/wc1/runs/ad/addicted-reservist')
    database = run / 'soils/ssurgo_tabular_cache.sqlite'
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as conn:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        conn.row_factory = sqlite3.Row
        tables = [[dict(r) for r in conn.execute(f'SELECT * FROM {table} ORDER BY {key}')]
                  for table, key in (('component', 'cokey'), ('chorizon', 'chkey'))]
    conn.close()
    counts = Counter()
    with rasterio.open(run / 'soils/ssurgo.tif') as soil, rasterio.open(run / 'dem/wbt/bound.tif') as basin:
        assert (soil.shape, soil.crs, soil.transform) == (basin.shape, basin.crs, basin.transform)
        for _, window in soil.block_windows(1):
            keys, n = np.unique(soil.read(1, window=window)[basin.read(1, window=window) == 1], return_counts=True)
            counts.update({str(int(k)): int(v) for k, v in zip(keys, n)})
    result['sources']['addicted-reservist'] = summarize(*tables, counts=counts, raw_predicate=source_predicate())
    result['sources']['addicted-reservist']['logical_sha256'] = [
        hashlib.sha256(json.dumps(table, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        for table in tables]
    def horizon(key, top, bottom, master='B', name=None):
        return dict(cokey='1', chkey=str(key), hzdept_r=top, hzdepb_r=bottom,
                    hzthk_r=None, desgnmaster=master, hzname=name or master)
    components = [dict(mukey='1', cokey='1', comppct_r=100, compname='Analytical')]
    cases = {
        'legacy_pair': ([horizon(1, 0, 10, 'A'), horizon(2, 10, 30, 'E/B'),
                         horizon(3, 10, 30, 'E/B'), horizon(4, 30, 40)], 40),
        'legacy_pair_with_repeated_id': ([horizon(1, 0, 20, 'E/B'), horizon(1, 0, 20, 'E/B'),
                                         horizon(2, 0, 20, 'E/B')], 20),
        'ordinary_duplicate_range': ([horizon(1, 0, 20), horizon(2, 0, 20)], None),
        'offset_overlap': ([horizon(1, 0, 20), horizon(2, 10, 30)], None),
        'gap': ([horizon(1, 0, 10), horizon(2, 20, 30)], None),
        'conflicting_id': ([horizon(1, 0, 10), horizon(1, 0, 20)], None),
        'conflicting_id_reported_thickness': ([dict(horizon(1, 0, 10), hzthk_r=10),
                                               dict(horizon(1, 0, 10), hzthk_r=11)], None),
        'conflicting_id_h_names': ([horizon(1, 0, 10, 'H', 'H1'), horizon(1, 0, 10, 'H', 'H2')], None),
        'conflicting_id_material': ([horizon(1, 0, 10, 'H', 'H1'), horizon(1, 0, 10, 'C')], None),
        'conflicting_id_cr_material': ([horizon(1, 0, 10, 'C', 'Cr'), horizon(1, 0, 10, 'C')], None),
        'normalized_same_id_not_pair': ([horizon('01', 0, 20, 'E/B'), horizon('1', 0, 20, 'E/B')], 20),
        'rock_between_soil': ([horizon(1, 0, 10), horizon(2, 10, 20, 'R'), horizon(3, 20, 30)], None),
        'terminal_rock': ([horizon(1, 0, 10), horizon(2, 10, 20, 'R')], 10),
        'weathered_recorded': ([horizon(1, 0, 10), horizon(2, 10, 20, 'C', 'Cr')], 20),
        'legacy_h': ([horizon(1, 0, 10, 'H', 'H1')], 10),
        'reversed_depth': ([horizon(1, 10, 0)], None),
    }
    result['analytical_cases'] = {}
    for name, (rows, expected) in cases.items():
        cr, _ = evaluate(components, rows, 'depth_no_r')
        assert cr[0]['thickness_cm'] == expected, (name, cr)
        result['analytical_cases'][name] = cr[0]
        if name == 'legacy_pair':
            assert cr[0]['source_row_count'] == 4 and cr[0]['horizon_count'] == 3
            assert cr[0]['pair_reductions'][0]['source_chkeys'] == ['2', '3']
        if name == 'normalized_same_id_not_pair':
            assert cr[0]['pair_reductions'] == []
        if name.startswith('conflicting_id'):
            for policy in POLICIES:
                checks, _ = evaluate(components, rows, policy)
                assert checks[0]['thickness_cm'] is None
                assert 'duplicate_id_conflict' in checks[0]['reason_codes']
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
