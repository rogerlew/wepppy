from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.contracts import ExportWarning
from wepppy.nodb.mods.features_export.exporters import ExportWriterRequest, PreparedLayerPayload, get_export_writer
from wepppy.nodb.mods.features_export.manifest import (
    MANIFEST_GENERATOR_VERSION,
    MANIFEST_SCHEMA_VERSION,
    build_export_manifest,
    serialize_export_manifest,
    write_export_manifest,
)
from wepppy.nodb.mods.features_export.planner import resolve_export_plan

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def catalog():
    return load_layer_catalog()


def _resolved_plan(catalog):
    return resolve_export_plan(
        {
            "format": "geojson",
            "units": "si",
            "layers": [
                "wepp.summary.hillslopes",
                "watershed.channels",
            ],
            "output_scopes": ["roads", "baseline"],
        },
        catalog,
    )


def _layer_payloads(plan) -> dict[str, PreparedLayerPayload]:
    payloads: dict[str, PreparedLayerPayload] = {}
    for idx, layer in enumerate(plan.layers):
        payloads[layer.output_layer_id] = PreparedLayerPayload(
            output_layer_id=layer.output_layer_id,
            payload=f"manifest::{layer.output_layer_id}",
            row_count=200 + idx,
            feature_count=20 + idx,
        )
    return payloads


def _artifact_for_manifest(tmp_path: Path, plan):
    writer = get_export_writer("geojson")
    request = ExportWriterRequest(
        plan=plan,
        layer_payloads=_layer_payloads(plan),
        artifact_dir=tmp_path,
        artifact_basename="features_export",
    )
    return writer.write(request)


def _dependency_snapshot_mapping() -> dict[str, object]:
    return {
        "catalog_signature": "catalog-sig-1",
        "fingerprint": "dep-fingerprint-1",
        "entries": [
            {
                "relpath": "wepp/output/interchange/loss.parquet",
                "exists": True,
                "size": 123,
                "mtime_ns": 42,
                "content_hash_marker": "sha256",
                "content_hash_value": "abc123",
                "layer_id": "wepp.summary.hillslopes",
                "output_layer_id": "baseline__wepp.summary.hillslopes",
                "dependency_role": "source",
                "dependency_id": "metrics",
            }
        ],
    }


def test_build_export_manifest_includes_required_wp3_fields(
    tmp_path: Path,
    catalog,
) -> None:
    plan = _resolved_plan(catalog)
    artifact = _artifact_for_manifest(tmp_path, plan)

    manifest = build_export_manifest(
        plan=plan,
        artifact=artifact,
        dependency_snapshot=_dependency_snapshot_mapping(),
        artifact_id="artifact-123",
        cache_hit=False,
        source_job_id="job-123",
        generation_timestamp_utc="2026-03-26T17:45:00Z",
        requested_crs="wgs",
        resolved_crs="wgs",
        resolved_epsg=4326,
        additional_warnings=(
            ExportWarning(
                code="legacy_flags_ignored",
                message="Legacy flags are ignored under features export cutover.",
            ),
        ),
    )

    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["generator_version"] == MANIFEST_GENERATOR_VERSION
    assert manifest["artifact_id"] == "artifact-123"
    assert manifest["cache_hit"] is False
    assert manifest["source_job_id"] == "job-123"

    assert manifest["request"]["resolved"] == plan.request.to_mapping()
    assert manifest["catalog"] == {
        "catalog_version": plan.catalog_version,
        "schema_version": plan.schema_version,
    }
    assert manifest["dependency_snapshot"]["fingerprint"] == "dep-fingerprint-1"

    expected_layers = [layer.output_layer_id for layer in sorted(plan.layers, key=lambda item: item.output_layer_id)]
    assert [entry["output_layer_id"] for entry in manifest["layers"]] == expected_layers
    assert all("row_count" in entry and "feature_count" in entry for entry in manifest["layers"])

    warning_codes = [warning["code"] for warning in manifest["warnings"]]
    assert "scope_not_applicable" in warning_codes
    assert "legacy_flags_ignored" in warning_codes


def test_manifest_serialization_is_deterministic_and_write_step_is_separate(
    tmp_path: Path,
    catalog,
) -> None:
    plan = _resolved_plan(catalog)
    artifact = _artifact_for_manifest(tmp_path / "artifact", plan)

    manifest_a = build_export_manifest(
        plan=plan,
        artifact=artifact,
        dependency_snapshot={
            "entries": [{"b": 2, "a": 1}],
            "catalog_signature": "catalog-sig",
            "fingerprint": "dep-fingerprint",
        },
        artifact_id="artifact-abc",
        cache_hit=True,
        source_job_id="job-origin",
        generation_timestamp_utc="2026-03-26T18:00:00Z",
        additional_warnings=(
            {"code": "legacy_flags_ignored", "message": "legacy ignored"},
            {"code": "legacy_flags_ignored", "message": "legacy ignored"},
        ),
    )
    manifest_b = build_export_manifest(
        plan=plan,
        artifact=artifact,
        dependency_snapshot={
            "fingerprint": "dep-fingerprint",
            "catalog_signature": "catalog-sig",
            "entries": [{"a": 1, "b": 2}],
        },
        artifact_id="artifact-abc",
        cache_hit=True,
        source_job_id="job-origin",
        generation_timestamp_utc="2026-03-26T18:00:00Z",
        additional_warnings=(
            {"message": "legacy ignored", "code": "legacy_flags_ignored"},
        ),
    )

    serialized_a = serialize_export_manifest(manifest_a)
    serialized_b = serialize_export_manifest(manifest_b)

    assert serialized_a == serialized_b

    manifest_path = write_export_manifest(tmp_path / "manifest.json", manifest_a)
    assert manifest_path.exists()
    assert manifest_path.read_text(encoding="utf-8") == serialized_a

    parsed = json.loads(serialized_a)
    assert parsed["artifact"]["artifact_relpath"] == artifact.artifact_relpath
    assert parsed["warnings"].count({"code": "legacy_flags_ignored", "message": "legacy ignored"}) == 1
