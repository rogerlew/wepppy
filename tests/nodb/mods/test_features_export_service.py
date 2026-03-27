from __future__ import annotations

from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.cache_key import CacheKeyParts
from wepppy.nodb.mods.features_export.contracts import (
    NormalizedExportRequest,
    ResolvedExportPlan,
    ResolvedLayerPlan,
)
from wepppy.nodb.mods.features_export.dependency_tracker import DependencySnapshot
from wepppy.nodb.mods.features_export.exporters import (
    ExportArtifactMetadata,
    ExportedLayerArtifact,
)

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


def _build_submission(cache_key: str) -> service.FeaturesExportSubmission:
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


def test_execute_features_export_cache_miss_result_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))

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
        == f"/weppcloud/runs/run-1/cfg/download/export/features/artifacts/{result['artifact_id']}/features_export.gpkg"
    )
    assert result["manifest_relpath"] == "export/features/jobs/job-source/manifest.json"
    assert isinstance(result["warnings"], list)
    assert (tmp_path / str(result["artifact_relpath"])).is_file()
    assert (tmp_path / result["manifest_relpath"]).is_file()

    cache_entry = service.get_cache_index_entry(tmp_path, submission.cache_key_parts.cache_key)
    assert cache_entry is not None
    assert cache_entry["source_job_id"] == "job-source"


def test_execute_features_export_cache_hit_returns_new_job_id_and_source_job_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITE_PREFIX", "/weppcloud")
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))

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
        == f"/weppcloud/runs/run-1/cfg/download/{miss_result['artifact_relpath']}"
    )
    assert hit_result["manifest_relpath"] == "export/features/jobs/job-cache/manifest.json"

    manifest = service.load_job_manifest(tmp_path, "job-cache")
    assert manifest is not None
    assert manifest["cache_hit"] is True
    assert manifest["source_job_id"] == "job-source"


def test_prepare_export_submission_passes_nodb_ref_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    fake_catalog = SimpleNamespace()
    captured: dict[str, object] = {}

    monkeypatch.setattr(service, "load_layer_catalog", lambda: fake_catalog)
    monkeypatch.setattr(service, "resolve_export_plan", lambda payload, catalog: plan)
    monkeypatch.setattr(service, "_resolve_plan_swat_run_id", lambda resolved_plan, wd_path: resolved_plan)

    def _fake_build_dependency_snapshot(plan_arg, catalog_arg, wd_path_arg, **kwargs):
        captured["plan"] = plan_arg
        captured["catalog"] = catalog_arg
        captured["wd_path"] = wd_path_arg
        captured["resolver"] = kwargs.get("nodb_ref_resolver")
        return DependencySnapshot(
            catalog_signature="catalog-signature",
            entries=(),
            fingerprint="dependency-fingerprint",
        )

    monkeypatch.setattr(service, "build_dependency_snapshot", _fake_build_dependency_snapshot)
    monkeypatch.setattr(
        service,
        "build_cache_key",
        lambda *args, **kwargs: CacheKeyParts(
            request_hash="request-hash",
            dependency_fingerprint="dependency-fingerprint",
            cache_key="request-hash+dependency-fingerprint",
        ),
    )
    monkeypatch.setattr(
        service,
        "Watershed",
        SimpleNamespace(
            getInstance=lambda wd: SimpleNamespace(subwta_shp="watershed/subwta.shp"),
        ),
    )

    submission = service.prepare_export_submission(tmp_path, {"format": "geopackage"})

    assert submission.plan is plan
    assert captured["plan"] is plan
    assert captured["catalog"] is fake_catalog
    resolver = captured["resolver"]
    assert callable(resolver)
    assert resolver(str(tmp_path), "watershed", "subwta_shp") == "watershed/subwta.shp"


def test_nodb_ref_resolver_rejects_unsupported_controller(tmp_path: Path) -> None:
    with pytest.raises(service.FeaturesExportServiceError, match="Unsupported nodb_ref controller"):
        service._resolve_nodb_ref_relpath(str(tmp_path), "landuse", "landuse_shp")


def test_execute_features_export_invalid_cached_geopackage_forces_regeneration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submission = _build_submission(cache_key="request-hash+dependency-fingerprint")
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))

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
    monkeypatch.setattr(service, "prepare_export_submission", lambda wd, payload: submission)
    monkeypatch.setattr(service, "get_export_writer", lambda fmt: _DummyWriter(tmp_path))

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
