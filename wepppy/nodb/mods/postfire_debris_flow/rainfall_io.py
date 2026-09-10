"""Bounded trusted-local rainfall files; no provenance-directed filesystem reads."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import stat

import pyarrow as pa
import pyarrow.parquet as pq

__all__ = ['RainfallError']
MAX_BYTES = 64 * 1024 * 1024
MAX_TEXT = 1024 * 1024
MAX_DECODED = 128 * 1024 * 1024
HASH = re.compile(r'[0-9a-f]{64}\Z')
ARTIFACTS = ('wbt/intersection.tif', 'wbt/slope.tif', 'wbt/summary.json', 'wbt/support.tif')


class RainfallError(ValueError):
    """An expected local boundary failure with a stable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code, message):
    raise RainfallError(code, message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def regular(path, limit=MAX_BYTES):
    p = Path(path).absolute()
    if '..' in p.parts or any(q.is_symlink() for q in (p, *p.parents)):
        fail('invalid_input', 'Symlinks and parent traversal are unsupported')
    info = p.stat()
    if not stat.S_ISREG(info.st_mode):
        fail('invalid_input', 'Expected a regular local file')
    if info.st_size > limit:
        fail('resource_limit', f'File exceeds byte limit: {p}')
    return p


def digest(path):
    h = hashlib.sha256()
    with regular(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def hash_value(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def pinned(path, expected, consumed, limit=MAX_BYTES):
    p = regular(path, limit)
    key = str(p)
    if key not in expected or not hash_value(expected[key]):
        fail('missing_provenance', f'Expected SHA-256 required: {p}')
    actual = digest(p)
    if actual != expected[key]:
        fail('provenance_mismatch', f'SHA-256 mismatch: {p}')
    consumed[key] = actual
    return p


def recheck(consumed):
    for path, expected in consumed.items():
        if digest(path) != expected:
            fail('source_changed', f'Source changed: {path}')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('invalid_input', 'Duplicate JSON key')
        result[key] = value
    return result


def _json_float(text):
    value = float(text)
    if not math.isfinite(value):
        fail('invalid_input', 'Nonfinite JSON number')
    return value


def read_json(path):
    p = regular(path, MAX_TEXT)
    try:
        result = json.loads(p.read_text(), object_pairs_hook=_pairs, parse_float=_json_float,
                            parse_constant=lambda x: fail('invalid_input', 'Nonfinite JSON'))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise RainfallError('invalid_input', 'Malformed JSON') from exc
    if not isinstance(result, dict):
        fail('invalid_input', 'Expected JSON object')
    return result


def write_json(path, value):
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if len(data.encode()) > MAX_TEXT:
        fail('resource_limit', 'JSON exceeds limit')
    with Path(path).open('x') as stream:
        stream.write(data)


def read_table(path, *, max_rows, numeric=False, schema=None):
    p = regular(path)
    try:
        # A file object prevents directory/dataset discovery and external URI inference.
        with p.open('rb') as stream:
            f = pq.ParquetFile(stream, thrift_string_size_limit=MAX_TEXT,
                               thrift_container_size_limit=100_000)
            m = f.metadata
            if m.num_rows > max_rows or m.num_columns > 64:
                fail('resource_limit', 'Parquet dimensions exceed limits')
            if sum(m.row_group(i).total_byte_size for i in range(m.num_row_groups)) > MAX_DECODED:
                fail('resource_limit', 'Parquet decoded size exceeds limit')
            s = f.schema_arrow
            if len(s.names) != len(set(s.names)):
                fail('invalid_input', 'Duplicate parquet columns')
            if numeric and any(not (pa.types.is_integer(v.type) or pa.types.is_floating(v.type)) for v in s):
                fail('invalid_input', 'Climate columns must be primitive numbers')
            if schema is not None and not s.equals(schema, check_metadata=False):
                fail('invalid_input', 'Unexpected result table schema')
            for i in range(m.num_row_groups):
                for j in range(m.num_columns):
                    if m.row_group(i).column(j).file_path:
                        fail('invalid_input', 'External parquet chunks are forbidden')
            table = f.read(use_threads=False)
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError) as exc:
        raise RainfallError('invalid_input', 'Malformed parquet') from exc
    if table.nbytes > MAX_DECODED:
        fail('resource_limit', 'Decoded parquet exceeds limit')
    return table.replace_schema_metadata(None)


def load_predictors(path, expected, consumed):
    p = pinned(path, expected, consumed, MAX_TEXT)
    m = read_json(p)
    validate_predictors(m)
    if set(m['artifacts_sha256']) != set(ARTIFACTS):
        fail('invalid_input', 'Unexpected predictor artifact names')
    # Only fixed artifact paths are read. Source and preparation paths are provenance.
    for name in ARTIFACTS:
        artifact = regular(p.parent / name)
        actual = digest(artifact)
        if actual != m['artifacts_sha256'][name]:
            fail('provenance_mismatch', 'Predictor artifact digest mismatch')
        consumed[str(artifact)] = actual
    summary = read_json(p.parent / 'wbt/summary.json')
    t = m['predictors']['T']
    if summary != t.get('wbt_summary') or summary.get('status') != 'complete' or summary.get('T') != t['value']:
        fail('invalid_input', 'Predictor summary mismatch')
    return m


def _validate_predictor_geometry(m, total):
    grid = m['grid']
    shape, transform, crs = (grid.get(k) for k in ('shape','transform','crs'))
    if (not isinstance(shape,list) or len(shape) != 2 or any(type(v) is not int or v <= 0 for v in shape)
            or shape[0]*shape[1] > 10_000_000 or total > shape[0]*shape[1]
            or not isinstance(transform,list) or len(transform) != 6 or not all(number(v) for v in transform)
            or not isinstance(crs,str) or re.fullmatch(r'EPSG:32[67][0-9]{2}',crs) is None
            or not 1 <= int(crs[-2:]) <= 60):
        fail('invalid_input', 'Invalid predictor grid')
    a,b,c,d,e,f = transform
    if a <= 0 or b != 0 or d != 0 or e != -a:
        fail('invalid_input', 'Predictor grid must use square north-up meter cells')
    if not math.isclose(m['area_km2'],total*a*a/1e6,rel_tol=1e-12):
        fail('invalid_input', 'Predictor area and support disagree')
    outlet = m['outlet']
    if outlet.get('type') == 'FeatureCollection':
        features = outlet.get('features')
        if not isinstance(features,list) or len(features) != 1 or not isinstance(features[0],dict):
            fail('invalid_input', 'Expected one assessment outlet')
        outlet = features[0]
    if outlet.get('type') == 'Feature':
        outlet = outlet.get('geometry')
    if not isinstance(outlet,dict) or outlet.get('type') != 'Point':
        fail('invalid_input', 'Expected Point assessment outlet')
    coordinates = outlet.get('coordinates')
    if not isinstance(coordinates,list) or len(coordinates) != 2 or not all(number(v) for v in coordinates):
        fail('invalid_input', 'Invalid outlet coordinates')
    t = m['predictors']['T']
    summary = t.get('wbt_summary')
    if not isinstance(summary,dict):
        fail('invalid_input', 'Missing WBT summary')
    counts = summary.get('counts')
    if (summary.get('schema_version') != 1 or summary.get('tool') != 'StaleySlopeSbs'
            or not isinstance(counts,dict)
            or not {'basin','intersection_true','intersection_false','intersection_unknown'} <= counts.keys()
            or any(type(v) is not int or not 0 <= v <= total for v in counts.values())):
        fail('invalid_input', 'Invalid WBT summary counts')
    expected_grid = {'rows':shape[0],'columns':shape[1],'epsg':int(crs[5:]),
                     'resolution_m':a,'west':c,'north':f}
    expected_parameters = {'algorithm':'Horn 3x3','dem_source':'raw','edges':'nine-valid-cells',
                           'threshold_degrees':23,'elevation_units':'m','sbs_classes':[0,1,2,3]}
    if (summary.get('grid') != expected_grid or summary.get('parameters') != expected_parameters
            or summary.get('status') != 'complete' or summary.get('T') != t['value']):
        fail('invalid_input', 'WBT summary grid/parameters differ')
    y, n, u = (counts[k] for k in ('intersection_true','intersection_false','intersection_unknown'))
    if (counts['basin'] != total or y+n+u != total or t['lower'] != y/total
            or t['upper'] != (y+u)/total or t['value'] != (None if u else y/total)
            or t['support']['valid_cells'] != total-u
            or summary.get('T_lower') != t['lower'] or summary.get('T_upper') != t['upper']):
        fail('invalid_input', 'Inconsistent WBT T bounds/support')


def validate_predictors(m):
    required = {'schema_version', 'status', 'availability', 'source_kind', 'readiness',
                'grid', 'outlet', 'area_km2', 'warnings', 'predictors', 'sources_sha256',
                'prepared_sha256', 'tool', 'k_provenance', 'artifacts_sha256'}
    if not required <= m.keys() or type(m['schema_version']) is not int or m['schema_version'] != 1 or m['status'] != 'complete':
        fail('invalid_input', 'Expected completed version-1 M1 predictor manifest')
    if m['source_kind'] not in ('real', 'mixed', 'synthetic') or not number(m['area_km2']) or m['area_km2'] <= 0:
        fail('invalid_input', 'Invalid predictor source/area')
    if not isinstance(m['warnings'], list) or any(not isinstance(v, str) for v in m['warnings']):
        fail('invalid_input', 'Invalid predictor warnings')
    if (not .2 <= m['area_km2'] <= 8) != ('area_outside_study_range' in m['warnings']):
        fail('invalid_input', 'Area warning is inconsistent')
    if any(not isinstance(m[k], dict) for k in ('grid', 'outlet', 'readiness', 'predictors', 'tool')):
        fail('invalid_input', 'Invalid predictor metadata objects')
    for key in ('sources_sha256', 'prepared_sha256', 'artifacts_sha256'):
        hashes = m[key]
        if not isinstance(hashes, dict) or not hashes or any(not isinstance(k, str) or not hash_value(v) for k, v in hashes.items()):
            fail('invalid_input', f'Invalid {key}')
    if not hash_value(m['tool'].get('sha256')):
        fail('invalid_input', 'Invalid tool digest')
    preds = m['predictors']
    if set(preds) != {'T', 'F', 'S'}:
        fail('invalid_input', 'Expected T/F/S predictors')
    available = 0
    total = None
    for key, units in (('T', 'fraction'), ('F', 'normalized_dNBR'), ('S', 'USLE_customary')):
        v = preds[key]
        if not isinstance(v, dict) or not {'value','status','reason','units','support'} <= v.keys() or v['units'] != units:
            fail('invalid_input', f'Invalid {key} predictor')
        support = v['support']
        if not isinstance(support, dict) or not {'total_cells','valid_cells','coverage_fraction'} <= support.keys():
            fail('invalid_input', 'Invalid predictor support')
        n, c, fraction = (support[x] for x in ('total_cells','valid_cells','coverage_fraction'))
        if type(n) is not int or type(c) is not int or not 0 <= c <= n <= 10_000_000 or n == 0 or not number(fraction) or fraction != c/n:
            fail('invalid_input', 'Inconsistent predictor coverage')
        if total is not None and n != total:
            fail('invalid_input', 'Predictor domains differ')
        total = n
        if v['status'] == 'available':
            if not number(v['value']) or v['reason'] is not None or c == 0:
                fail('invalid_input', 'Inconsistent available predictor')
            if key in ('T','S') and not 0 <= v['value'] <= 1:
                fail('invalid_input', 'Predictor out of range')
            if key in ('T','S') and c != n:
                fail('invalid_input', 'Incomplete point predictor coverage')
            available += 1
        elif v['status'] != 'unavailable' or v['value'] is not None or not isinstance(v['reason'], str) or not v['reason']:
            fail('invalid_input', 'Inconsistent unavailable predictor')
    t = preds['T']
    if not all(number(t.get(k)) for k in ('lower','upper')) or not 0 <= t['lower'] <= t['upper'] <= 1:
        fail('invalid_input', 'Invalid T bounds')
    if t['value'] is not None and not t['lower'] == t['value'] == t['upper']:
        fail('invalid_input', 'Inconsistent point T')
    if m['availability'] != ('complete' if available == 3 else 'partial' if available else 'unavailable'):
        fail('invalid_input', 'Inconsistent predictor availability')
    _validate_predictor_geometry(m, total)
    if preds['F']['value'] is not None and preds['F'].get('observed_mean') != preds['F']['value']:
        fail('invalid_input', 'Available F must equal its observed mean')
    if preds['S']['value'] is not None:
        _validate_k(m['k_provenance'])
        if preds['S'].get('multiplier') != 1 or preds['S'].get('observed_mean') != preds['S']['value']:
            fail('invalid_input', 'Available S must preserve multiplier and observed mean')


def _validate_k(k):
    required = {'selected_modes','artifacts','statistic','near_surface_depths',
                'near_surface_weights_cm','mode_contract','gap_fill_policy','gap_fill_summary'}
    if not isinstance(k,dict) or not required <= k.keys():
        fail('invalid_input', 'Available S requires K provenance')
    if (not isinstance(k['selected_modes'],list) or 'polaris_nomograph' not in k['selected_modes']
            or not isinstance(k['artifacts'],dict) or k['artifacts'].get('nomograph') != 'rusle/k_polaris_nomograph.tif'
            or k['statistic'] != 'mean' or k['near_surface_depths'] != ['0_5','5_15']
            or k['near_surface_weights_cm'] != {'0_5':5.,'5_15':10.}
            or any(not isinstance(k[name],dict) or not k[name] for name in ('mode_contract','gap_fill_policy','gap_fill_summary'))):
        fail('invalid_input', 'Invalid accepted K provenance')
    mode = k['mode_contract'].get('polaris_nomograph')
    expected = {'vfs_source':'rusle2_estimated_from_sand', 'structure_class_mapping':'modeled_texture_proxy_v1',
                'permeability_class_mapping':'modeled_ksat_proxy_v1'}
    if not isinstance(mode,dict) or any(mode.get(key) != value for key,value in expected.items()):
        fail('invalid_input', 'Unsupported K parameterization')
    fragment = mode.get('cfvo_profile_fragment_adjustment')
    if not isinstance(fragment,dict) or not isinstance(fragment.get('status'),str) or not fragment['status']:
        fail('invalid_input', 'Missing K fragment provenance')
