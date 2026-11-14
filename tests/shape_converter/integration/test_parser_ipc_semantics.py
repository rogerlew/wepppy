"""Compare real Rust-parser artifacts with retained Fiona oracle fixtures."""
from __future__ import annotations

import asyncio
import io
import json
import struct
from types import SimpleNamespace

import fiona
import pyarrow.parquet as pq
import pytest
from shapely import from_wkb
from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import (
    build_minimal_point_dataset,
    build_multipatch_dataset,
    build_multipart_dataset,
    build_multipoint_dataset,
    build_zip_bytes,
)
from wepppy.microservices.shape_converter.app import create_app
from wepppy.microservices.shape_converter import convert

pytestmark = [pytest.mark.integration, pytest.mark.microservice]


def _multipatch_entries():
    points = [(0., 0.), (1., 0.), (0., 1.), (2., 0.), (3., 0.), (3., 1.), (2., 1.), (2., 0.)]
    body = (struct.pack('<i4d2i', 31, 0, 0, 3, 1, 2, 8)
            + struct.pack('<4i', 0, 3, 0, 2)
            + b''.join(struct.pack('<2d', *point) for point in points)
            + struct.pack('<10d', *([0.] * 10)))
    def header(size):
        return (struct.pack('>7i', 9994, 0, 0, 0, 0, 0, size // 2)
                + struct.pack('<2i8d', 1000, 31, 0, 0, 3, 1, 0, 0, 0, 0))
    entries = build_minimal_point_dataset('a')
    entries['a.shp'] = header(108 + len(body)) + struct.pack('>2i', 1, len(body) // 2) + body
    entries['a.shx'] = header(108) + struct.pack('>2i', 50, len(body) // 2)
    return entries


def _semantic_datasets():
    datasets = {
        'multipoint_m': build_multipoint_dataset(prefix='multipoint-m', shape_type=28),
        'polygon_m': build_multipart_dataset(
            prefix='polygon-m',
            shape_type=25,
            parts=[
                [(0., 0.), (0., 1.), (1., 1.), (1., 0.), (0., 0.)],
                [(2., 0.), (2., 1.), (3., 1.), (3., 0.), (2., 0.)],
            ],
        ),
        'multipatch_fan': build_multipatch_dataset(
            prefix='multipatch-fan',
            parts=[(1, [(0., 0., 1.), (1., 0., 1.), (1., 1., 1.), (0., 1., 1.)])],
        ),
    }
    canonical_prj = build_minimal_point_dataset(prefix='crs')['crs.prj']
    for entries in datasets.values():
        shp_name = next(name for name in entries if name.endswith('.shp'))
        entries[f'{shp_name[:-4]}.prj'] = canonical_prj
    return datasets


@pytest.mark.parametrize('dataset', ['multipoint_m', 'polygon_m', 'multipatch_fan'])
def test_rust_parser_geometry_matches_retained_fiona_oracle(tmp_path, dataset):
    entries = _semantic_datasets()[dataset]
    source = tmp_path / 'source'
    source.mkdir()
    for name, content in entries.items():
        (source / name).write_bytes(content)
    shp_path = next(source.glob('*.shp'))
    with fiona.open(shp_path) as collection:
        fiona_geometry = next(iter(collection))['geometry'].__geo_interface__

    output_path = source / 'payload.json'
    asyncio.run(convert._run_parser_worker(
        shp_path=shp_path,
        output_path=output_path,
        scratch=SimpleNamespace(request_dir=source),
    ))
    rust_geometry = json.loads(output_path.read_text(encoding='utf-8'))['geometries'][0]

    assert rust_geometry == json.loads(json.dumps(fiona_geometry))


@pytest.mark.parametrize('output_format', ['geojson', 'geoparquet'])
@pytest.mark.parametrize(
    'dataset',
    ['point_null', 'multipatch', 'multipoint_m', 'polygon_m', 'multipatch_fan'],
)
def test_real_worker_output_semantics_and_cleanup(tmp_path, output_format, dataset):
    if dataset == 'point_null':
        source = tmp_path / 'source'
        source.mkdir()
        with fiona.open(source / 'a.shp', 'w', driver='ESRI Shapefile', crs='EPSG:4326',
                        schema={'geometry': '3D Point', 'properties': {
                            'NAME': 'str', 'COUNT': 'int', 'VALUE': 'float', 'DATE': 'date'}}) as sink:
            sink.write({'geometry': {'type': 'Point', 'coordinates': (10, 20, 3)},
                        'properties': {'NAME': 'demo', 'COUNT': 7, 'VALUE': 1.25, 'DATE': '2026-01-02'}})
            sink.write({'geometry': None,
                        'properties': {'NAME': None, 'COUNT': None, 'VALUE': None, 'DATE': None}})
        entries = {path.name: path.read_bytes() for path in source.iterdir()}
    elif dataset == 'multipatch':
        entries = _multipatch_entries()
    else:
        entries = _semantic_datasets()[dataset]
    scratch = tmp_path / 'scratch'
    with TestClient(create_app()) as client:
        client.app.state.scratch_root = scratch
        response = client.post('/v1/convert',
            files={'archive': ('input.zip', build_zip_bytes(entries), 'application/zip')},
            data={'output_format': output_format, 'target_crs': 'same_as_shapefile'})
        assert response.status_code == 200, response.text
        assert 'attachment' in response.headers['content-disposition']
        metadata = client.get(response.headers['x-shape-converter-metadata-path']).json()
    assert not scratch.exists() or list(scratch.iterdir()) == []
    assert metadata['feature_count'] == (2 if dataset == 'point_null' else 1)
    if output_format == 'geojson':
        document = response.json()
        features = document['features']
        properties = [feature['properties'] for feature in features]
        geometries = [feature['geometry'] for feature in features]
    else:
        table = pq.read_table(io.BytesIO(response.content))
        geo_metadata = json.loads(table.schema.metadata[b'geo'])
        column = geo_metadata['primary_column']
        assert geo_metadata['columns'][column]['crs'] is not None
        records = table.to_pylist()
        properties = [{key: value for key, value in record.items() if key != column} for record in records]
        geometries = [None if record[column] is None else from_wkb(record[column]).__geo_interface__
                      for record in records]
    if dataset == 'point_null':
        assert len(properties) == 2
        assert properties[0] == {'NAME': 'demo', 'COUNT': 7, 'VALUE': 1.25, 'DATE': '2026-01-02'}
        assert type(properties[0]['COUNT']) is int
        assert all(value is None for value in properties[1].values())
        assert geometries[0]['type'] == 'Point'
        assert list(geometries[0]['coordinates']) == [10, 20, 3]
        assert geometries[1] is None
        assert metadata['bbox'] == [10, 20, 10, 20]
    elif dataset == 'multipatch':
        assert properties == [{'NAME': 'demo'}]
        assert geometries[0]['type'] == 'GeometryCollection'
        assert len(geometries[0]['geometries']) == 2
        assert all(item['type'] == 'MultiPolygon' for item in geometries[0]['geometries'])
        assert metadata['bbox'] == [0, 0, 3, 1]
    else:
        expected_types = {
            'multipoint_m': 'MultiPoint',
            'polygon_m': 'MultiPolygon',
            'multipatch_fan': 'MultiPolygon',
        }
        assert properties == [{
            'NAME': {
                'multipoint_m': 'multipoint',
                'polygon_m': 'multipart',
                'multipatch_fan': 'multipatch',
            }[dataset]
        }]
        assert geometries[0]['type'] == expected_types[dataset]
        if dataset == 'multipoint_m':
            assert len(geometries[0]['coordinates']) == 2
            assert metadata['bbox'] == [10, 20, 12, 21]
        elif dataset == 'polygon_m':
            assert len(geometries[0]['coordinates']) == 2
            assert metadata['bbox'] == [0, 0, 3, 1]
        else:
            assert len(geometries[0]['coordinates']) == 2
            assert metadata['bbox'] == [0, 0, 1, 1]
