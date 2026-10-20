"""Independent local-area oracle through the actual temporal materializer."""
import pandas as pd
import pytest

from wepppy.nodb.mods.features_export.temporal_wide_materializer import materialize_temporal_layer_wide
from wepppy.nodb.mods.features_export.join_planner import MaterializationContractError

pytestmark = pytest.mark.unit


def water_frame():
    return pd.DataFrame({
        'key': [1]*4, 'ofe_id': [1, 2, 1, 2], 'year': [2001]*4,
        'julian': [1, 1, 2, 2], 'Area': [250., 750.]*2,
        'Ep': [1., 4.]*2, 'Es': [.5, 1.]*2, 'Er': [.5, 1.]*2,
        'ET': [2., 6.]*2, 'Dp': [4., 8.]*2, 'Q': [11., 22.]*2,
    })


def materialize(frame, mode):
    return materialize_temporal_layer_wide(
        frame=frame, layer_id='wepp.interchange.hill_wat', temporal_mode=mode,
        selected_columns=('Ep', 'Es', 'Er', 'ET', 'Dp', 'Q'),
        unit_mapping={c: 'mm' for c in ('Ep', 'Es', 'Er', 'ET', 'Dp', 'Q')},
        join_key_column='key', event_selector=None,
    ).frame


@pytest.mark.parametrize('mode,suffix,et,dp,q', [
    ('event', '_2001_01_01', 5., 7., 22.),
    ('yearly', '_yr2001', 10., 14., 44.),
    ('annual_average', '', 10., 14., 44.),
])
def test_daily_local_flux_before_temporal_reduction(mode, suffix, et, dp, q):
    result = materialize(water_frame(), mode).iloc[0]
    assert result['ET'+suffix] == pytest.approx(et)
    assert result['Dp'+suffix] == pytest.approx(dp)
    assert result['Q'+suffix] == q
    assert sum(result[c+suffix] for c in ('Ep', 'Es', 'Er')) == pytest.approx(et)


@pytest.mark.parametrize('area', [0., -1., float('nan'), float('inf')])
def test_invalid_area_is_not_a_terminal_or_equal_weight_fallback(area):
    frame = water_frame(); frame.loc[0, 'Area'] = area
    with pytest.raises(MaterializationContractError):
        materialize(frame, 'yearly')


def test_sparse_day_uses_its_own_area_and_subdivision_is_invariant():
    frame = water_frame().drop(index=3)
    result = materialize(frame, 'yearly').iloc[0]
    assert result['ET_yr2001'] == 7.
    assert result['Dp_yr2001'] == 11.
    split = water_frame()
    part = split[split.ofe_id == 2].copy()
    part.Area /= 2
    split.loc[split.ofe_id == 2, 'Area'] /= 2
    part.ofe_id = 3
    result = materialize(pd.concat([split, part], ignore_index=True), 'yearly').iloc[0]
    assert result['ET_yr2001'] == 10.
    assert result['Dp_yr2001'] == 14.


@pytest.mark.parametrize('mode,suffix,et,dp,ep', [
    ('event', '_2001_01_01', 5., 7., 3.25),
    ('yearly', '_yr2001', 10., 14., 6.5),
    ('annual_average', '', 10., 14., 6.5),
])
@pytest.mark.parametrize('left_year', [1999, None])
def test_joined_water_source_keeps_its_own_area_flux_and_dates(mode,suffix,et,dp,ep,left_year):
    from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame
    from wepppy.nodb.mods.features_export.duckdb_materializer import materialize_layer_attributes
    from wepppy.nodb.mods.features_export.temporal_wide_materializer import derive_water_et
    from wepppy.nodb.mods.features_export.join_planner import JOIN_KEY_COLUMN
    left = pd.DataFrame({'wepp_id':[1], 'Area':[999.], 'year':[left_year],
                         'julian':[9 if left_year else None], 'Ep':[999.]})
    water = water_frame().drop(columns=['key','ET']); water['wepp_id'] = 1
    water = derive_water_et(water)
    frame, _ = materialize_layer_attributes(
        layer_id='ag_fields.metrics.subfields', carrier_layer=None,
        join_contract={'primary_key':'wepp_id'}, allow_non_unique_keys=True,
        sources=[DiscoveredSourceFrame('fields','parquet',True,left,{}),
                 DiscoveredSourceFrame('ag_fields_hill_wat','parquet',True,water,{})],
    )
    local = frame.attrs['hwat_columns']
    result = materialize_temporal_layer_wide(
        frame=frame, layer_id='ag_fields.metrics.subfields', temporal_mode=mode,
        selected_columns=(local['ET'], local['Dp'], local['Ep']), unit_mapping={},
        join_key_column=JOIN_KEY_COLUMN, event_selector=None,
    ).frame.iloc[0]
    assert result[local['ET']+suffix] == et
    assert result[local['Dp']+suffix] == dp
    assert result[local['Ep']+suffix] == ep
    assert not any(name.endswith('_yr1999') for name in result.index)


def test_requested_missing_event_is_null_for_local_fluxes():
    from wepppy.nodb.mods.features_export.contracts import NormalizedTemporalEvent
    frame = water_frame().iloc[:2]
    result = materialize_temporal_layer_wide(
        frame=frame, layer_id='wepp.interchange.hill_wat', temporal_mode='event',
        selected_columns=('ET', 'Dp', 'Q'), unit_mapping={}, join_key_column='key',
        event_selector=NormalizedTemporalEvent(selector='date', dates=('2001-01-01','2001-01-02')),
    ).frame.iloc[0]
    assert result['ET_2001_01_01'] == 5.
    assert pd.isna(result['ET_2001_01_02'])
    assert pd.isna(result['Dp_2001_01_02'])


@pytest.mark.parametrize('empty', [False, True])
def test_unmatched_joined_water_retains_geometry_and_null_metrics(empty):
    from wepppy.nodb.mods.features_export.discovery import DiscoveredSourceFrame
    from wepppy.nodb.mods.features_export.duckdb_materializer import materialize_layer_attributes
    from wepppy.nodb.mods.features_export.join_planner import JOIN_KEY_COLUMN
    water = water_frame(); water['wepp_id'] = 1
    if empty: water = water.iloc[:0]
    left = pd.DataFrame({'wepp_id':[1,2], 'year':[2001,2001], 'julian':[1,1]})
    frame, _ = materialize_layer_attributes(
        layer_id='ag_fields.metrics.subfields', carrier_layer=None,
        join_contract={'primary_key':'wepp_id'}, allow_non_unique_keys=True,
        sources=[DiscoveredSourceFrame('fields','parquet',True,left,{}),
                 DiscoveredSourceFrame('ag_fields_hill_wat','parquet',True,water,{})],
    )
    result = materialize_temporal_layer_wide(
        frame=frame, layer_id='ag_fields.metrics.subfields', temporal_mode='yearly',
        selected_columns=('ET','Dp'), unit_mapping={},
        join_key_column=JOIN_KEY_COLUMN, event_selector=None,
    ).frame.set_index(JOIN_KEY_COLUMN)
    assert len(result) == 2
    assert pd.isna(result.loc['2','ET_yr2001'])
    assert pd.isna(result.loc['2','Dp_yr2001'])
    if not empty:
        assert result.loc['1','ET_yr2001'] == 10.


@pytest.mark.parametrize('mode', ['event','yearly','annual_average'])
@pytest.mark.parametrize('scope', ['baseline','roads'])
def test_real_parquet_core_derives_selected_et_without_exporting_area(tmp_path, mode, scope):
    from wepppy.nodb.mods.features_export.carrier_layer_materializer import materialize_carrier_layer_core
    from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
    from wepppy.nodb.mods.features_export.planner import resolve_export_plan
    from wepppy.nodb.mods.features_export.dependency_tracker import DependencyEntry
    from wepppy.nodb.mods.features_export.join_planner import JOIN_KEY_COLUMN
    layer_id = 'wepp.interchange.hill_wat'
    frame = water_frame().drop(columns=['ET','key']); frame['wepp_id'] = 1
    frame.to_parquet(tmp_path/'H.wat.parquet',index=False)
    catalog = load_layer_catalog()
    temporal = {'mode':mode}
    if mode == 'event': temporal['event'] = {'selector':'date','dates':['2001-01-01']}
    plan = resolve_export_plan({'format':'parquet','units':'si','layers':[layer_id],
        'output_scopes':[scope], 'temporal':temporal,
        'column_selection':{layer_id:{'include':['ET','Dp']}}},catalog)
    result = materialize_carrier_layer_core(
        wd=tmp_path, layer=plan.layers[0], catalog_layer_raw=catalog.layer_index[layer_id].raw,
        request_plan=plan, consolidated_join_key_column=JOIN_KEY_COLUMN,
        dependency_entries=(DependencyEntry(relpath='H.wat.parquet',exists=True,size=None,mtime_ns=None,
            dependency_role='source',dependency_id='wepp_hill_wat'),),
    )
    suffix = '_2001_01_01' if mode == 'event' else '_yr2001' if mode == 'yearly' else ''
    assert result.frame['ET'+suffix].iloc[0] == (5. if mode == 'event' else 10.)
    assert result.frame['Dp'+suffix].iloc[0] == (7. if mode == 'event' else 14.)
    assert 'Area' not in result.selected_columns
    assert result.unit_mapping['ET'+suffix] == 'mm'
    # Exercise shared production writers, not only an in-memory reduction.
    import dataclasses
    import json
    import zipfile
    import geopandas as gpd
    from shapely.geometry import Polygon
    from wepppy.nodb.mods.features_export.exporters import get_export_writer
    from wepppy.nodb.mods.features_export.exporters.base import PreparedLayerPayload, ExportWriterRequest
    from wepppy.nodb.mods.features_export.tabular_temporal_layout import reshape_temporal_wide_to_long
    geometry = Polygon([(0,0),(1,0),(1,1),(0,0)])
    geo = gpd.GeoDataFrame(result.frame,geometry=[geometry],crs='EPSG:4326')
    for fmt in ('parquet','csv','geojson'):
        formatted_plan = dataclasses.replace(plan,request=dataclasses.replace(plan.request,format=fmt))
        payload = PreparedLayerPayload(output_layer_id=plan.layers[0].output_layer_id,
            payload=geo.to_json(),tabular_frame=result.frame,row_count=1,feature_count=1)
        artifact = get_export_writer(fmt).write(ExportWriterRequest(
            plan=formatted_plan,layer_payloads={payload.output_layer_id:payload},artifact_dir=tmp_path/fmt))
        with zipfile.ZipFile(artifact.artifact_path) as archive:
            member = next(name for name in archive.namelist() if name.endswith('.'+fmt))
            with archive.open(member) as incoming:
                if fmt == 'parquet': readback = pd.read_parquet(incoming)
                elif fmt == 'csv': readback = pd.read_csv(incoming)
                else:
                    feature = json.load(incoming)['features'][0]
                    assert feature['geometry'] == json.loads(geo.to_json())['features'][0]['geometry']
                    readback = pd.DataFrame([feature['properties']])
        assert readback['ET'+suffix].iloc[0] == (5. if mode == 'event' else 10.)
        assert readback['Dp'+suffix].iloc[0] == (7. if mode == 'event' else 14.)
    long = reshape_temporal_wide_to_long(frame=result.frame,selected_columns=result.selected_columns,
        unit_mapping=result.unit_mapping,temporal_mode=mode,event_selector=plan.request.temporal.event)
    assert long.frame['ET'].iloc[0] == (5. if mode == 'event' else 10.)
    assert long.frame['Dp'].iloc[0] == (7. if mode == 'event' else 14.)


def test_routed_only_selection_retains_existing_area_independent_behavior():
    frame = water_frame(); frame.Area = float('nan')
    result = materialize_temporal_layer_wide(frame=frame,layer_id='wepp.interchange.hill_wat',
        temporal_mode='yearly',selected_columns=('Q',),unit_mapping={},join_key_column='key',
        event_selector=None).frame
    assert result.Q_yr2001.iloc[0] == 44.


def test_et_only_selection_rejects_hidden_infinite_components():
    from wepppy.nodb.mods.features_export.temporal_wide_materializer import derive_water_et
    frame = water_frame(); frame.loc[0,'Ep'] = float('inf'); frame.loc[0,'Es'] = -float('inf')
    frame = derive_water_et(frame)
    with pytest.raises(MaterializationContractError,match='finite'):
        materialize_temporal_layer_wide(frame=frame,layer_id='wepp.interchange.hill_wat',
            temporal_mode='yearly',selected_columns=('ET',),unit_mapping={},join_key_column='key',
            event_selector=None)
