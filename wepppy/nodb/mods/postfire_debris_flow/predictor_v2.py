"""Validate common-support products without weakening the offline v1 reader."""
import numpy as np
import rasterio

from . import rainfall_io as io
from .m1_inputs import read_raster

__all__ = ['validate', 'load_artifacts']
ARTIFACTS = ('valid_mask.tif', *io.ARTIFACTS)


def validate(m):
    if m.get('model') == 'M3':
        io.fail('integration_pending', 'M3 terrain artifact validation is not implemented')
    required = {'schema_version', 'model', 'support_policy', 'status', 'availability',
                'source_kind', 'readiness', 'grid', 'outlet', 'area_km2', 'warnings',
                'predictors', 'sources_sha256', 'prepared_sha256', 'tool', 'artifacts_sha256', 'coverage'}
    if not required <= m.keys() or m['model'] != 'M1' or m['status'] != 'complete' or m['support_policy'] != 'common_valid_v1':
        io.fail('invalid_input', 'Invalid version-2 predictor contract')
    if m['source_kind'] not in ('real', 'mixed', 'synthetic') or not io.number(m['area_km2']) or m['area_km2'] <= 0:
        io.fail('invalid_input', 'Invalid predictor source/area')
    if (not isinstance(m['warnings'], list) or any(not isinstance(v, str) for v in m['warnings'])
            or (not .2 <= m['area_km2'] <= 8) != ('area_outside_study_range' in m['warnings'])):
        io.fail('invalid_input', 'Invalid predictor warnings')
    for name in ('grid', 'outlet', 'readiness', 'predictors', 'tool', 'coverage'):
        if not isinstance(m[name], dict):
            io.fail('invalid_input', 'Invalid predictor metadata')
    for name in ('sources_sha256', 'prepared_sha256', 'artifacts_sha256'):
        hashes = m[name]
        if not isinstance(hashes, dict) or not hashes or any(not isinstance(k, str) or not io.hash_value(v) for k, v in hashes.items()):
            io.fail('invalid_input', 'Invalid predictor hashes')
    if set(m['artifacts_sha256']) != set(ARTIFACTS) or not io.hash_value(m['tool'].get('sha256')):
        io.fail('invalid_input', 'Invalid predictor artifact/tool identity')
    coverage = m['coverage']
    total, count = coverage.get('total_cells'), coverage.get('valid_cells')
    if (type(total) is not int or type(count) is not int or not 0 <= count <= total <= 10_000_000 or total == 0
            or type(coverage.get('excluded_cells')) is not int or coverage['excluded_cells'] != total-count
            or not io.number(coverage.get('valid_fraction')) or coverage['valid_fraction'] != count/total
            or coverage.get('policy') != 'common_valid_v1' or coverage.get('mask') != 'valid_mask.tif'):
        io.fail('invalid_input', 'Inconsistent common coverage')
    io._validate_grid_outlet(m, total)
    preds = m['predictors']
    if set(preds) != {'T', 'F', 'S'}:
        io.fail('invalid_input', 'Expected T/F/S predictors')
    units = ('fraction', 'normalized_dNBR', 'USLE_customary')
    available = 0
    for key, unit in zip(('T', 'F', 'S'), units):
        p = preds[key]
        if not isinstance(p, dict) or not {'value', 'status', 'reason', 'support', 'units'} <= p.keys() or p['units'] != unit or {'lower', 'upper'} & p.keys():
            io.fail('invalid_input', 'Invalid common-support predictor')
        expected_count = count
        support = p['support']
        if (not isinstance(support, dict) or type(support.get('total_cells')) is not int
                or type(support.get('valid_cells')) is not int or not io.number(support.get('coverage_fraction'))
                or support != dict(total_cells=total, valid_cells=expected_count, coverage_fraction=expected_count/total)):
            io.fail('invalid_input', 'Predictor support differs from model domain')
        if p['status'] == 'available':
            value = p['value']
            if not io.number(value) or p['reason'] is not None or expected_count == 0:
                io.fail('invalid_input', 'Inconsistent available predictor')
            if key in ('T', 'S') and not 0 <= value <= 1:
                io.fail('invalid_input', 'Predictor out of range')
            available += 1
        elif p['status'] != 'unavailable' or p['value'] is not None or not isinstance(p['reason'], str) or not p['reason']:
            io.fail('invalid_input', 'Inconsistent unavailable predictor')
        if (count > 0) != (p['status'] == 'available') or (count == 0 and p['reason'] != 'zero_valid_support'):
            io.fail('invalid_input', 'Common support and point availability disagree')
    if m['availability'] != ('complete' if available == 3 else 'partial' if available else 'unavailable'):
        io.fail('invalid_input', 'Inconsistent predictor availability')
    _validate_m1_summary(m, total)
    if count:
        io._validate_k(m.get('k_provenance'))


def _validate_m1_summary(m, total):
    summary = m['predictors']['T'].get('wbt_summary')
    if not isinstance(summary, dict) or not isinstance(summary.get('counts'), dict):
        io.fail('invalid_input', 'Missing raw WBT summary')
    counts = summary['counts']
    keys = ('intersection_true', 'intersection_false', 'intersection_unknown')
    if any(type(counts.get(k)) is not int or not 0 <= counts[k] <= total for k in keys):
        io.fail('invalid_input', 'Invalid raw WBT counts')
    unknown = counts['intersection_unknown']
    # Validate the retained raw summary against raw support, not the new point.
    raw = dict(value=summary.get('T'), lower=summary.get('T_lower'), upper=summary.get('T_upper'),
               support={'valid_cells': total-unknown}, wbt_summary=summary)
    io._validate_predictor_geometry({**m, 'predictors': {'T': raw}}, total)


def load_artifacts(root, m, consumed, limits):
    for name in ARTIFACTS:
        limit = io.MAX_TEXT if name.endswith('.json') else io.MAX_PREDICTOR_BYTES
        path = io.regular(root/name, limit)
        actual = io.digest(path, limit)
        if actual != m['artifacts_sha256'][name]:
            io.fail('provenance_mismatch', 'Predictor artifact digest mismatch')
        consumed[str(path)] = actual
        if limits is not None:
            limits[str(path)] = limit
    values, valid, grid = read_raster(root/'valid_mask.tif', categorical=True)
    with rasterio.open(root/'valid_mask.tif') as ds:
        if ds.dtypes != ('uint8',) or ds.nodata != 255:
            io.fail('invalid_input', 'Invalid exact support mask encoding')
    c = m['coverage']
    if (grid != m['grid'] or np.any(valid & ~np.isin(values, [0, 1]))
            or int(valid.sum()) != c['total_cells'] or int(np.count_nonzero(valid & (values == 1))) != c['valid_cells']
            or np.any(~valid & (values != 255))):
        io.fail('invalid_input', 'Exact support mask differs from coverage')
    summary = io.read_json(root/'wbt/summary.json')
    if summary != m['predictors']['T'].get('wbt_summary'):
        io.fail('invalid_input', 'Predictor summary mismatch')
    intersection, determined, raw_grid = read_raster(root/'wbt/intersection.tif', categorical=True)
    common = valid & (values == 1)
    if not np.array_equal(valid, determined):
        io.fail('invalid_input', 'Exact support mask domain differs from raw watershed')
    if (raw_grid != grid or np.any(common & (~determined | ~np.isin(intersection, [0, 1])))
            or (common.any() and m['predictors']['T']['value'] != np.count_nonzero(common & (intersection == 1))/int(common.sum()))):
        io.fail('invalid_input', 'Common T differs from raw intersection')
