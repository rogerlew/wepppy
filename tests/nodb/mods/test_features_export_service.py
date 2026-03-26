from __future__ import annotations

from pathlib import Path
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
        artifact_path.write_text("features-export", encoding="utf-8")
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
    assert result["download_url"] == "/rq-engine/api/runs/run-1/cfg/export/features/job-source/download"
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
    assert hit_result["download_url"] == "/rq-engine/api/runs/run-1/cfg/export/features/job-cache/download"
    assert hit_result["manifest_relpath"] == "export/features/jobs/job-cache/manifest.json"

    manifest = service.load_job_manifest(tmp_path, "job-cache")
    assert manifest is not None
    assert manifest["cache_hit"] is True
    assert manifest["source_job_id"] == "job-source"

