"""Service execution, caching, and artifact publication tests."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.cache_key import CacheKeyParts
from wepppy.nodb.mods.features_export.catalog_loader import load_layer_catalog
from wepppy.nodb.mods.features_export.contracts import (
    NormalizedExportRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.dependency_tracker import DependencyEntry, DependencySnapshot
from wepppy.nodb.mods.features_export.exporters import (
    ExportArtifactMetadata,
    ExportedLayerArtifact,
    PreparedLayerPayload,
)
from wepppy.nodb.mods.features_export.readme_builder import build_export_readme

pytestmark = pytest.mark.unit


class _DummyWriter:
    def __init__(self, wd: Path) -> None:
        self._wd = wd

    def write(self, request) -> ExportArtifactMetadata:
        artifact_path = request.artifact_dir / "features_export.gpkg"
        with sqlite3.connect(artifact_path) as conn:
            conn.execute("PRAGMA application_id=0x47504B47")
            conn.execute(
                """
                CREATE TABLE gpkg_contents (
                    table_name TEXT NOT NULL PRIMARY KEY,
                    data_type TEXT NOT NULL
                )
                """
            )
            conn.commit()
        artifact_relpath = artifact_path.relative_to(self._wd).as_posix()

        layer_output = ExportedLayerArtifact(
            layer_id="watershed.subcatchments",
            output_layer_id="shared__watershed.subcatchments",
            scope="shared",
            scope_class="scope_invariant",
            format="geopackage",
            relpath=artifact_relpath,
            row_count=1,
            feature_count=1,
        )
        return ExportArtifactMetadata(
            format="geopackage",
            artifact_relpath=artifact_relpath,
            artifact_path=str(artifact_path),
            layer_outputs=(layer_output,),
            warnings=(),
            packaged_member_relpaths=(),
        )


class _DummyZipWriter:
    def __init__(self, wd: Path) -> None:
        self._wd = wd

    def write(self, request) -> ExportArtifactMetadata:
        artifact_path = request.artifact_dir / "features_export.parquet.zip"
        member_path = request.artifact_dir / "hillslopes.parquet"
        member_path.write_bytes(b"dummy parquet bytes")

        with zipfile.ZipFile(artifact_path, "w") as zip_handle:
            zip_handle.writestr("hillslopes.parquet", member_path.read_bytes())

        layer_output = ExportedLayerArtifact(
            layer_id="watershed.subcatchments",
            output_layer_id="shared__watershed.subcatchments",
            scope="shared",
            scope_class="scope_invariant",
            format="parquet",
            relpath="hillslopes.parquet",
            row_count=1,
            feature_count=1,
        )
        return ExportArtifactMetadata(
            format="parquet",
            artifact_relpath=artifact_path.relative_to(self._wd).as_posix(),
            artifact_path=str(artifact_path),
            layer_outputs=(layer_output,),
            warnings=(),
            packaged_member_relpaths=("hillslopes.parquet",),
        )


def _write_valid_geopackage_zip(artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    gpkg_member_path = artifact_path.parent / "features_export.gpkg"
    with sqlite3.connect(gpkg_member_path) as conn:
        conn.execute("PRAGMA application_id=0x47504B47")
        conn.commit()

    with zipfile.ZipFile(artifact_path, "w") as zip_handle:
        zip_handle.write(gpkg_member_path, arcname="features_export.gpkg")


def _build_submission(cache_key: str, *, format_token: str = "geopackage") -> service.FeaturesExportSubmission:
    request = NormalizedExportRequest(
        format=format_token,
        units="si",
        layers=("watershed.subcatchments",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
            ),
        ),
        warnings=(),
    )
    dependency_snapshot = DependencySnapshot(
        catalog_signature="catalog-signature",
        entries=(),
        fingerprint="dependency-fingerprint",
    )
    cache_key_parts = CacheKeyParts(
        request_hash="request-hash",
        dependency_fingerprint=dependency_snapshot.fingerprint,
        cache_key=cache_key,
    )
    return service.FeaturesExportSubmission(
        catalog=SimpleNamespace(),
        plan=plan,
        dependency_snapshot=dependency_snapshot,
        cache_key_parts=cache_key_parts,
        unitizer_preferences_fingerprint=None,
    )


def _stub_materialize_export_payloads(submission, *, wd, runid):  # noqa: ARG001
    payload = PreparedLayerPayload(
        output_layer_id="shared__watershed.subcatchments",
        payload="{}",
        row_count=1,
        feature_count=1,
    )
    return submission.plan, {"shared__watershed.subcatchments": payload}, {}


def test_layer_outputs_from_cache_entry_skips_malformed_entries_and_falls_back_to_plan() -> None:
    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    layer = ResolvedLayerPlan(
        layer_id="watershed.subcatchments",
        family="watershed",
        scope_class="scope_invariant",
        scope="shared",
        output_layer_id="shared__watershed.subcatchments",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(layer,),
        warnings=(),
    )

    outputs = service._layer_outputs_from_cache_entry(
        {
            "layer_outputs": [
                {"layer_id": "", "output_layer_id": "missing-layer-id"},
                {"layer_id": "missing-output-id", "output_layer_id": ""},
                {"scope": "shared"},
                123,
            ]
        },
        plan,
        "export/features/artifacts/cache/features_export.gpkg",
        "geopackage",
    )

    assert len(outputs) == 1
    assert outputs[0].layer_id == "watershed.subcatchments"
    assert outputs[0].output_layer_id == "shared__watershed.subcatchments"
    assert outputs[0].row_count is None
    assert outputs[0].feature_count is None


def test_execute_features_export_rejects_empty_job_id_before_export_dir_creation(
    tmp_path: Path,
) -> None:
    export_root = tmp_path / "export"
    assert not export_root.exists()

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.execute_features_export(
            tmp_path,
            runid="run-1",
            config="cfg",
            payload={"format": "geopackage"},
            job_id="",
        )

    assert exc.value.status_code == 500
    assert str(exc.value) == "job_id must be a non-empty string."
    assert not export_root.exists()


def test_execute_features_export_creates_export_root_before_cache_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "get_cache_index_entry", lambda wd, cache_key: None)

    def _fake_cache_miss(
        wd: Path,
        *,
        runid: str,
        config: str,
        job_id: str,
        submission: service.FeaturesExportSubmission,
    ) -> dict[str, object]:
        assert (wd / "export").is_dir()
        assert runid == "run-1"
        assert config == "cfg"
        assert job_id == "job-source"
        assert submission.cache_key_parts.cache_key == "request-hash+dependency-fingerprint"
        return {"ok": True}

    monkeypatch.setattr(service, "_run_cache_miss_export", _fake_cache_miss)
    assert not (tmp_path / "export").exists()

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-source",
    )

    assert result == {"ok": True}
    assert (tmp_path / "export").is_dir()


def test_execute_features_export_cache_miss_result_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-source",
    )

    assert result["cache_hit"] is False
    assert result["source_job_id"] is None
    assert isinstance(result["artifact_id"], str) and result["artifact_id"]
    assert (
        result["download_url"]
        == "/rq-engine/api/runs/run-1/cfg/export/features/job/job-source/download"
    )
    assert result["manifest_relpath"] == "export/features/jobs/job-source/manifest.json"
    assert isinstance(result["warnings"], list)
    assert (tmp_path / str(result["artifact_relpath"])).is_file()
    assert (tmp_path / result["manifest_relpath"]).is_file()
    assert str(result["artifact_relpath"]).endswith(".zip")

    artifact_zip_path = tmp_path / str(result["artifact_relpath"])
    with zipfile.ZipFile(artifact_zip_path, "r") as zip_handle:
        names = set(zip_handle.namelist())
        assert "manifest.json" in names
        assert "README.md" in names
        assert "features_export.gpkg" in names
        assert "profile.yml" not in names
        assert not any(name.endswith(".yml") for name in names)

        manifest = json.loads(zip_handle.read("manifest.json").decode("utf-8"))
        readme_text = zip_handle.read("README.md").decode("utf-8")

    assert manifest["artifact"]["packaged_member_relpaths"] == [
        "README.md",
        "features_export.gpkg",
        "manifest.json",
    ]
    assert manifest["artifact_id"] == result["artifact_id"]
    assert manifest["artifact"]["artifact_relpath"] == "features_export.geopackage.zip"
    assert "| Run ID | run-1 |" in readme_text
    assert "| Config | cfg |" in readme_text
    assert f"| Artifact ID | {result['artifact_id']} |" in readme_text
    assert "shared__watershed.subcatchments" in readme_text
    assert "features_export.gpkg" in readme_text
    assert "`manifest.json` is the canonical machine-readable provenance" in readme_text

    cache_entry = service.get_cache_index_entry(tmp_path, submission.cache_key_parts.cache_key)
    assert cache_entry is not None
    assert cache_entry["source_job_id"] == "job-source"


def test_execute_features_export_cache_miss_retains_final_zip_for_zip_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(
        cache_key="request-hash+dependency-fingerprint+parquet",
        format_token="parquet",
    )
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyZipWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "parquet"},
        job_id="job-source",
    )

    artifact_zip_path = tmp_path / str(result["artifact_relpath"])
    assert artifact_zip_path.is_file()
    with zipfile.ZipFile(artifact_zip_path, "r") as zip_handle:
        names = set(zip_handle.namelist())
        assert "hillslopes.parquet" in names
        assert "README.md" in names
        assert "manifest.json" in names
        assert "profile.yml" not in names
        assert not any(name.endswith(".yml") for name in names)
        manifest = json.loads(zip_handle.read("manifest.json").decode("utf-8"))
        readme_text = zip_handle.read("README.md").decode("utf-8")

    assert manifest["artifact"]["packaged_member_relpaths"] == [
        "README.md",
        "hillslopes.parquet",
        "manifest.json",
    ]
    assert "hillslopes.parquet" in readme_text


def test_execute_features_export_cache_hit_returns_new_job_id_and_source_job_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    miss_result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-source",
    )

    class _UnexpectedWriter:
        def write(self, request):
            raise AssertionError("cache-hit path should not call writer.write")

    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _UnexpectedWriter())

    hit_result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-cache",
    )

    assert hit_result["cache_hit"] is True
    assert hit_result["source_job_id"] == "job-source"
    assert hit_result["artifact_id"] == miss_result["artifact_id"]
    assert (
        hit_result["download_url"]
        == "/rq-engine/api/runs/run-1/cfg/export/features/job/job-cache/download"
    )
    assert hit_result["manifest_relpath"] == "export/features/jobs/job-cache/manifest.json"

    manifest = service.load_job_manifest(tmp_path, "job-cache")
    assert manifest is not None
    assert manifest["cache_hit"] is True
    assert manifest["source_job_id"] == "job-source"
    assert "README.md" in manifest["artifact"]["packaged_member_relpaths"]
    assert "manifest.json" in manifest["artifact"]["packaged_member_relpaths"]


def test_build_export_readme_is_deterministic_and_redacts_absolute_paths() -> None:
    manifest = {
        "artifact_id": "artifact-123",
        "cache_hit": False,
        "generated_at_utc": "2026-03-29T23:10:00Z",
        "source_job_id": None,
        "artifact": {
            "format": "geopackage",
            "artifact_relpath": "features_export.geopackage.zip",
            "packaged_member_relpaths": ["features_export.gpkg", "manifest.json", "README.md"],
        },
        "request": {
            "resolved": {
                "format": "geopackage",
                "units": "si",
                "crs": "wgs",
                "layers": ["watershed.subcatchments"],
                "output_scopes": ["baseline"],
            },
        },
        "crs": {
            "requested_crs": "wgs",
            "resolved_crs": "wgs",
            "resolved_epsg": 4326,
        },
        "layers": [
            {
                "layer_id": "watershed.subcatchments",
                "output_layer_id": "shared__watershed.subcatchments",
                "scope": "shared",
                "context": "base",
                "row_count": 1,
                "feature_count": 1,
                "artifact_relpath": "features_export.gpkg",
            }
        ],
        "columns": {
            "output_layer_metadata": {
                "shared__watershed.subcatchments": {
                    "source_layer_ids": ["watershed.subcatchments"],
                    "selected_columns": ["TopazID"],
                    "unit_mapping": {"TopazID": "non-unitized"},
                    "description_mapping": {"TopazID": "Unique hillslope identifier."},
                }
            }
        },
        "dependency_snapshot": {
            "catalog_signature": "catalog-signature",
            "fingerprint": "dependency-fingerprint",
            "entries": [
                {
                    "dependency_role": "source",
                    "dependency_id": "sbs",
                    "layer_id": "watershed.subcatchments",
                    "output_layer_id": "shared__watershed.subcatchments",
                    "relpath": "/wc1/runs/run-1/private/path.parquet",
                    "exists": True,
                    "size": 101,
                }
            ],
        },
        "warnings": [],
    }

    rendered_a = build_export_readme(manifest=manifest, runid="run-1", config="cfg")
    rendered_b = build_export_readme(manifest=manifest, runid="run-1", config="cfg")

    assert rendered_a == rendered_b
    assert "## Layer inventory" in rendered_a
    assert "| Column | Unit | Description |" in rendered_a
    assert "| TopazID | non-unitized | Unique hillslope identifier. |" in rendered_a
    assert "## Dependency lineage summary" in rendered_a
    assert "[redacted-absolute-path]" in rendered_a
    assert "/wc1/runs/run-1/private/path.parquet" not in rendered_a


def test_execute_features_export_invalid_cached_geopackage_forces_regeneration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    stale_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-stale" / "features_export.gpkg"
    )
    stale_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    stale_artifact_path.write_text('{"format":"geopackage","placeholder":true}', encoding="utf-8")

    stale_cache_entry = {
        "artifact_id": "artifact-stale",
        "artifact_relpath": stale_artifact_path.relative_to(tmp_path).as_posix(),
        "artifact_format": "geopackage",
        "layer_outputs": [],
        "packaged_member_relpaths": [],
        "source_job_id": "job-stale",
        "manifest_relpath": "export/features/jobs/job-stale/manifest.json",
        "warnings": [],
    }
    monkeypatch.setattr(service, "get_cache_index_entry", lambda wd, cache_key: stale_cache_entry)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-new",
    )

    assert result["cache_hit"] is False
    assert result["artifact_id"] != "artifact-stale"


def test_execute_features_export_cached_sqlite_without_gpkg_markers_forces_regeneration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))
    monkeypatch.setattr(service, "_materialize_export_payloads", _stub_materialize_export_payloads)

    stale_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-stale-sqlite" / "features_export.gpkg"
    )
    stale_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(stale_artifact_path) as conn:
        conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY)")
        conn.commit()

    stale_cache_entry = {
        "artifact_id": "artifact-stale-sqlite",
        "artifact_relpath": stale_artifact_path.relative_to(tmp_path).as_posix(),
        "artifact_format": "geopackage",
        "layer_outputs": [],
        "packaged_member_relpaths": [],
        "source_job_id": "job-stale-sqlite",
        "manifest_relpath": "export/features/jobs/job-stale-sqlite/manifest.json",
        "warnings": [],
    }
    monkeypatch.setattr(service, "get_cache_index_entry", lambda wd, cache_key: stale_cache_entry)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-new-sqlite",
    )

    assert result["cache_hit"] is False
    assert result["artifact_id"] != "artifact-stale-sqlite"


def test_execute_features_export_writes_spatial_geopackage_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geometry_path = tmp_path / "dem" / "wbt" / "subcatchments.WGS.geojson"
    geometry_path.parent.mkdir(parents=True, exist_ok=True)
    geometry_path.write_text(
        (
            '{"type":"FeatureCollection","features":['
            '{"type":"Feature","properties":{"TopazID":1,"Name":"A"},'
            '"geometry":{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}},'
            '{"type":"Feature","properties":{"TopazID":2,"Name":"B"},'
            '"geometry":{"type":"Polygon","coordinates":[[[1,1],[2,1],[2,2],[1,2],[1,1]]]}}]}'
        ),
        encoding="utf-8",
    )

    request = NormalizedExportRequest(
        format="geopackage",
        units="si",
        layers=("watershed.subcatchments",),
        crs="wgs",
        output_scopes=("baseline",),
        swat_run_id="none",
    )
    plan = ResolvedExportPlan(
        catalog_version="test-catalog-v1",
        schema_version=1,
        request=request,
        layers=(
            ResolvedLayerPlan(
                layer_id="watershed.subcatchments",
                family="watershed",
                scope_class="scope_invariant",
                scope="shared",
                output_layer_id="shared__watershed.subcatchments",
            ),
        ),
        warnings=(),
    )
    dependency_snapshot = DependencySnapshot(
        catalog_signature="catalog-signature",
        entries=(
            DependencyEntry(
                relpath="dem/wbt/subcatchments.WGS.geojson",
                exists=True,
                size=geometry_path.stat().st_size,
                mtime_ns=geometry_path.stat().st_mtime_ns,
                layer_id="watershed.subcatchments",
                output_layer_id="shared__watershed.subcatchments",
                dependency_role="geometry",
                dependency_id="geometry",
            ),
            DependencyEntry(
                relpath="dem/wbt/subcatchments.WGS.geojson",
                exists=True,
                size=geometry_path.stat().st_size,
                mtime_ns=geometry_path.stat().st_mtime_ns,
                layer_id="watershed.subcatchments",
                output_layer_id="shared__watershed.subcatchments",
                dependency_role="source",
                dependency_id="watershed_subcatchments_geojson",
            ),
        ),
        fingerprint="dependency-fingerprint",
    )
    cache_key_parts = CacheKeyParts(
        request_hash="request-hash",
        dependency_fingerprint=dependency_snapshot.fingerprint,
        cache_key="request-hash+dependency-fingerprint",
    )
    submission = service.FeaturesExportSubmission(
        catalog=load_layer_catalog(),
        plan=plan,
        dependency_snapshot=dependency_snapshot,
        cache_key_parts=cache_key_parts,
        unitizer_preferences_fingerprint=None,
    )

    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)

    result = service.execute_features_export(
        tmp_path,
        runid="run-1",
        config="cfg",
        payload={"format": "geopackage"},
        job_id="job-spatial",
    )

    artifact_path = tmp_path / str(result["artifact_relpath"])
    assert artifact_path.is_file()

    with zipfile.ZipFile(artifact_path, "r") as zip_handle:
        gpkg_member = next(name for name in zip_handle.namelist() if name.endswith(".gpkg"))
        gpkg_bytes = zip_handle.read(gpkg_member)

    extracted_gpkg = tmp_path / "extracted.gpkg"
    extracted_gpkg.write_bytes(gpkg_bytes)

    with sqlite3.connect(extracted_gpkg) as conn:
        content_row = conn.execute(
            "SELECT table_name, data_type FROM gpkg_contents WHERE identifier = ?",
            ("shared__watershed.subcatchments",),
        ).fetchone()

        assert content_row is not None
        table_name, data_type = content_row
        assert data_type == "features"

        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        geom_count = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE geom IS NOT NULL'
        ).fetchone()[0]

    assert row_count == 2
    assert geom_count == 2


def test_publish_profile_artifact_and_resolve_published_artifact_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.geopackage.zip"
    _write_valid_geopackage_zip(artifact_path)
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)

    service.upsert_cache_index_entry(
        tmp_path,
        submission.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )

    entry = service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    assert entry["profile"] == "prep-wepp"
    assert entry["artifact_relpath"] == artifact_relpath
    registry = service.load_publication_registry(tmp_path)
    profiles = registry.get("profiles", {})
    assert isinstance(profiles, dict)
    assert "prep-wepp" in profiles

    resolved_path, resolved_relpath = service.resolve_published_artifact_path(
        tmp_path,
        profile="prep-wepp",
    )
    assert resolved_path == artifact_path
    assert resolved_relpath == artifact_relpath


def test_resolve_published_artifact_path_repairs_registry_from_cache_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.geopackage.zip"
    _write_valid_geopackage_zip(artifact_path)
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    submission_fresh = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission_fresh)
    service.upsert_cache_index_entry(
        tmp_path,
        submission_fresh.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    drift_cache_key = "request-hash-drifted+dependency-fingerprint-drifted"
    service.upsert_cache_index_entry(
        tmp_path,
        drift_cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )

    cache_index_path = tmp_path / "export" / "features" / "cache" / "index.json"
    cache_index = json.loads(cache_index_path.read_text(encoding="utf-8"))
    cache_index["entries"] = {
        drift_cache_key: cache_index["entries"][drift_cache_key],
    }
    cache_index_path.write_text(
        json.dumps(cache_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    resolved_path, resolved_relpath = service.resolve_published_artifact_path(
        tmp_path,
        profile="prep-wepp",
    )
    assert resolved_path == artifact_path
    assert resolved_relpath == artifact_relpath

    registry = service.load_publication_registry(tmp_path)
    profile_entry = registry["profiles"]["prep-wepp"]
    assert profile_entry["cache_key"] == drift_cache_key
    assert profile_entry["request_hash"] == "request-hash-drifted"
    assert profile_entry["dependency_fingerprint"] == "dependency-fingerprint-drifted"


def test_resolve_published_artifact_path_rejects_missing_cache_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_path = tmp_path / "export" / "features" / "artifacts" / "artifact-1" / "features_export.geopackage.zip"
    _write_valid_geopackage_zip(artifact_path)
    artifact_relpath = artifact_path.relative_to(tmp_path).as_posix()

    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    service.upsert_cache_index_entry(
        tmp_path,
        submission.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "artifact_path": str(artifact_path),
            "artifact_paths": [artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-1/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-1",
            "artifact_relpath": artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    cache_index_path = tmp_path / "export" / "features" / "cache" / "index.json"
    cache_index = json.loads(cache_index_path.read_text(encoding="utf-8"))
    cache_index["entries"] = {}
    cache_index_path.write_text(
        json.dumps(cache_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.resolve_published_artifact_path(tmp_path, profile="prep-wepp")

    assert exc.value.status_code == 409
    assert exc.value.code == "stale_publication"


def test_resolve_published_artifact_path_rejects_incompatible_cache_artifact_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gpkg_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gpkg" / "features_export.geopackage.zip"
    )
    _write_valid_geopackage_zip(gpkg_artifact_path)
    gpkg_artifact_relpath = gpkg_artifact_path.relative_to(tmp_path).as_posix()

    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    service.upsert_cache_index_entry(
        tmp_path,
        submission.cache_key_parts.cache_key,
        {
            "artifact_id": "artifact-gpkg",
            "artifact_relpath": gpkg_artifact_relpath,
            "artifact_path": str(gpkg_artifact_path),
            "artifact_paths": [gpkg_artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": ["features_export.gpkg"],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gpkg/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-gpkg",
            "artifact_relpath": gpkg_artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    gdb_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gdb" / "features_export.gdb.zip"
    )
    gdb_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(gdb_artifact_path, "w") as zip_handle:
        zip_handle.writestr("features_export.gdb/table.gdbtable", b"gdb-bytes")
    gdb_artifact_relpath = gdb_artifact_path.relative_to(tmp_path).as_posix()
    gdb_cache_key = "request-hash-gdb+dependency-fingerprint-gdb"
    service.upsert_cache_index_entry(
        tmp_path,
        gdb_cache_key,
        {
            "artifact_id": "artifact-gdb",
            "artifact_relpath": gdb_artifact_relpath,
            "artifact_path": str(gdb_artifact_path),
            "artifact_paths": [gdb_artifact_relpath],
            "artifact_format": "geodatabase",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gdb/manifest.json",
            "warnings": [],
        },
    )

    registry = service.load_publication_registry(tmp_path)
    profile_entry = registry["profiles"]["prep-wepp"]
    profile_entry["artifact_relpath"] = gdb_artifact_relpath
    profile_entry["cache_key"] = gdb_cache_key
    profile_entry["request_hash"] = "request-hash-gdb"
    profile_entry["dependency_fingerprint"] = "dependency-fingerprint-gdb"
    service._write_publication_registry(tmp_path, registry)

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.resolve_published_artifact_path(tmp_path, profile="prep-wepp")

    assert exc.value.status_code == 409
    assert exc.value.code == "stale_publication"


def test_resolve_published_artifact_path_rejects_incompatible_geodatabase_cache_artifact_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_prepare_export_submission(_wd: Path, payload: dict[str, object]) -> service.FeaturesExportSubmission:
        format_token = str(payload.get("format") or "").strip().lower()
        if format_token == "geodatabase":
            return _build_submission(
                cache_key="request-hash-gdb+dependency-fingerprint-gdb",
                format_token="geodatabase",
            )
        return _build_submission(
            cache_key="request-hash-gpkg+dependency-fingerprint-gpkg",
            format_token="geopackage",
        )

    monkeypatch.setattr(service, "prepare_export_submission", _fake_prepare_export_submission)

    gdb_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gdb" / "features_export.gdb.zip"
    )
    gdb_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(gdb_artifact_path, "w") as zip_handle:
        zip_handle.writestr("features_export.gdb/table.gdbtable", b"gdb-bytes")
    gdb_artifact_relpath = gdb_artifact_path.relative_to(tmp_path).as_posix()
    gdb_cache_key = "request-hash-gdb+dependency-fingerprint-gdb"
    service.upsert_cache_index_entry(
        tmp_path,
        gdb_cache_key,
        {
            "artifact_id": "artifact-gdb",
            "artifact_relpath": gdb_artifact_relpath,
            "artifact_path": str(gdb_artifact_path),
            "artifact_paths": [gdb_artifact_relpath],
            "artifact_format": "geodatabase",
            "layer_outputs": [],
            "packaged_member_relpaths": [],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gdb/manifest.json",
            "warnings": [],
        },
    )
    service.publish_profile_artifact(
        tmp_path,
        profile="prep-wepp-geodatabase",
        job_id="job-1",
        job_result={
            "artifact_id": "artifact-gdb",
            "artifact_relpath": gdb_artifact_relpath,
            "manifest_relpath": "export/features/jobs/job-1/manifest.json",
        },
    )

    gpkg_artifact_path = (
        tmp_path / "export" / "features" / "artifacts" / "artifact-gpkg" / "features_export.geopackage.zip"
    )
    _write_valid_geopackage_zip(gpkg_artifact_path)
    gpkg_artifact_relpath = gpkg_artifact_path.relative_to(tmp_path).as_posix()
    gpkg_cache_key = "request-hash-gpkg+dependency-fingerprint-gpkg"
    service.upsert_cache_index_entry(
        tmp_path,
        gpkg_cache_key,
        {
            "artifact_id": "artifact-gpkg",
            "artifact_relpath": gpkg_artifact_relpath,
            "artifact_path": str(gpkg_artifact_path),
            "artifact_paths": [gpkg_artifact_relpath],
            "artifact_format": "geopackage",
            "layer_outputs": [],
            "packaged_member_relpaths": ["features_export.gpkg"],
            "source_job_id": "job-1",
            "manifest_relpath": "export/features/artifacts/artifact-gpkg/manifest.json",
            "warnings": [],
        },
    )

    registry = service.load_publication_registry(tmp_path)
    profile_entry = registry["profiles"]["prep-wepp-geodatabase"]
    profile_entry["artifact_relpath"] = gpkg_artifact_relpath
    profile_entry["cache_key"] = gpkg_cache_key
    profile_entry["request_hash"] = "request-hash-gpkg"
    profile_entry["dependency_fingerprint"] = "dependency-fingerprint-gpkg"
    service._write_publication_registry(tmp_path, registry)

    with pytest.raises(service.FeaturesExportServiceError) as exc:
        service.resolve_published_artifact_path(tmp_path, profile="prep-wepp-geodatabase")

    assert exc.value.status_code == 409
    assert exc.value.code == "stale_publication"


def test_resolve_published_profile_request_supports_cutover_profiles() -> None:
    prep_wepp_profile, prep_wepp_request = service.resolve_published_profile_request("prep-wepp")
    assert prep_wepp_profile == "prep-wepp"
    assert prep_wepp_request["format"] == "geopackage"

    prep_details_profile, prep_details_request = service.resolve_published_profile_request(
        "prep-details"
    )
    assert prep_details_profile == "prep-details"
    assert prep_details_request["format"] == "csv"

    dual_profile, dual_request = service.resolve_published_profile_request("prep-wepp-gpkg-gdb")
    assert dual_profile == "prep-wepp-gpkg-gdb"
    assert dual_request["format"] == "geopackage"

    geodatabase_profile, geodatabase_request = service.resolve_published_profile_request(
        "prep-wepp-geodatabase"
    )
    assert geodatabase_profile == "prep-wepp-geodatabase"
    assert geodatabase_request["format"] == "geodatabase"


def test_companion_rejects_unproven_legacy_source_without_conversion(tmp_path, monkeypatch):
    # Native dual-profile generation and retention are covered in
    # test_features_export_freshness; this old synthetic source has no proof.
    artifact = tmp_path / "export/features/artifacts/legacy/features_export.gpkg"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"legacy-source")
    submission = _build_submission(cache_key="request+dependency", format_token="geopackage")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload, **kwargs: submission)
    monkeypatch.setattr(service, "openfilegdb_create_available", lambda: True)

    def unexpected_conversion(*args, **kwargs):
        pytest.fail("Legacy source without accepted provenance must not be converted")

    monkeypatch.setattr(service, "convert_geopackage_to_openfilegdb", unexpected_conversion)
    with pytest.raises(service.FeaturesExportServiceError) as error:
        service.co_create_post_wepp_geodatabase_artifact(
            tmp_path, source_job_id="legacy", source_job_result={
                "artifact_relpath": artifact.relative_to(tmp_path).as_posix(),
            },
        )
    assert (error.value.status_code, error.value.code) == (409, "changed_source")
    assert artifact.read_bytes() == b"legacy-source"
