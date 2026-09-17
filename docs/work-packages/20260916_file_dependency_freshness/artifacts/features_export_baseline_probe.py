"""Actual submission/export/cache reuse with disposable GeoJSON and parquet."""
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile
import pandas as pd
from tests.nodb.mods.test_features_export_dependency_tracker import _catalog_with_attr_source
from wepppy.nodb.mods.features_export import service

with TemporaryDirectory(prefix='export-freshness-') as temporary:
    root = Path(temporary)
    catalog = _catalog_with_attr_source(layer_id='test.attributes', geometry_locator={'kind': 'relpath', 'value': 'geometry.geojson'})
    (root / 'geometry.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'id': 1}, 'geometry': {'type': 'Polygon', 'coordinates': [[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}
    ]}))
    path = root / 'attrs.parquet'
    pd.DataFrame({'id': [1], 'value': [25.0]}).to_parquet(path, index=False)
    before = path.stat()
    payload = {'format': 'parquet', 'units': 'si', 'layers': ['test.attributes']}
    with patch.object(service, 'load_layer_catalog', return_value=catalog):
        first_submission = service.prepare_export_submission(root, payload)
        first = service.execute_features_export(root, runid='probe', config='test', payload=payload, job_id='first')
        pd.DataFrame({'id': [1], 'value': [75.0]}).to_parquet(path, index=False)
        assert path.stat().st_size == before.st_size
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        second_submission = service.prepare_export_submission(root, payload)
        second = service.execute_features_export(root, runid='probe', config='test', payload=payload, job_id='second')
    artifact = root / second['artifact_relpath']
    with ZipFile(artifact) as archive:
        frames = {name: pd.read_parquet(io.BytesIO(archive.read(name))).to_dict('records')
                  for name in archive.namelist() if name.endswith('.parquet')}
    print(json.dumps({'same_cache_key': first_submission.cache_key_parts.cache_key == second_submission.cache_key_parts.cache_key,
                      'first_result': first, 'second_result': second,
                      'actual_source': pd.read_parquet(path).to_dict('records'), 'exported': frames}, indent=2, default=str))
