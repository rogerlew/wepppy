"""Real boundary archive regression for Culvert_web_app issue #307."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

pytest.importorskip("starlette")
from starlette.testclient import TestClient

from wepppy.microservices.shape_converter import create_app

pytestmark = [pytest.mark.integration, pytest.mark.microservice]
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "data" / "shape_converter"


@pytest.mark.parametrize("output_format", ["geojson", "geoparquet"])
def test_boundary_scientific_dbf_values_survive_conversion(output_format: str) -> None:
    archive = (FIXTURE_DIR / "boundary.zip").read_bytes()
    provenance = json.loads((FIXTURE_DIR / "boundary.provenance.json").read_text())
    assert hashlib.sha256(archive).hexdigest() == provenance["sha256"]
    # Guard against replacing the reproducer with a rounded, rewritten DBF.
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        dbf = source.read("santee_boundary_f.dbf")
    assert b"2.39087662256e-01" in dbf
    assert b"2.41558165692e-03" in dbf

    if output_format == "geoparquet":
        pq = pytest.importorskip("pyarrow.parquet")

    with TestClient(create_app()) as client:
        inspection = client.post(
            "/v1/inspect",
            files={"archive": ("boundary.zip", archive, "application/zip")},
        )
        assert inspection.status_code == 200, inspection.text
        assert inspection.json()["feature_count"] == 1
        response = client.post(
            "/v1/convert",
            files={"archive": ("boundary.zip", archive, "application/zip")},
            data={"output_format": output_format, "target_crs": "wgs84"},
        )
        assert response.status_code == 200, response.text

    if output_format == "geojson":
        features = response.json()["features"]
        assert len(features) == 1
        properties = features[0]["properties"]
        assert features[0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    else:
        table = pq.read_table(io.BytesIO(response.content))
        assert table.num_rows == 1
        properties = table.to_pylist()[0]
        assert properties["geometry"]

    # Exact equality is intentional: approximate comparison masks DBF rounding.
    for name, expected in provenance["expected_numeric_properties"].items():
        assert isinstance(properties[name], float)
        assert properties[name] == expected
    assert properties["NAME"] == "Santee Experimental Forest"
