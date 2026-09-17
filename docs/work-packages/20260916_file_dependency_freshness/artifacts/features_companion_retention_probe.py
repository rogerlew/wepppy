"""Actual accepted native companion survives until a second conversion fails.

Disposable local data only. Catalog/profile are fixture selections; the first
conversion, cache and filesystem are real. The second converter alone raises
ENOSPC to exercise the existing caller's failure-retention boundary.
"""
import errno
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from tests.nodb.mods.test_features_export_dependency_tracker import _catalog_with_attr_source
from wepppy.nodb.mods.features_export import service


with TemporaryDirectory(prefix="features-companion-retention-") as temporary:
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
    pd.DataFrame({"id": [1], "value": [25.0]}).to_parquet(root / "attrs.parquet", index=False)
    gpkg_request = {"format": "geopackage", "units": "si", "layers": ["test.attributes"]}
    gdb_request = {**gpkg_request, "format": "geodatabase"}
    with patch.object(service, "load_layer_catalog", return_value=catalog), patch.object(
        service, "resolve_published_profile_request",
        return_value=("prep-wepp-geodatabase", gdb_request),
    ):
        original = service.execute_features_export(
            root, runid="probe", config="test", payload=gpkg_request, job_id="original",
        )
        companion = service.co_create_post_wepp_geodatabase_artifact(
            root, source_job_id="original", source_job_result=original,
        )
        accepted_path = root / companion["artifact_relpath"]
        accepted_bytes = accepted_path.read_bytes()
        cache_path = root / "export/features/cache/index.json"
        cache_before = cache_path.read_bytes()
        with patch.object(service, "convert_geopackage_to_openfilegdb", side_effect=OSError(
            errno.ENOSPC, "disposable conversion failure injected by review",
        )):
            try:
                service.co_create_post_wepp_geodatabase_artifact(
                    root, source_job_id="original", source_job_result=original,
                )
            except OSError as exc:
                failure = {"type": type(exc).__name__, "errno": exc.errno}
            else:
                raise AssertionError("Expected injected converter failure")
    observed = {
        "first_conversion": "real GDAL OpenFileGDB",
        "second_conversion": "injected ENOSPC at native converter call",
        "accepted_sha256": hashlib.sha256(accepted_bytes).hexdigest(),
        "accepted_size": len(accepted_bytes),
        "failure": failure,
        "accepted_artifact_still_exists": accepted_path.exists(),
        "cache_index_unchanged": cache_path.read_bytes() == cache_before,
        "accepted_artifact_relpath": companion["artifact_relpath"],
    }
    print(json.dumps(observed, indent=2))
    assert observed["accepted_artifact_still_exists"] is False
    assert observed["cache_index_unchanged"] is True
