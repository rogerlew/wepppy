"""Validate common-support products without weakening the offline v1 reader."""
import math
import numpy as np
import rasterio

from . import rainfall_io as io
from .m1_inputs import read_raster

__all__ = ['validate', 'load_artifacts']
ARTIFACTS = ('valid_mask.tif', *io.ARTIFACTS)
M3_ARTIFACTS = ('valid_mask.tif','wbt/relief.tif','wbt/area.tif','wbt/coverage.tif',
                'wbt/summary.json','soil/thickness_cm.tif','soil/source.tif','soil/manifest.json',
                'terrain/manifest.json','terrain/wbt/watershed.tif','prepared/sbs.tif','prepared/domain.tif')


def _artifacts(m):
    if m.get('schema_version') == 3:
        return (*ARTIFACTS, 'kf/kf.tif', 'kf/manifest.json')
    return ARTIFACTS if m['model'] == 'M1' else M3_ARTIFACTS


def validate(m):
    required = {'schema_version', 'model', 'support_policy', 'status', 'availability',
                'source_kind', 'readiness', 'grid', 'outlet', 'area_km2', 'warnings',
                'predictors', 'sources_sha256', 'prepared_sha256', 'tool', 'artifacts_sha256', 'coverage'}
    if not required <= m.keys() or m['model'] not in ('M1','M3') or m['status'] != 'complete' or m['support_policy'] != 'common_valid_v1':
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
    if m.get('schema_version') == 3:
        from .kf_source import POLICY, validate_manifest
        provenance = m.get('kf_provenance')
        if (m['model'] != 'M1' or m.get('soil_policy') != POLICY or 'k_provenance' in m
                or not isinstance(provenance,dict) or set(provenance) != {'manifest','sha256'}
                or not io.hash_value(provenance['sha256'])):
            io.fail('invalid_input','Invalid version-3 Kf predictor provenance')
        validate_manifest(provenance['manifest'])
        if (provenance['manifest']['target_grid'] != m['grid']
                or provenance['sha256'] != m['artifacts_sha256'].get('kf/manifest.json')
                or provenance['manifest']['artifacts_sha256']['kf.tif'] != m['artifacts_sha256'].get('kf/kf.tif')):
            io.fail('provenance_mismatch','Kf provenance differs from predictor artifacts')
    inventory = _artifacts(m)
    if set(m['artifacts_sha256']) != set(inventory) or not io.hash_value(m['tool'].get('sha256')):
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
    units = ('fraction', 'normalized_dNBR', 'USLE_customary') if m['model'] == 'M1' else ('dimensionless','fraction','thickness_cm_div_254')
    available = 0
    for key, unit in zip(('T', 'F', 'S'), units):
        p = preds[key]
        if not isinstance(p, dict) or not {'value', 'status', 'reason', 'support', 'units'} <= p.keys() or p['units'] != unit or {'lower', 'upper'} & p.keys():
            io.fail('invalid_input', 'Invalid common-support predictor')
        full_terrain = m['model'] == 'M3' and key == 'T'
        expected_count = (total if p['status'] == 'available' else 0) if full_terrain else count
        support = p['support']
        if (not isinstance(support, dict) or type(support.get('total_cells')) is not int
                or type(support.get('valid_cells')) is not int or not io.number(support.get('coverage_fraction'))
                or support != dict(total_cells=total, valid_cells=expected_count, coverage_fraction=expected_count/total)):
            io.fail('invalid_input', 'Predictor support differs from model domain')
        if p['status'] == 'available':
            value = p['value']
            if not io.number(value) or p['reason'] is not None or expected_count == 0:
                io.fail('invalid_input', 'Inconsistent available predictor')
            bounded = key in ('T','S') if m['model'] == 'M1' else key == 'F'
            if (bounded and not 0 <= value <= 1) or (m['model'] == 'M3' and value < 0):
                io.fail('invalid_input', 'Predictor out of range')
            available += 1
        elif p['status'] != 'unavailable' or p['value'] is not None or not isinstance(p['reason'], str) or not p['reason']:
            io.fail('invalid_input', 'Inconsistent unavailable predictor')
        if not full_terrain and ((count > 0) != (p['status'] == 'available') or (count == 0 and p['reason'] != 'zero_valid_support')):
            io.fail('invalid_input', 'Common support and point availability disagree')
    if m['availability'] != ('complete' if available == 3 else 'partial' if available else 'unavailable'):
        io.fail('invalid_input', 'Inconsistent predictor availability')
    if m['model'] == 'M1':
        _validate_m1_summary(m, total)
        if count and m['schema_version'] == 2:
            io._validate_k(m.get('k_provenance'))
    else:
        if not {'terrain/manifest.json','soil/manifest.json'} <= m['prepared_sha256'].keys():
            io.fail('invalid_input', 'Missing prepared M3 identities')
        _validate_m3_summary(m,total)
        primary,fallback = coverage.get('primary_valid_cells'),coverage.get('fallback_valid_cells')
        if (m.get('soil_policy') != 'recorded_depth_v1' or type(primary) is not int
                or type(fallback) is not int or min(primary,fallback) < 0 or primary+fallback != count):
            io.fail('invalid_input', 'Invalid M3 soil policy or common source contributions')


def _validate_m3_summary(m,total):
    t = m['predictors']['T']
    summary = t.get('wbt_summary')
    if not isinstance(summary,dict):
        io.fail('invalid_input', 'Missing M3 terrain summary')
    area, relief, cells = summary.get('area_m2'),summary.get('relief_m'),summary.get('full_upstream_cells')
    outlet = summary.get('outlet')
    if (type(summary.get('schema_version')) is not int or summary['schema_version'] != 1 or summary.get('status') != 'complete' or summary.get('tool') != 'D8UpstreamRelief'
            or summary.get('tool_sha256') != m['tool']['sha256'] or summary.get('tool_version') != m['tool'].get('version')
            or not isinstance(summary.get('tool_version'),str) or not summary['tool_version'] or summary.get('grid') != m['grid']
            or type(cells) is not int or not 0 < cells <= 10_000_000 or not io.number(area) or area <= 0
            or not io.number(relief) or relief < 0 or area != cells*m['grid']['transform'][0]**2
            or not isinstance(outlet,list) or len(outlet) != 2 or any(type(v) is not int for v in outlet)
            or any(not 0 <= v < size for v,size in zip(outlet,m['grid']['shape']))
            or type(summary.get('terrain_valid')) is not bool):
        io.fail('invalid_input', 'Invalid M3 terrain summary')
    if summary['terrain_valid']:
        if cells != total or summary.get('reason') is not None or t['value'] != relief/math.sqrt(area):
            io.fail('invalid_input', 'M3 full-basin terrain differs from predictor')
    elif (summary.get('reason') not in ('terrain_potentially_truncated','watershed_area_mismatch')
          or t['value'] is not None or t['reason'] != summary['reason']):
        io.fail('invalid_input', 'Invalid unavailable M3 terrain')


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
    for name in _artifacts(m):
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
    if m['model'] == 'M3':
        _load_m3(root,m,values,valid,consumed,limits)
        return
    intersection, determined, raw_grid = read_raster(root/'wbt/intersection.tif', categorical=True)
    common = valid & (values == 1)
    if not np.array_equal(valid, determined):
        io.fail('invalid_input', 'Exact support mask domain differs from raw watershed')
    if (raw_grid != grid or np.any(common & (~determined | ~np.isin(intersection, [0, 1])))
            or (common.any() and m['predictors']['T']['value'] != np.count_nonzero(common & (intersection == 1))/int(common.sum()))):
        io.fail('invalid_input', 'Common T differs from raw intersection')
    if m['schema_version'] == 3:
        from .kf_source import read_prepared
        k, usable, provenance = read_prepared(root/'kf/kf.tif',root/'kf/manifest.json',grid)
        if (provenance != m['kf_provenance']['manifest'] or np.any(common & ~usable)
                or (common.any() and float(np.mean(k[common],dtype=np.float64)) != m['predictors']['S']['value'])):
            io.fail('provenance_mismatch','Common S differs from the saved Kf raster')


def _load_m3(root,m,mask,domain,consumed,limits):
    summary = m['predictors']['T']['wbt_summary']
    original,original_valid,original_grid = read_raster(root/'prepared/domain.tif',categorical=True)
    if (original_grid != m['grid'] or not original_valid.all() or not np.isin(original,[0,1]).all()
            or not np.array_equal(domain,original == 1)):
        io.fail('invalid_input', 'M3 mask differs from prepared authoritative watershed')
    from .m3_integration import _outlet
    if _outlet(m['outlet'],m['grid'],m['coverage']['total_cells']) != summary['outlet']:
        io.fail('invalid_input', 'M3 outlet geometry differs from native sampled cell')
    terrain_path = root/'terrain/manifest.json'
    expected = {str(terrain_path):m['prepared_sha256']['terrain/manifest.json']}
    io.pinned(terrain_path,expected,consumed,io.MAX_TEXT)
    terrain = io.read_json(terrain_path)
    if (terrain.get('status') != 'complete' or terrain.get('summary') != summary
            or not isinstance(terrain.get('artifacts_sha256'),dict)):
        io.fail('invalid_input', 'Prepared M3 terrain differs from summary')
    routed_path = root/'terrain/wbt/watershed.tif'
    identity = terrain.get('artifacts_sha256',{}).get('wbt/watershed.tif')
    if not io.hash_value(identity):
        io.fail('invalid_input', 'Missing routed watershed identity')
    io.pinned(routed_path,{str(routed_path):identity},consumed,io.MAX_PREDICTOR_BYTES)
    if limits is not None:
        limits[str(terrain_path)] = io.MAX_TEXT
        limits[str(routed_path)] = io.MAX_PREDICTOR_BYTES
    routed,routed_valid,routed_grid = read_raster(routed_path,categorical=True)
    if routed_grid != m['grid'] or (summary['terrain_valid'] and not np.array_equal(routed_valid & (routed > 0),domain)):
        io.fail('invalid_input', 'M3 mask differs from native routed watershed')
    outlet = tuple(summary['outlet'])
    if not domain[outlet]:
        io.fail('invalid_input', 'M3 outlet is outside the watershed mask')
    for name,key in (('area','area_m2'),('relief','relief_m'),('coverage',None)):
        values,valid,grid = read_raster(root/f'wbt/{name}.tif',categorical=name == 'coverage')
        if grid != m['grid'] or not valid[outlet] or (key is not None and values[outlet] != summary[key]):
            io.fail('invalid_input', 'Native terrain artifact differs from M3 summary')
        if name == 'coverage':
            reason = ('terrain_potentially_truncated' if values[outlet] == 1 else
                      'watershed_area_mismatch' if summary['full_upstream_cells'] != m['coverage']['total_cells'] else None)
            if values[outlet] not in (0,1) or summary['reason'] != reason:
                io.fail('invalid_input', 'Native terrain coverage differs from M3 availability')
    source,valid,grid = read_raster(root/'soil/source.tif',categorical=True)
    thickness,usable,thickness_grid = read_raster(root/'soil/thickness_cm.tif',continuous_missing=True)
    common = domain & (mask == 1)
    sbs,sbs_valid,sbs_grid = read_raster(root/'prepared/sbs.tif',categorical=True)
    if (sbs_grid != m['grid'] or not np.isin(sbs[sbs_valid],[0,1,2,3]).all()
            or not np.array_equal(common,domain & sbs_valid & usable & np.isin(source,[1,2]))):
        io.fail('invalid_input', 'M3 exact common support differs from prepared SBS and soil')
    if common.any() and m['predictors']['F']['value'] != np.count_nonzero(common & (sbs >= 2))/int(common.sum()):
        io.fail('invalid_input', 'M3 F differs from prepared SBS')
    if (grid != m['grid'] or thickness_grid != grid or not np.array_equal(valid,domain)
            or not np.isin(source[valid],[0,1,2]).all() or np.any(common & (~usable | ~np.isin(source,[1,2])))
            or not np.array_equal(usable,domain & np.isin(source,[1,2])) or np.any(usable & (thickness < 0))):
        io.fail('invalid_input', 'M3 soil artifacts differ from support')
    for label,value in (('primary',1),('fallback',2)):
        if int(np.count_nonzero(common & (source == value))) != m['coverage'][label+'_valid_cells']:
            io.fail('invalid_input', 'M3 common source counts disagree')
    if common.any() and float(np.mean(thickness[common],dtype=np.float64))/254 != m['predictors']['S']['value']:
        io.fail('invalid_input', 'M3 S differs from common thickness')
    soil = io.read_json(root/'soil/manifest.json')
    if (soil.get('status') != 'complete' or soil.get('policy') != m['soil_policy']
            or soil.get('grid') != grid or soil.get('units') != 'cm'
            or not isinstance(soil.get('artifacts_sha256'),dict)
            or m['prepared_sha256']['soil/manifest.json'] != m['artifacts_sha256']['soil/manifest.json']):
        io.fail('invalid_input', 'M3 soil manifest differs')
    for name in ('source.tif','thickness_cm.tif'):
        if soil.get('artifacts_sha256',{}).get(name) != m['artifacts_sha256']['soil/'+name]:
            io.fail('invalid_input', 'M3 soil manifest raster identity differs')
    counts = {label:int(np.count_nonzero(source == value)) for label,value in
              (('primary',1),('fallback',2),('unavailable',0),('outside',255))}
    if soil.get('source_cells') != counts:
        io.fail('invalid_input', 'M3 soil manifest source counts differ')
