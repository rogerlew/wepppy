from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter.archive_validation import validate_and_extract_zip_archive
from wepppy.microservices.shape_converter.errors import ShapeConverterError
from wepppy.microservices.shape_converter.inspect import select_single_shapefile_dataset

convert = importlib.import_module('wepppy.microservices.shape_converter.convert')
worker = importlib.import_module('wepppy.microservices.shape_converter.convert_parser_worker')
pytestmark = [pytest.mark.unit, pytest.mark.microservice]


def valid_payload():
    return {'properties': [{'NAME': 'demo', 'COUNT': 1, 'VALUE': 1.25, 'FLAG': True, 'EMPTY': None}],
            'geometries': [{'type': 'Point', 'coordinates': [10.0, 20.0]}],
            'source_bounds': [10.0, 20.0, 10.0, 20.0], 'source_crs_wkt': None}


def read_payload(tmp_path, data):
    path = tmp_path / 'payload.json'
    path.write_bytes(data)
    return convert._read_parser_payload(payload_path=path, worker_stdout='', worker_stderr='')


def test_json_payload_roundtrip(tmp_path):
    payload = valid_payload()
    assert read_payload(tmp_path, json.dumps(payload).encode()) == payload


@pytest.mark.parametrize('data', [b'\x80\x04N.', b'\x80\x04}\x94.', b'\xff', b'{} {}', b'{"x":1,"x":2}',
                                   b'[' * 100 + b']' * 100, b'{"canary":"private-value"}'])
def test_non_json_or_malformed_payload_rejected(tmp_path, data):
    with pytest.raises(ShapeConverterError) as error:
        read_payload(tmp_path, data)
    assert error.value.code == 'invalid_shapefile'
    assert 'private-value' not in error.value.details
    assert not (tmp_path / 'canary').exists()


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(extra=True),
    lambda p: p.pop('source_crs_wkt'),
    lambda p: p.update(source_bounds=[0, 0, float('nan'), 0]),
    lambda p: p.update(source_bounds=[2, 0, 1, 0]),
    lambda p: p.update(source_crs_wkt=123),
    lambda p: p.update(source_crs_wkt=''),
    lambda p: p.update(properties=[]),
    lambda p: p['properties'][0].update(NESTED={}),
    lambda p: p['properties'][0].update(VALUE=float('inf')),
    lambda p: p['geometries'][0].update(type='Unknown'),
    lambda p: p['geometries'][0].update(coordinates=[True, 1]),
    lambda p: p['geometries'][0].update(coordinates=[1]),
    lambda p: p['geometries'][0].update(extra='private-value'),
])
def test_invalid_schema_rejected(tmp_path, mutation):
    payload = valid_payload()
    mutation(payload)
    with pytest.raises(ShapeConverterError) as error:
        read_payload(tmp_path, json.dumps(payload).encode())
    assert error.value.code == 'invalid_shapefile'
    assert 'private-value' not in error.value.details


@pytest.mark.parametrize('names', [('caf\u00e9.shp', 'cafe\u0301.shp'),
                                  ('STRASSE.shp', 'stra\u00dfe.shp'),
                                  ('dir/a.shp', 'dir\\a.shp')])
def test_normalized_archive_aliases_rejected(tmp_path, names):
    with pytest.raises(ShapeConverterError):
        validate_and_extract_zip_archive(archive_name='input.zip',
            archive_bytes=build_zip_bytes({name: b'x' for name in names}), extraction_root=tmp_path)


@pytest.mark.parametrize('extra', ['other.shp', 'other.prj', 'other.qix'])
def test_incomplete_or_optional_extra_prefix_rejected(tmp_path, extra):
    entries = build_minimal_point_dataset('one')
    entries[extra] = b'x'
    extracted = validate_and_extract_zip_archive(archive_name='input.zip',
        archive_bytes=build_zip_bytes(entries), extraction_root=tmp_path)
    with pytest.raises(ShapeConverterError) as error:
        select_single_shapefile_dataset(extracted)
    assert error.value.code == 'invalid_shapefile'


def test_normalized_valid_dataset_and_optional_sidecar(tmp_path):
    entries = build_minimal_point_dataset('cafe\u0301')
    entries['cafe\u0301.cpg'] = b'UTF-8'
    extracted = validate_and_extract_zip_archive(archive_name='input.zip',
        archive_bytes=build_zip_bytes(entries), extraction_root=tmp_path)
    selected = select_single_shapefile_dataset(extracted)
    assert selected.prefix_path.name == 'caf\u00e9'
    assert selected.prefix_path.with_suffix('.shp').exists()


def test_actual_driver_rejects_disguised_geojson(tmp_path):
    path = tmp_path / 'disguised.shp'
    path.write_text('{"type":"FeatureCollection","features":[]}')
    with pytest.raises(ValueError):
        worker._load_shapefile_payload(shp_path=path, max_features=10, max_vertices_per_feature=10)


def test_exact_driver_checked_before_dataset_access(tmp_path, monkeypatch):
    class WrongDriver:
        driver = 'GeoJSON'
        def __enter__(self): return self
        def __exit__(self, *args): return False
        @property
        def bounds(self):
            pytest.fail('dataset bounds read before driver rejection')
    monkeypatch.setattr(worker.fiona, 'open', lambda *a, **k: WrongDriver())
    with pytest.raises(ValueError, match='driver'):
        worker._load_shapefile_payload(shp_path=tmp_path / 'input.shp', max_features=10, max_vertices_per_feature=10)


def test_json_duplicate_and_overflow_are_rejected_by_decoder():
    from wepppy.microservices.shape_converter.parser_ipc import decode_payload
    encoded = json.dumps(valid_payload())
    duplicate = encoded[:-1] + ', "source_crs_wkt": null}'
    with pytest.raises(ValueError, match='Duplicate'):
        decode_payload(duplicate.encode(), max_bytes=4096, max_features=10, max_vertices=10)
    for number in ('1e999', 'NaN', 'Infinity', '-Infinity'):
        data = encoded.replace('1.25', number).encode()
        with pytest.raises(ValueError, match='Non-finite|property value'):
            decode_payload(data, max_bytes=4096, max_features=10, max_vertices=10)


def test_json_budgets_exact_edges_and_escaped_strings(monkeypatch):
    from wepppy.microservices.shape_converter import parser_ipc as ipc
    monkeypatch.setattr(ipc, 'MAX_DEPTH', 2)
    monkeypatch.setattr(ipc, 'MAX_VALUES', 3)
    ipc._scan_budget('[{"x":"escaped \\\" [ { :"}]')  # array, object, string
    ipc._scan_budget('[1,2]')
    with pytest.raises(ValueError, match='value limit'):
        ipc._scan_budget('[1,2,3]')
    with pytest.raises(ValueError, match='nesting limit'):
        ipc._scan_budget('[[[]]]')


def test_payload_byte_limit_edges_and_atomic_write(tmp_path):
    from wepppy.microservices.shape_converter import parser_ipc as ipc
    payload = valid_payload()
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    path = tmp_path / 'result.json'
    ipc.write_payload(path, payload, max_bytes=len(data), max_features=1, max_vertices=1)
    assert ipc.read_payload(path, max_bytes=len(data), max_features=1, max_vertices=1) == payload
    assert not path.with_suffix('.partial').exists()
    with pytest.raises(ValueError):
        ipc.read_payload(path, max_bytes=len(data)-1, max_features=1, max_vertices=1)
    with pytest.raises(ValueError):
        ipc.write_payload(tmp_path / 'absent.json', payload, max_bytes=len(data)-1,
                          max_features=1, max_vertices=1)
    assert not (tmp_path / 'absent.json').exists()


def test_payload_symlink_fifo_and_missing_rejected(tmp_path):
    import os
    data = tmp_path / 'real'
    data.write_text(json.dumps(valid_payload()))
    link = tmp_path / 'link'
    link.symlink_to(data)
    fifo = tmp_path / 'fifo'
    os.mkfifo(fifo)
    for path in (link, fifo, tmp_path / 'missing', tmp_path):
        with pytest.raises(ShapeConverterError):
            convert._read_parser_payload(payload_path=path,
                worker_stdout='private-value', worker_stderr='private-value')


def test_collection_vertices_and_feature_limits(tmp_path, monkeypatch):
    payload = valid_payload()
    point = payload['geometries'][0]
    payload['geometries'] = [{'type': 'GeometryCollection', 'geometries': [point, point]}]
    monkeypatch.setattr(convert, '_MAX_VERTICES_PER_FEATURE', 2)
    assert read_payload(tmp_path, json.dumps(payload).encode()) == payload
    monkeypatch.setattr(convert, '_MAX_VERTICES_PER_FEATURE', 1)
    with pytest.raises(ShapeConverterError):
        read_payload(tmp_path, json.dumps(payload).encode())
    monkeypatch.setattr(convert, '_MAX_CONVERT_FEATURES', 0)
    with pytest.raises(ShapeConverterError):
        read_payload(tmp_path, json.dumps(valid_payload()).encode())


@pytest.mark.parametrize('geometry', [
    {'type': 'LineString', 'coordinates': [1, 2]},
    {'type': 'Polygon', 'coordinates': [[1, 2]]},
    {'type': 'MultiPolygon', 'coordinates': [[[1, 2]]]},
    {'type': 'GeometryCollection', 'geometries': [None]},
    {'type': 'Point', 'coordinates': [10**400, 2]},
])
def test_invalid_coordinate_nesting_rejected(tmp_path, geometry):
    payload = valid_payload()
    payload['geometries'] = [geometry]
    with pytest.raises(ShapeConverterError):
        read_payload(tmp_path, json.dumps(payload).encode())


def test_budget_checks_precede_decoder(monkeypatch):
    from wepppy.microservices.shape_converter import parser_ipc as ipc
    def forbidden(*args, **kwargs):
        pytest.fail('JSON allocated before budget rejection')
    monkeypatch.setattr(ipc.json, 'loads', forbidden)
    monkeypatch.setattr(ipc, 'MAX_VALUES', 2)
    with pytest.raises(ValueError, match='value limit'):
        ipc.decode_payload(b'[1,2]', max_bytes=100, max_features=10, max_vertices=10)
    monkeypatch.setattr(ipc, 'MAX_DEPTH', 1)
    with pytest.raises(ValueError, match='nesting limit'):
        ipc.decode_payload(b'[[]]', max_bytes=100, max_features=10, max_vertices=10)


def test_invalid_wkt_is_canonical_and_contains_no_payload(tmp_path):
    payload = valid_payload()
    payload['source_crs_wkt'] = 'private-crs-canary'
    decoded = read_payload(tmp_path, json.dumps(payload).encode())
    with pytest.raises(ShapeConverterError) as error:
        convert._loaded_shapefile_from_payload(decoded)
    assert error.value.code == 'invalid_shapefile'
    assert 'private-crs-canary' not in error.value.details


@pytest.mark.parametrize('geometry', [
    {'type': 'MultiLineString', 'coordinates': [[], [[1, 2], [2, 3]]]},
    {'type': 'MultiPolygon', 'coordinates': [[], [[[0, 0], [1, 0], [0, 1], [0, 0]]]]},
])
def test_malformed_multipart_returns_canonical_error(tmp_path, geometry):
    payload = valid_payload()
    payload['geometries'] = [geometry]
    decoded = read_payload(tmp_path, json.dumps(payload).encode())
    with pytest.raises(ShapeConverterError) as error:
        convert._loaded_shapefile_from_payload(decoded)
    assert error.value.code == 'invalid_shapefile'
    assert error.value.details == 'Invalid geometry in parser payload.'


def test_worker_diagnostics_are_discarded(tmp_path, monkeypatch):
    from types import SimpleNamespace
    (tmp_path / 'diagnostic_probe.py').write_text(
        'import os\nos.write(1, b"private-value" * 100000)\n'
        'os.write(2, b"\\xff" * 1000000)\nraise SystemExit(1)\n')
    monkeypatch.setenv('PYTHONPATH', str(tmp_path))
    monkeypatch.setattr(convert, '_PARSER_WORKER_MODULE', 'diagnostic_probe')
    with pytest.raises(ShapeConverterError) as error:
        convert._run_parser_worker(shp_path=tmp_path / 'a.shp', output_path=tmp_path / 'result.json',
                                   scratch=SimpleNamespace(request_dir=tmp_path))
    assert error.value.code == 'invalid_shapefile'
    assert error.value.details == 'Parser worker failed to parse the dataset.'
