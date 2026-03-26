from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.nodb.mods.features_export.cache_key import (
    CACHE_INDEX_RELPATH,
    build_cache_key,
    build_request_hash,
    cache_index_path,
    get_cache_index_entry,
    load_cache_index,
    upsert_cache_index_entry,
)
from wepppy.nodb.mods.features_export.catalog_loader import parse_layer_catalog
from wepppy.nodb.mods.features_export.planner import resolve_export_plan

pytestmark = pytest.mark.unit


def _catalog() -> object:
    return parse_layer_catalog(
        {
            "metadata": {
                "catalog_version": "wp2-test",
                "schema_version": 2,
                "updated_at_utc": "2026-03-26T00:00:00Z",
                "owner": "tests",
                "status": "draft",
                "resolver_contract": {
                    "allowed_locator_kinds": ["nodb_ref", "relpath", "path_template"],
                    "path_template_vars": {
                        "scope_root": {
                            "values": {
                                "baseline": "output",
                                "roads": "roads/output",
                            }
                        }
                    },
                    "temporal_modes": ["annual_average", "yearly", "event"],
                    "event_selectors": ["date", "return_period"],
                },
            },
            "layers": [
                {
                    "layer_id": "test.layer",
                    "family": "test",
                    "scope_class": "scope_invariant",
                    "geometry": {
                        "type": "polygon",
                        "locator": {"kind": "relpath", "value": "geometry.geojson"},
                        "feature_id_keys": ["id"],
                    },
                    "join": {"primary_key": "id", "fallback_keys": []},
                    "sources": [
                        {
                            "source_id": "attrs",
                            "kind": "parquet",
                            "locator": {"kind": "relpath", "value": "attrs.parquet"},
                            "required": True,
                            "role": "attributes",
                        }
                    ],
                    "dependencies": [],
                    "temporal": {
                        "supported_modes": [],
                        "grain": "none",
                        "time_columns": [],
                        "mode_rules": {},
                    },
                    "measures": {"required": ["id"], "optional": []},
                }
            ],
        },
        source_name="<memory>",
    )


def _resolve_plan(*, units: str, swat_run_id: str | None) -> object:
    payload: dict[str, object] = {
        "format": "geoparquet",
        "units": units,
        "layers": ["test.layer"],
    }
    if swat_run_id is not None:
        payload["swat_run_id"] = swat_run_id
    return resolve_export_plan(payload, _catalog())


def test_build_request_hash_requires_concrete_swat_run_id() -> None:
    plan = _resolve_plan(units="si", swat_run_id=None)

    with pytest.raises(ValueError, match="concrete swat_run_id"):
        build_request_hash(plan)


def test_build_request_hash_requires_unitizer_fingerprint_for_project_units() -> None:
    plan = _resolve_plan(units="project", swat_run_id="run_2026032601")

    with pytest.raises(ValueError, match="Unitizer preferences fingerprint"):
        build_request_hash(plan)

    hash_a = build_request_hash(plan, unitizer_preferences_fingerprint="pref-a")
    hash_b = build_request_hash(plan, unitizer_preferences_fingerprint="pref-b")

    assert hash_a != hash_b
    assert len(hash_a) == 64


def test_build_cache_key_combines_request_hash_and_dependency_fingerprint() -> None:
    plan = _resolve_plan(units="si", swat_run_id="run_2026032601")

    parts = build_cache_key(plan, "dep-fingerprint-123")

    assert parts.cache_key == f"{parts.request_hash}+dep-fingerprint-123"
    assert parts.dependency_fingerprint == "dep-fingerprint-123"


def test_cache_index_load_get_upsert_roundtrip(tmp_path: Path) -> None:
    assert load_cache_index(tmp_path) == {"schema_version": 1, "entries": {}}

    upsert_cache_index_entry(
        tmp_path,
        "key-z",
        {
            "artifact_id": "artifact-z",
            "artifact_paths": ["export/features/artifacts/artifact-z/data.zip"],
            "source_job_id": "job-z",
            "manifest_relpath": "export/features/jobs/job-z/manifest.json",
        },
    )
    upsert_cache_index_entry(
        tmp_path,
        "key-a",
        {
            "artifact_id": "artifact-a",
            "artifact_paths": ["export/features/artifacts/artifact-a/data.zip"],
            "source_job_id": "job-a",
            "manifest_relpath": "export/features/jobs/job-a/manifest.json",
        },
    )

    index_payload = load_cache_index(tmp_path)
    assert list(index_payload["entries"].keys()) == ["key-a", "key-z"]

    entry = get_cache_index_entry(tmp_path, "key-a")
    assert entry is not None
    assert entry["artifact_id"] == "artifact-a"

    index_file = cache_index_path(tmp_path)
    assert index_file == tmp_path / CACHE_INDEX_RELPATH
    assert index_file.exists()

    serialized = index_file.read_text(encoding="utf-8")
    loaded = json.loads(serialized)
    assert list(loaded["entries"].keys()) == ["key-a", "key-z"]
