from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from urllib.parse import urljoin

import pytest
import requests
from shapely.geometry import shape

from wepppy.microservices.vector_upload_normalization import (
    RetentionActor,
    prepare_vector_upload,
    validate_feature_collection_geometries,
)


pytestmark = pytest.mark.integration


def exact_converter_environment() -> tuple[str, Path]:
    """Bind opt-in HTTP tests to final5 and the retained, hashed fixture bytes."""
    converter_url = os.getenv("VECTOR_UPLOAD_INTEGRATION_URL")
    if not converter_url:
        pytest.skip("exact converter integration URL is not configured")
    fixture_root = Path(__file__).parents[1] / "data/vector_upload_final5"
    manifest = json.loads((fixture_root / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        content = (fixture_root / name).read_bytes()
        assert len(content) == expected["size"], name
        assert hashlib.sha256(content).hexdigest() == expected["sha256"], name
    response = requests.get(urljoin(converter_url, "/health/ready"), timeout=30)
    response.raise_for_status()
    readiness = response.json()
    assert readiness["status"] == "ok"
    assert readiness["check"] == "ready"
    assert readiness["parser"] == "shape_parser_cli"
    assert readiness["geoparquet_parser"] == "ready"
    assert readiness["provenance"] == "binary_binding_verified"
    assert readiness["geoparquet_parser_provenance"] == {
        "binary_name": "geoparquet_parser_cli",
        "binary_version": "geoparquet_parser_cli 0.0.0",
        "binary_sha256": "160854839d237acb4c369bc15f97d5e51ae3841aaaca37777ba2353cfdd79c47",
        "cargo_lock_sha256": "ce923427941fabe153c8b282dcfddeb1168b60670055ab34f47911d039748f13",
        "source_revision": "e172f9f8a23c10774f87828181048c72188ba78a",
    }
    return converter_url, fixture_root


def assert_feature_equivalence(actual: dict, expected: dict) -> None:
    """Compare every ordered feature/property and geometry, ignoring JSON layout."""
    assert actual["type"] == expected["type"] == "FeatureCollection"
    assert len(actual["features"]) == len(expected["features"])
    for received, source in zip(actual["features"], expected["features"]):
        assert received["properties"] == source["properties"]
        assert shape(received["geometry"]).equals(shape(source["geometry"]))


def assert_receipt(prepared, source: Path, canonical: Path) -> None:
    receipt = json.loads((prepared.attempt_dir / "normalization.json").read_text())
    original, = (prepared.attempt_dir / "original").iterdir()
    assert original.read_bytes() == source.read_bytes()
    assert receipt["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["canonical_sha256"] == hashlib.sha256(canonical.read_bytes()).hexdigest()
    assert receipt["status"] == "accepted"


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
    converter_url, fixture_root = exact_converter_environment()
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
        assert_receipt(prepared, source, canonical)
        parsed = json.loads(canonical.read_text())
        semantic_results.append(parsed)

    assert len(semantic_results) == 4
    for result in semantic_results:
        assert_feature_equivalence(result, semantic_results[0])
