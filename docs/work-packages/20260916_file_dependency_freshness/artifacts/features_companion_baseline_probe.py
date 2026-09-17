"""Real disposable GeoPackage/FileGDB export proving companion cache attribution.

Only catalog/profile selection is injected; planning, source reading, both native
writers, conversion, cache-index writes, and cache lookup remain real.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
from osgeo import ogr
from tests.nodb.mods.test_features_export_dependency_tracker import _catalog_with_attr_source
from wepppy.nodb.mods.features_export import service


with TemporaryDirectory(prefix="features-companion-freshness-") as temporary:
    root = Path(temporary)
    catalog = _catalog_with_attr_source(
        layer_id="test.attributes",
        geometry_locator={"kind": "relpath", "value": "geometry.geojson"},
    )
    (root / "geometry.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {"id": 1},
            "geometry": {"type": "Polygon", "coordinates": [
                [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        }],
    }))
    source = root / "attrs.parquet"
    pd.DataFrame({"id": [1], "value": [25.0]}).to_parquet(source, index=False)
    gpkg_request = {"format": "geopackage", "units": "si", "layers": ["test.attributes"]}
    gdb_request = {**gpkg_request, "format": "geodatabase"}
    with patch.object(service, "load_layer_catalog", return_value=catalog), patch.object(
        service, "resolve_published_profile_request",
        return_value=("prep-wepp-geodatabase", gdb_request),
    ):
        old_submission = service.prepare_export_submission(root, gdb_request)
        original = service.execute_features_export(
            root, runid="probe", config="test", payload=gpkg_request, job_id="original",
        )
        pd.DataFrame({"id": [1], "value": [75.0]}).to_parquet(source, index=False)
        new_submission = service.prepare_export_submission(root, gdb_request)
        assert old_submission.cache_key_parts.cache_key != new_submission.cache_key_parts.cache_key
        companion = service.co_create_post_wepp_geodatabase_artifact(
            root, source_job_id="original", source_job_result=original,
        )
        later = service.execute_features_export(
            root, runid="probe", config="test", payload=gdb_request, job_id="later",
        )
    archive_path = root / later["artifact_relpath"]
    with ZipFile(archive_path) as archive:
        gdb_root = next(name.split("/", 1)[0] for name in archive.namelist() if ".gdb/" in name)
    dataset = ogr.Open(f"/vsizip/{archive_path}/{gdb_root}")
    assert dataset is not None
    rows = [dict(feature.items()) for feature in dataset.GetLayer(0)]
    observed = {
        "backend": "real GDAL OpenFileGDB", "source": pd.read_parquet(source).to_dict("records"),
        "old_and_new_source_keys_differ": True,
        "companion": companion, "later_result": later, "exported": rows,
    }
    print(json.dumps(observed, indent=2))
    assert later["cache_hit"] is True
    assert rows[0]["value"] == 25.0
