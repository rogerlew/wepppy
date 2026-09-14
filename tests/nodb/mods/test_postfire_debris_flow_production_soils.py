"""Unmocked isolated SQLite boundaries and approved soil-policy regression."""
import csv
import json
from pathlib import Path
import sqlite3

import numpy as np
import pytest
import rasterio

from wepppy.nodb.mods.postfire_debris_flow.soil_policy import (
    derive_recorded_component, derive_recorded_mapunits,
)
from wepppy.nodb.mods.postfire_debris_flow.soil_snapshot import (
    prepare_soil_tables, snapshot_cache, verify_snapshot,
)
from wepppy.nodb.mods.postfire_debris_flow.soil_thickness import derive_component

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parent/'fixtures/postfire_debris_flow_soils'


def horizon(key=1, top=0, bottom=100, master='H', name='H1'):
    return dict(cokey='1', chkey=str(key), hzdept_r=top, hzdepb_r=bottom,
                hzthk_r=None, desgnmaster=master, hzname=name)


def database(path):
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE component (mukey TEXT,cokey TEXT,compname TEXT,comppct_r REAL)')
        conn.execute('CREATE TABLE chorizon (cokey TEXT,chkey TEXT,hzname TEXT,hzdept_r REAL,hzdepb_r REAL,hzthk_r REAL,desgnmaster TEXT)')
        conn.execute("INSERT INTO component VALUES ('7','1','Legacy',100)")
        conn.execute("INSERT INTO chorizon VALUES ('1','1','H1',0,100,NULL,'H')")
    return path


def test_policy_preserves_offline_defaults_and_recorded_material():
    rows = [horizon(), horizon(2, 100, 150, 'C', 'Cr'), horizon(3, 150, 200, 'R', 'R')]
    before = json.dumps(rows)
    assert derive_component(rows)['thickness_cm'] is None
    value = derive_recorded_component(rows)
    assert value['thickness_cm'] == 150
    assert value['interval_sum_cm'] == 200
    assert json.dumps(rows) == before
    assert derive_component(rows)['thickness_cm'] is None


@pytest.mark.parametrize('changes', [{'hzthk_r': 200}, {'hzname': 'H2'},
                                   {'desgnmaster': 'C', 'hzname': 'C'}, {'hzdepb_r': 200}])
def test_duplicate_conflicts_cannot_be_erased_by_policy(changes):
    rows = [horizon(), dict(horizon(), **changes)]
    value = derive_recorded_component(rows)
    assert value['thickness_cm'] is None
    assert 'duplicate_id_conflict' in value['reason_codes']


def test_pair_once_with_canonical_ids_and_retained_provenance():
    rows = [horizon('01', 0, 50, 'E/B', 'E/B'), horizon('1', 0, 50, 'E/B', 'E/B'),
            horizon(2, 0, 50, 'E/B', 'E/B')]
    value = derive_recorded_component(rows)
    assert value['thickness_cm'] == 50
    assert value['source_row_count'] == 3
    assert value['horizon_count'] == 1
    assert value['pair_reductions'][0]['source_chkeys'] == ['1', '2']
    assert value['interval_sum_cm'] == 100
    assert derive_recorded_component([horizon(1), horizon(2)])['thickness_cm'] is None


def test_weighting_and_disagreement_are_explicit():
    components = [dict(mukey='7', cokey=str(i), comppct_r=w) for i,w in [(1,70),(2,50)]]
    rows = [dict(horizon(), hzthk_r=99), dict(horizon(2, 0, 200), cokey='2')]
    derived, means = derive_recorded_mapunits(components, rows)
    assert derived[0]['thickness_cm'] == 100
    assert derived[0]['reported_thickness_conflicts'] == 1
    assert means[0]['mean_cm'] == pytest.approx(17000/120)
    assert means[0]['known_percentage'] == 120
    assert 'overfull_percentage' in means[0]['reason_codes']


@pytest.mark.parametrize('site,valid,available', [('moscow_mountain',91,44), ('topanga',31,13), ('az_ponderosa',187,53)])
def test_frozen_recorded_depth_results(site, valid, available):
    tables = []
    for table in ('component', 'chorizon'):
        with (FIXTURES/f'{site}_{table}.csv').open(newline='') as stream:
            tables.append(list(csv.DictReader(stream)))
    components, mapunits = derive_recorded_mapunits(*tables)
    assert sum(row['status'] == 'valid' for row in components) == valid
    assert sum(row['mean_cm'] is not None for row in mapunits) == available


def test_snapshot_wal_commits_and_concurrent_change(tmp_path):
    path = database(tmp_path/'cache ?#.sqlite')
    writer = sqlite3.connect(path)
    try:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute("UPDATE chorizon SET hzdepb_r=125 WHERE chkey='1'")
        writer.commit()
        before = path.read_bytes()
        snapshot = snapshot_cache(path, tmp_path/'snapshot')
        assert snapshot['horizons'][0]['hzdepb_r'] == 125
        assert path.read_bytes() == before
        writer.execute("UPDATE chorizon SET hzdepb_r=140 WHERE chkey='1'")
        writer.commit()
        with pytest.raises(ValueError, match='changed'):
            verify_snapshot(path, snapshot, tmp_path/'recheck')
        assert writer.execute('SELECT hzdepb_r FROM chorizon').fetchone() == (140,)
    finally:
        writer.close()


def test_preparation_propagates_source_and_derived_values_without_source_writes(tmp_path):
    path = database(tmp_path/'cache.sqlite')
    before = path.read_bytes()
    output = tmp_path/'soil'
    manifest = prepare_soil_tables(path, output)
    assert path.read_bytes() == before
    with (output/'mapunits.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert float(rows[0]['mean_cm']) == 100
    with (output/'horizons_source.csv').open() as stream:
        assert list(csv.DictReader(stream))[0]['desgnmaster'] == 'H'
    assert manifest['counts'] == {'components':1, 'horizons':1, 'mapunits':1}
    assert len(manifest['artifacts_sha256']) == 4
    with pytest.raises(FileExistsError):
        prepare_soil_tables(path, output)


def test_corrupt_and_symlink_sources_leave_no_success_manifest(tmp_path):
    path = tmp_path/'bad.sqlite'
    path.write_bytes(b'not a database')
    with pytest.raises(sqlite3.DatabaseError):
        prepare_soil_tables(path, tmp_path/'bad_attempt')
    assert (tmp_path/'bad_attempt/incomplete.json').exists()
    assert not (tmp_path/'bad_attempt/manifest.json').exists()
    link = tmp_path/'link.sqlite'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='Unsafe'):
        snapshot_cache(link, tmp_path/'unsafe')


def test_writer_change_inside_snapshot_is_rejected(tmp_path, monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow import soil_snapshot
    path = database(tmp_path/'concurrent.sqlite')
    writer = sqlite3.connect(path)
    writer.execute('PRAGMA journal_mode=WAL')
    writer.execute('UPDATE chorizon SET hzdepb_r=110')
    writer.commit()
    read = soil_snapshot._read_tables
    def concurrent_read(*args, **kwargs):
        rows = read(*args, **kwargs)
        writer.execute('UPDATE chorizon SET hzdepb_r=120')
        writer.commit()
        return rows
    monkeypatch.setattr(soil_snapshot, '_read_tables', concurrent_read)
    try:
        with pytest.raises(ValueError, match='during snapshot'):
            snapshot_cache(path, tmp_path/'concurrent_snapshot')
        assert writer.execute('SELECT hzdepb_r FROM chorizon').fetchone() == (120,)
    finally:
        writer.close()


def test_clean_wal_source_never_gains_companions(tmp_path):
    path = database(tmp_path/'clean.sqlite')
    connection = sqlite3.connect(path)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.close()
    before = path.read_bytes()
    assert not Path(str(path)+'-wal').exists()
    snapshot = snapshot_cache(path, tmp_path/'retained')
    assert snapshot['horizons'][0]['hzdepb_r'] == 100
    assert path.read_bytes() == before
    assert not Path(str(path)+'-wal').exists()
    assert not Path(str(path)+'-shm').exists()


def test_uncommitted_rollback_journal_spill_is_never_a_snapshot(tmp_path):
    path = database(tmp_path/'rollback.sqlite')
    writer = sqlite3.connect(path)
    try:
        writer.execute('PRAGMA cache_size=1')
        before = path.read_bytes()
        writer.execute('BEGIN IMMEDIATE')
        writer.execute('UPDATE chorizon SET hzdepb_r=777')
        writer.execute('UPDATE component SET compname=?, comppct_r=90', ('x'*100000,))
        assert Path(str(path)+'-journal').exists()
        assert path.read_bytes() != before  # actual spill, not only dirty memory
        with pytest.raises(ValueError, match='Rollback journal'):
            snapshot_cache(path, tmp_path/'uncommitted')
        writer.rollback()
        assert writer.execute('SELECT hzdepb_r FROM chorizon').fetchone() == (100,)
        assert writer.execute('SELECT comppct_r FROM component').fetchone() == (100,)
    finally:
        writer.close()


@pytest.mark.parametrize('unit,accepted', [('inch',True), ('m',False)])
def test_thick_raster_unit_admission(tmp_path, unit, accepted):
    from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import read_raster, M1Error
    grid = {'shape':[2,3], 'crs':'EPSG:32611', 'transform':[10,0,500000,0,-10,4000000]}
    path = tmp_path/'units.tif'
    soil_raster(path, np.ones((2,3)), grid)
    with rasterio.open(path, 'r+') as ds:
        ds.set_band_unit(1, unit)
    if accepted:
        assert read_raster(path, allowed_units=(None,'','inch','inches','in'))[0][0,0] == 1
    else:
        with pytest.raises(M1Error, match='unit'):
            read_raster(path, allowed_units=(None,'','inch','inches','in'))


@pytest.mark.parametrize('table,column,status', [('chorizon','hzthk_r','valid'),
    ('chorizon','hzdepb_r','unavailable'), ('component','comppct_r','valid')])
def test_nonfinite_source_numbers_reach_scientific_policy(tmp_path, table, column, status):
    path = database(tmp_path/'nonfinite.sqlite')
    with sqlite3.connect(path) as conn:
        conn.execute(f'UPDATE {table} SET {column}=?', (float('inf'),))
    result = prepare_soil_tables(path, tmp_path/'soil')
    assert result['status'] == 'complete'
    with (tmp_path/'soil/components.csv').open() as stream:
        component = list(csv.DictReader(stream))[0]
    assert component['status'] == status
    if column == 'hzthk_r':
        assert component['reported_thickness_conflicts'] == '1'
    if column == 'comppct_r':
        with (tmp_path/'soil/mapunits.csv').open() as stream:
            assert list(csv.DictReader(stream))[0]['status'] == 'unavailable'


def test_retained_sqlite_preserves_null_empty_duplicate_conflict(tmp_path):
    path = database(tmp_path/'null_empty.sqlite')
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO chorizon VALUES ('1','1','H1',0,100,'','H')")
    prepare_soil_tables(path, tmp_path/'soil')
    copied = tmp_path/'soil/snapshots/initial/cache.sqlite'
    replay = snapshot_cache(copied, tmp_path/'replay')
    components, _ = derive_recorded_mapunits(replay['components'], replay['horizons'])
    assert components[0]['status'] == 'unavailable'
    assert 'duplicate_id_conflict' in components[0]['reason_codes']
    assert {r['hzthk_r'] for r in replay['horizons']} == {None, ''}


def test_inspection_keys_canonical_but_replay_preserves_raw_values(tmp_path):
    path = database(tmp_path/'keys.sqlite')
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE component SET mukey='007', cokey='01'")
        conn.execute("UPDATE chorizon SET cokey='01', chkey='001'")
    prepare_soil_tables(path, tmp_path/'soil')
    with (tmp_path/'soil/horizons_source.csv').open() as stream:
        row = list(csv.DictReader(stream))[0]
    assert row['cokey'] == row['chkey'] == '1'
    replay = snapshot_cache(tmp_path/'soil/snapshots/initial/cache.sqlite', tmp_path/'replay_keys')
    assert replay['horizons'][0]['chkey'] == '001'


def soil_raster(path, values, grid, nodata=-9999):
    with rasterio.open(path, 'w', driver='GTiff', count=1, dtype=values.dtype,
                       height=values.shape[0], width=values.shape[1], nodata=nodata,
                       crs=grid['crs'], transform=rasterio.Affine(*grid['transform'])) as ds:
        ds.write(values, 1)


@pytest.mark.parametrize('mode', ['missing', 'primary', 'fallback', 'both'])
def test_cellwise_prepared_soil_sources(tmp_path, mode):
    from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import prepare_soil, SOURCE_ID
    from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import digest
    grid = {'shape':[2,3], 'crs':'EPSG:32611', 'transform':[10,0,500000,0,-10,4000000]}
    domain = np.array([[True,True,True], [True,True,False]])
    soils = tmp_path/'soils'; soils.mkdir()
    cache = database(soils/'ssurgo_tabular_cache.sqlite')
    original = cache.read_bytes()
    soil_raster(soils/'ssurgo.tif', np.array([[7,8,9],[8,7,7]], dtype='int32'), grid)
    prepared = tmp_path/'postfire_debris_flow/inputs'; prepared.mkdir(parents=True)
    metadata = {'schema_version': 1}
    if mode in ('primary', 'both'):
        evidence = prepared/'primary.json'
        evidence.write_text(json.dumps({'schema_version':1, 'collection_by_mukey':{'7':'SSURGO'},
                                        'source':'isolated fixture', 'retrieved_at':'2026-09-14T00:00:00Z'}))
        metadata['primary'] = dict(collection='SSURGO', mukeys=['7'],
                                   evidence=str(evidence.relative_to(tmp_path)), evidence_sha256=digest(evidence))
    if mode in ('fallback', 'both'):
        native = prepared/'native.tif'
        soil_raster(native, np.array([[10,0,-1],[20,30,-9999]], dtype='float64'), grid)
        with rasterio.open(native) as ds:
            bounds = list(ds.bounds)
        evidence = prepared/'fallback.json'
        evidence.write_text(json.dumps(dict(schema_version=1, source_id=SOURCE_ID, source='isolated fixture',
                                            sha256=digest(native), grid=grid, bounds=bounds)))
        metadata['fallback'] = dict(path=str(native.relative_to(tmp_path)), sha256=digest(native),
                                    source_id=SOURCE_ID, units='inch', evidence=str(evidence.relative_to(tmp_path)),
                                    evidence_sha256=digest(evidence))
    (prepared/'soil_sources.json').write_text(json.dumps(metadata))
    output = tmp_path/'attempt'
    result = prepare_soil(tmp_path, output, grid, domain)
    assert cache.read_bytes() == original
    assert not (output/'incomplete.json').exists()
    with rasterio.open(output/'source.tif') as ds:
        sources = ds.read(1)
    with rasterio.open(output/'thickness_cm.tif') as ds:
        values = ds.read(1, masked=True)
    expected_primary = 2 if mode in ('primary','both') else 0
    expected_fallback = (2 if mode == 'both' else 4) if mode in ('fallback','both') else 0
    assert result['source_cells'] == dict(primary=expected_primary, fallback=expected_fallback,
                                        unavailable=5-expected_primary-expected_fallback, outside=1)
    assert sources[1,2] == 255 and values.mask[1,2]
    if expected_primary:
        assert values[0,0] == 100 and values[1,1] == 100
    if expected_fallback:
        assert values[0,1] == 0 and sources[0,1] == 2
        assert values[1,0] == pytest.approx(50.8)
        assert values.mask[0,2]
    retry = prepare_soil(tmp_path, tmp_path/'retry', grid, domain)
    assert retry['source_cells'] == result['source_cells']
    assert cache.read_bytes() == original


@pytest.mark.parametrize('payload', ['', '[]', '{"schema_version":2}', '{"primary":{}}',
                                    '{"schema_version":1,"primary":{}}'])
def test_malformed_prepared_metadata_is_not_absence(tmp_path, payload):
    from wepppy.nodb.mods.postfire_debris_flow.soil_inputs import prepared_sources
    from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import RainfallError
    directory = tmp_path/'postfire_debris_flow/inputs'; directory.mkdir(parents=True)
    (directory/'soil_sources.json').write_text(payload)
    with pytest.raises(RainfallError):
        prepared_sources(tmp_path)


@pytest.mark.parametrize('appears', ['metadata', 'cache', 'labels', 'mask'])
def test_absent_soil_dependency_appearing_during_composition_fails(tmp_path, monkeypatch, appears):
    from wepppy.nodb.mods.postfire_debris_flow import soil_inputs
    from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import RainfallError
    grid = {'shape':[2,3], 'crs':'EPSG:32611', 'transform':[10,0,500000,0,-10,4000000]}
    (tmp_path/'soils').mkdir()
    (tmp_path/'postfire_debris_flow/inputs').mkdir(parents=True)
    prepare = soil_inputs.prepare
    def source_appears(*args, **kwargs):
        prepare(*args, **kwargs)
        if appears == 'metadata':
            (tmp_path/soil_inputs.META).write_text('{}')
        elif appears == 'cache':
            database(tmp_path/'soils/ssurgo_tabular_cache.sqlite')
        elif appears == 'labels':
            soil_raster(tmp_path/'soils/ssurgo.tif', np.ones((2,3)), grid)
        else:
            (tmp_path/'soils/ssurgo.tif.msk').write_bytes(b'new mask')
    monkeypatch.setattr(soil_inputs, 'prepare', source_appears)
    with pytest.raises(RainfallError, match='presence'):
        soil_inputs.prepare_soil(tmp_path, tmp_path/'attempt', grid, np.ones((2,3), dtype=bool))
    assert not (tmp_path/'attempt/manifest.json').exists()
    assert (tmp_path/'attempt/incomplete.json').exists()


def test_hashing_enforces_limit_after_file_growth(tmp_path, monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow import rainfall_io as io
    path = tmp_path/'growing'; path.write_bytes(b'123')
    regular = io.regular
    def grow_after_admission(*args, **kwargs):
        result = regular(*args, **kwargs)
        with path.open('ab') as stream:
            stream.write(b'456')
        return result
    monkeypatch.setattr(io, 'regular', grow_after_admission)
    with pytest.raises(io.RainfallError, match='grew beyond'):
        io.digest(path, limit=4)


def test_copy_symlink_swap_cannot_retain_outside_bytes(tmp_path, monkeypatch):
    from wepppy.nodb.mods.postfire_debris_flow import soil_inputs, rainfall_io as io
    source = tmp_path/'inside'; source.write_bytes(b'approved')
    outside = tmp_path/'outside'; outside.write_bytes(b'outside synthetic marker')
    target = tmp_path/'retained'
    expected = io.digest(source)
    regular = io.regular
    calls = 0
    def swap_at_open(*args, **kwargs):
        nonlocal calls
        result = regular(*args, **kwargs)
        calls += 1
        if calls == 3:  # initial stat, initial digest, then descriptor admission
            source.unlink(); source.symlink_to(outside)
        return result
    monkeypatch.setattr(io, 'regular', swap_at_open)
    with pytest.raises((OSError, io.RainfallError)):
        soil_inputs._copy(source, target, expected)
    assert not target.exists() or b'outside synthetic marker' not in target.read_bytes()
