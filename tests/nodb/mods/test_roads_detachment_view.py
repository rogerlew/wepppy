"""Real files, CRS and shared/exclusive admission for the dashboard read view."""
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyproj import Transformer
import pytest

from tests.roads_lifecycle_fixtures import write_current_roads_fixture
from wepppy.weppcloud.routes.nodb_api import _roads_detachment as view
from wepppy.nodb.mods.roads._segment_loss_summary import SCHEMA
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

pytestmark = pytest.mark.integration


def sources(root, rows=None, *, crs='EPSG:4326'):
    write_current_roads_fixture(root)
    folder = root / view.SEGMENTS
    folder.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = [dict(segment_id='line1', segment_run_id=i, profile_scope='mixed_profile',
                     soil_loss_kg=mass, modeled_area_m2=area, soil_loss_density_kg_m2=mass/area,
                     simulation_years=16, design='outslope_rutted', segment_length_m=20.,
                     summary_policy='roads_segment_pass_v1') for i, mass, area in [(1, 2., 10.), (2, 9., 30.)]]
    manifest = [dict(segment_id=r['segment_id'], segment_run_id=r['segment_run_id'],
                     design=r['design'], status='completed') for r in rows]
    (folder / 'roads.segment.pass.manifest.json').write_text(json.dumps(manifest))
    coordinates = [[-123., 45.], [-123.001, 45.001]]
    if crs != 'EPSG:4326':
        transform = Transformer.from_crs(4326, crs, always_xy=True)
        coordinates = [list(transform.transform(*p)) for p in coordinates]
    (folder / 'roads.inslope.monotonic.geojson').write_text(json.dumps(dict(type='FeatureCollection', features=[
        dict(type='Feature', properties=dict(segment_id='line1', name='<img src=x onerror=alert(1)>',
             roads_detachment={'state': 'forged'}), geometry=dict(type='LineString', coordinates=coordinates))])))
    (folder / 'roads.inslope.summary.json').write_text(json.dumps(dict(input_crs=crs,
        source_crs='EPSG:32611', configured_input_crs='EPSG:32611', input_crs_source='inferred')))
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), root / view.SUMMARY)
    return folder


def test_multi_profile_full_area_no_second_annualization_and_literal_labels(tmp_path):
    sources(tmp_path)
    result = view.read_detachment_view(tmp_path)
    feature = result['features'][0]
    data = feature['properties']['roads_detachment']
    assert data['rate_t_ha_year'] == 2.75
    assert data['annual_detachment_kg'] == 11.
    assert data['modeled_area_m2'] == 40.
    assert data['profile_count'] == 2
    assert [p['segment_length_m'] for p in data['profiles']] == [20., 20.]
    assert feature['properties']['name'] == '<img src=x onerror=alert(1)>'
    assert result['roads_detachment']['state'] == 'available'


@pytest.mark.parametrize('crs', ['EPSG:4326', 'EPSG:32610'])
def test_effective_crs_overrides_original_and_configured(tmp_path, crs):
    sources(tmp_path, crs=crs)
    point = view.read_detachment_view(tmp_path)['features'][0]['geometry']['coordinates'][0]
    assert point == pytest.approx([-123., 45.])


def test_empty_and_single_storm_remain_distinct(tmp_path):
    sources(tmp_path, [])
    assert view.read_detachment_view(tmp_path)['roads_detachment']['state'] == 'no_completed_profiles'
    (tmp_path / view.SUMMARY).unlink()
    with pytest.raises(lifecycle.RoadsResultsUnavailable): view.read_detachment_view(tmp_path)
    receipt = dict(policy=lifecycle.POLICY, is_single_storm=True,
                   required_relpaths=sorted(lifecycle.mandatory_paths(True)))
    (tmp_path / lifecycle.RECEIPT).write_text(json.dumps(receipt))
    result = view.read_detachment_view(tmp_path)
    assert result['roads_detachment']['state'] == 'unavailable_mean_annual'
    assert result['features'][0]['properties']['roads_detachment']['rate_t_ha_year'] is None


def test_partial_preserves_diagnostics_without_aggregate(tmp_path):
    folder = sources(tmp_path)
    manifest = folder / 'roads.segment.pass.manifest.json'
    rows = json.loads(manifest.read_text())
    rows.append(dict(segment_id='line1', status='skipped', reason='No usable routing'))
    manifest.write_text(json.dumps(rows))
    data = view.read_detachment_view(tmp_path)['features'][0]['properties']['roads_detachment']
    assert data['state'] == 'partial' and data['rate_t_ha_year'] is None
    assert data['profile_count'] == 2


@pytest.mark.parametrize('change', ['duplicate_geometry', 'duplicate_profile', 'nonfinite', 'zero_area',
    'years', 'profile_scope', 'missing_completed', 'unmapped', 'conflicting_crs', 'missing_crs', 'alias'])
def test_integrity_errors_are_explicit(tmp_path, change):
    folder = sources(tmp_path)
    geometry_path = folder / 'roads.inslope.monotonic.geojson'
    geometry = json.loads(geometry_path.read_text())
    rows = pq.read_table(tmp_path / view.SUMMARY).to_pylist()
    if change == 'duplicate_geometry': geometry['features'].append(geometry['features'][0])
    elif change == 'duplicate_profile': rows.append(rows[0])
    elif change == 'nonfinite': rows[0]['soil_loss_kg'] = float('nan')
    elif change == 'zero_area': rows[0]['modeled_area_m2'] = 0.
    elif change == 'years': rows[0]['simulation_years'] = 15
    elif change == 'profile_scope': rows[0]['profile_scope'] = 'typo_scope'
    elif change == 'missing_completed': rows.pop()
    elif change == 'unmapped': rows[0]['segment_id'] = 'other'
    elif change == 'conflicting_crs': geometry['crs'] = dict(type='name', properties=dict(name='EPSG:32610'))
    elif change == 'missing_crs': (folder / 'roads.inslope.summary.json').write_text('{}')
    geometry_path.write_text(json.dumps(geometry))
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), tmp_path / view.SUMMARY)
    if change == 'alias':
        moved = folder / 'elsewhere.json'; geometry_path.rename(moved); geometry_path.symlink_to(moved)
    with pytest.raises(ValueError): view.read_detachment_view(tmp_path)


def test_guard_held_through_materialization_blocks_reprepare(tmp_path, monkeypatch):
    sources(tmp_path)
    original = view._transform_geometry
    def contested(*args):
        # Separate context/thread cannot inherit the reader's context. The real
        # flock must reject a preparation writer until geometry is materialized.
        from concurrent.futures import ThreadPoolExecutor
        def writer():
            with lifecycle.operation(tmp_path):
                pytest.fail('writer entered during materialization')
        with ThreadPoolExecutor(1) as pool:
            with pytest.raises(lifecycle.RoadsOperationBusy): pool.submit(writer).result()
        return original(*args)
    monkeypatch.setattr(view, '_transform_geometry', contested)
    view.read_detachment_view(tmp_path)
    with lifecycle.operation(tmp_path):
        lifecycle.retain(tmp_path, replace_segments=True)
    with pytest.raises(lifecycle.RoadsResultsUnavailable): view.read_detachment_view(tmp_path)


def test_negative_and_remainder_not_mapped(tmp_path):
    sources(tmp_path)
    rows = pq.read_table(tmp_path / view.SUMMARY).to_pylist()
    rows[0].update(soil_loss_kg=-20., soil_loss_density_kg_m2=-2.)
    rows.append({**rows[0], 'segment_id': 'h1::remainder', 'segment_run_id': 3,
                 'profile_scope': 'replacement_remainder', 'design': 'outslope_unrutted_remainder'})
    sources(tmp_path, rows)
    result = view.read_detachment_view(tmp_path)
    assert result['roads_detachment']['remainder_profile_count'] == 1
    assert len(result['features']) == 1
    assert result['features'][0]['properties']['roads_detachment']['rate_t_ha_year'] == -2.75
