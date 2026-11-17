from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from shapely.geometry import shape

from wepppy.microservices.vector_upload_normalization import (
    RetentionActor,
    prepare_vector_upload,
    validate_feature_collection_geometries,
)


pytestmark = pytest.mark.integration


class _Reservation:
    reservation_id = "exact-image-integration"

    def bind_attempt(self, _attempt_dir: Path) -> None:
        pass

    def commit(self, exact_bytes: int) -> None:
        self.exact_bytes = exact_bytes

    def release_prewrite(self) -> None:
        pass


class _Ledger:
    def reserve(self, **_kwargs):
        return _Reservation()


class _Lease:
    def assert_owned(self) -> None:
        pass

    def release(self) -> None:
        pass


@pytest.mark.parametrize(
    ("workflow", "geometry", "allowed"),
    [
        ("roads", "line", ("LineString", "MultiLineString")),
        ("ag_fields", "polygon", ("Polygon", "MultiPolygon")),
        ("omni_run", "polygon", ("Polygon", "MultiPolygon")),
        ("omni_dry_run", "polygon", ("Polygon", "MultiPolygon")),
        ("batch_runner", "polygon", ("Polygon", "MultiPolygon")),
    ],
)
def test_exact_image_format_equivalence_at_receiving_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workflow: str,
    geometry: str,
    allowed: tuple[str, ...],
) -> None:
    converter_url = os.getenv("VECTOR_UPLOAD_INTEGRATION_URL")
    fixture_root_value = os.getenv("VECTOR_UPLOAD_INTEGRATION_FIXTURES")
    if not converter_url or not fixture_root_value:
        pytest.skip("exact converter integration environment is not configured")
    fixture_root = Path(fixture_root_value)
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    semantic_results: list[dict[str, object]] = []

    for suffix, fixture_suffix in (
        ("geojson", "geojson"),
        ("zip", "zip"),
        ("parquet", "parquet"),
        ("geoparquet", "parquet"),
    ):
        source = fixture_root / f"{geometry}.{fixture_suffix}"
        project = tmp_path / workflow / suffix
        project.mkdir(parents=True)
        attempts = project / "vector_upload_attempts"
        with source.open("rb") as stream:
            prepared = prepare_vector_upload(
                raw_filename=f"{geometry}.{suffix}",
                stream=stream,
                endpoint_max_bytes=10 * 1024 * 1024,
                attempt_root=attempts,
                evidence_roots=(attempts,),
                filesystem_root=tmp_path,
                project_key=f"integration:{workflow}:{suffix}",
                workflow=workflow,
                project_identity="exact-image-integration",
                actor=RetentionActor("human", 1),
                validator=lambda _path, payload: validate_feature_collection_geometries(payload, allowed),
                converter_url=converter_url,
                ledger=_Ledger(),
                scope_lease_factory=lambda _key: _Lease(),
            )
        canonical = project / "accepted.geojson"
        prepared.publish(
            mutation=lambda candidate: shutil.copy2(candidate, canonical),
            canonical_path=canonical,
            canonical_relative_path=f"{workflow}/{suffix}/accepted.geojson",
        )
        receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
        original = next((prepared.attempt_dir / "original").iterdir())
        assert hashlib.sha256(original.read_bytes()).hexdigest() == receipt["source_sha256"]
        assert receipt["status"] == "accepted"
        parsed = json.loads(canonical.read_text())
        semantic_results.append({
            "geometry": parsed["features"][0]["geometry"],
            "properties": parsed["features"][0]["properties"],
        })

    assert len(semantic_results) == 4
    assert all(result["properties"] == semantic_results[0]["properties"] for result in semantic_results)
    baseline = shape(semantic_results[0]["geometry"])
    assert all(baseline.equals(shape(result["geometry"])) for result in semantic_results[1:])
