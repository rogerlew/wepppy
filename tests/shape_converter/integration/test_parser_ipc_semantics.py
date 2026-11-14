"""Read artifacts from the real Fiona worker and JSON IPC boundary."""
from __future__ import annotations

import io
import json
import struct

import fiona
import pyarrow.parquet as pq
import pytest
from shapely import from_wkb
from starlette.testclient import TestClient

from tests.shape_converter.helpers.archive_builder import build_minimal_point_dataset, build_zip_bytes
from wepppy.microservices.shape_converter.app import create_app

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


@pytest.mark.parametrize('output_format', ['geojson', 'geoparquet'])
@pytest.mark.parametrize('dataset', ['point_null', 'multipatch'])
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
    else:
        entries = _multipatch_entries()
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
        assert all(value is None for value in properties[1].values())
        assert geometries[0]['type'] == 'Point'
        assert list(geometries[0]['coordinates']) == [10, 20, 3]
        assert geometries[1] is None
        assert metadata['bbox'] == [10, 20, 10, 20]
    else:
        assert properties == [{'NAME': 'demo'}]
        assert geometries[0]['type'] == 'GeometryCollection'
        assert len(geometries[0]['geometries']) == 2
        assert all(item['type'] == 'MultiPolygon' for item in geometries[0]['geometries'])
        assert metadata['bbox'] == [0, 0, 3, 1]
