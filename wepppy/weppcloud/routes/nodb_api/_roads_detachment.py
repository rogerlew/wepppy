"""Read-only coherent map view; roads-gl-dashboard-contract.md."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pyarrow.parquet as pq
from pyproj import CRS, Transformer

from wepppy.wepp.interchange import _roads_lifecycle as lifecycle
from wepppy.nodb.mods.roads._segment_loss_summary import SCHEMA

__all__ = ['read_detachment_view']

SEGMENTS = Path('wepp/roads/segments')
SUMMARY = Path('wepp/roads/output/interchange/roads_segment_loss_summary.parquet')
PROFILE_FIELDS = ('segment_run_id', 'profile_scope', 'soil_loss_kg', 'modeled_area_m2',
                  'soil_loss_density_kg_m2', 'simulation_years', 'design', 'segment_length_m')
REQUIRED = ('segment_id', 'summary_policy', *PROFILE_FIELDS[:-2])


def _source(root, relative):
    # Prepared metadata is outside current_read's output receipt. Apply the same
    # no-alias boundary to every file used in this joined materialization.
    path = root / relative
    if path.resolve() != path:
        raise ValueError('Roads map source cannot alias another resource.')
    return path


def _json(root, relative):
    return json.loads(_source(root, relative).read_text())


def _number(value, field, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'Invalid Roads {field}.')
    if positive and value <= 0:
        raise ValueError(f'Roads {field} must be positive.')
    return value


def _profile_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).strip():
        raise ValueError('Invalid Roads profile ID.')
    return str(value)


def _transform_geometry(geometry, transformer):
    if not isinstance(geometry, dict) or geometry.get('type') not in ('LineString', 'MultiLineString'):
        raise ValueError('Prepared Roads geometry must contain lines.')
    lines = [geometry.get('coordinates')] if geometry['type'] == 'LineString' else geometry.get('coordinates')
    if not isinstance(lines, list) or not lines:
        raise ValueError('Prepared Roads coordinates are missing.')
    result = []
    for line in lines:
        if not isinstance(line, list) or len(line) < 2:
            raise ValueError('Prepared Roads line has too few coordinates.')
        points = []
        for point in line:
            if not isinstance(point, list) or len(point) < 2:
                raise ValueError('Invalid prepared Roads coordinate.')
            x, y = (_number(point[i], 'coordinate') for i in (0, 1))
            lon, lat = transformer.transform(x, y, errcheck=True)
            if not math.isfinite(lon) or not math.isfinite(lat) or abs(lon) > 180 or abs(lat) > 90:
                raise ValueError('Prepared Roads coordinates cannot be mapped to longitude/latitude.')
            points.append([lon, lat])
        result.append(points)
    return {'type': geometry['type'], 'coordinates': result[0] if geometry['type'] == 'LineString' else result}


def _materialize(root):
    receipt = lifecycle.require_current(root)
    geometry = _json(root, SEGMENTS / 'roads.inslope.monotonic.geojson')
    prepare = _json(root, SEGMENTS / 'roads.inslope.summary.json')
    manifest = _json(root, SEGMENTS / 'roads.segment.pass.manifest.json')
    if not isinstance(geometry, dict) or geometry.get('type') != 'FeatureCollection':
        raise ValueError('Invalid prepared Roads feature collection.')
    ids = lifecycle.segment_ids(geometry.get('features'))
    if not isinstance(prepare, dict) or not prepare.get('input_crs'):
        raise ValueError('Prepared Roads effective input CRS is missing.')
    source_crs = CRS.from_user_input(prepare['input_crs'])
    if geometry.get('crs'):
        declaration = geometry['crs']
        if not isinstance(declaration, dict) or declaration.get('type') != 'name':
            raise ValueError('Invalid prepared Roads CRS declaration.')
        properties = declaration.get('properties')
        if not isinstance(properties, dict) or not properties.get('name'):
            raise ValueError('Invalid prepared Roads CRS name.')
        declared = CRS.from_user_input(properties['name'])
        if not source_crs.equals(declared, ignore_axis_order=True):
            raise ValueError('Prepared Roads CRS conflicts with effective input CRS.')
    transformer = Transformer.from_crs(source_crs, CRS.from_epsg(4326), always_xy=True)
    if not isinstance(manifest, list):
        raise ValueError('Invalid Roads profile manifest.')
    completed, incomplete = {}, {}
    seen = set()
    for record in manifest:
        if not isinstance(record, dict):
            raise ValueError('Invalid Roads manifest record.')
        status = record.get('status', 'completed')
        if status not in ('completed', 'skipped', 'failed'):
            raise ValueError('Unknown Roads profile status.')
        segment = record.get('segment_id')
        if record.get('segment_run_id') is not None:
            key = _profile_id(record['segment_run_id'])
            if key in seen:
                raise ValueError('Duplicate Roads manifest profile ID.')
            seen.add(key)
        if status == 'completed':
            key = _profile_id(record.get('segment_run_id'))
            completed[key] = record
            if record.get('design') != 'outslope_unrutted_remainder' and segment not in ids:
                raise ValueError('Completed Roads profile has no prepared geometry.')
        else:
            incomplete.setdefault(segment, []).append(str(record.get('reason') or status))

    summary_path = _source(root, SUMMARY)
    unavailable = receipt['is_single_storm'] and not summary_path.exists()
    rows = []
    if not unavailable:
        parquet = pq.ParquetFile(summary_path)
        if not set(REQUIRED).issubset(parquet.schema_arrow.names):
            raise ValueError('Roads summary is missing required detachment columns.')
        if any(parquet.schema_arrow.field(name).type != SCHEMA.field(name).type for name in REQUIRED):
            raise ValueError('Roads summary has invalid detachment column types.')
        columns = [name for name in (*REQUIRED, 'design', 'segment_length_m') if name in parquet.schema_arrow.names]
        rows = parquet.read(columns=columns).to_pylist()
    groups = {key: [] for key in ids}
    summary_ids, durations = set(), set()
    remainder_count = 0
    for row in rows:
        key = _profile_id(row['segment_run_id'])
        if key in summary_ids or key not in completed:
            raise ValueError('Duplicate or unmatched Roads summary profile ID.')
        summary_ids.add(key)
        if row['summary_policy'] != 'roads_segment_pass_v1':
            raise ValueError('Unsupported Roads segment summary policy.')
        if row['segment_id'] != completed[key].get('segment_id'):
            raise ValueError('Roads summary and manifest segment IDs differ.')
        mass = _number(row['soil_loss_kg'], 'annual detachment')
        area = _number(row['modeled_area_m2'], 'modeled area', positive=True)
        density = _number(row['soil_loss_density_kg_m2'], 'detachment density')
        if not math.isclose(density, mass / area, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError('Roads detachment density disagrees with mass and area.')
        years = _number(row['simulation_years'], 'simulation years', positive=True)
        if int(years) != years:
            raise ValueError('Roads simulation years must be integral.')
        durations.add(years)
        if row.get('segment_length_m') is not None:
            _number(row['segment_length_m'], 'modeled source road-segment length', positive=True)
        if row['profile_scope'] not in ('road', 'mixed_profile', 'replacement_remainder', 'unclassified_profile'):
            raise ValueError('Unsupported Roads profile scope.')
        if row['profile_scope'] == 'replacement_remainder':
            if completed[key].get('design') != 'outslope_unrutted_remainder':
                raise ValueError('Roads remainder scope disagrees with manifest.')
            remainder_count += 1
            continue
        if completed[key].get('design') == 'outslope_unrutted_remainder' or row['segment_id'] not in groups:
            raise ValueError('Roads summary profile has no prepared geometry.')
        groups[row['segment_id']].append({field: row.get(field) for field in PROFILE_FIELDS})
    if len(durations) > 1:
        raise ValueError('Roads profiles have inconsistent simulation duration.')
    if not unavailable and summary_ids != set(completed):
        raise ValueError('Roads summary is missing completed profiles.')

    features = []
    for feature, key in zip(geometry['features'], ids):
        profiles = groups[key]
        state = 'partial' if profiles and key in incomplete else 'complete' if profiles else 'no_results'
        mass = math.fsum(row['soil_loss_kg'] for row in profiles) if state == 'complete' else None
        area = math.fsum(row['modeled_area_m2'] for row in profiles) if state == 'complete' else None
        rate = mass / area * 10 if state == 'complete' else None
        if rate is not None:
            _number(mass, 'aggregate mass')
            _number(area, 'aggregate area', positive=True)
            _number(rate, 'aggregate detachment')
        properties = dict(feature['properties'])
        properties['roads_detachment'] = dict(state=state, reason='; '.join(incomplete.get(key, [])) or None,
            rate_t_ha_year=rate, annual_detachment_kg=mass, modeled_area_m2=area,
            profile_count=len(profiles), profiles=profiles)
        features.append(dict(type='Feature', properties=properties,
                             geometry=_transform_geometry(feature.get('geometry'), transformer)))
    state = 'unavailable_mean_annual' if unavailable else 'available' if any(groups.values()) else 'no_completed_profiles'
    reason = 'Mean annual detachment is unavailable for single-storm results.' if unavailable else (
        'No completed road profiles.' if state == 'no_completed_profiles' else None)
    return dict(type='FeatureCollection', features=features, roads_detachment=dict(
        state=state, units='t/ha/year', remainder_profile_count=remainder_count, reason=reason))


def read_detachment_view(root):
    """Materialize all related sources while excluding preparation/run writers."""
    root = Path(root).resolve()
    with lifecycle.current_read(root):
        return _materialize(root)
