"""Real catalog, materialization, native writers, manifests and cache identities."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from tests.nodb.mods.test_features_export_dependency_tracker import _catalog_with_attr_source
from wepppy.nodb.mods.features_export import service

pytestmark = pytest.mark.unit


@pytest.fixture
def export_source(tmp_path, monkeypatch):
    catalog = _catalog_with_attr_source(
        layer_id="test.attributes", geometry_locator={"kind": "relpath", "value": "geometry.geojson"},
    )
    (tmp_path / "geometry.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"id": 1},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
    }]}))
    source = tmp_path / "attrs.parquet"
    pd.DataFrame({"id": [1], "value": [25.0]}).to_parquet(source, index=False)
    monkeypatch.setattr(service, "load_layer_catalog", lambda: catalog)
    original_profile = service.resolve_published_profile_request

    def profile(name, **kwargs):
        canonical, payload = original_profile(name, **kwargs)
        return canonical, {"format": payload["format"], "units": "si", "layers": ["test.attributes"]}

    monkeypatch.setattr(service, "resolve_published_profile_request", profile)
    return source


def _execute(root, job, format_token="parquet"):
    return service.execute_features_export(
        root, runid="freshness", config="test", job_id=job,
        payload={"format": format_token, "units": "si", "layers": ["test.attributes"]},
    )


def _rewrite(path, value):
    before = path.stat()
    pd.DataFrame({"id": [1], "value": [float(value)]}).to_parquet(path, index=False)
    assert path.stat().st_size == before.st_size
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))


def test_real_export_changed_bytes_and_metadata_only_reuse(tmp_path, export_source):
    first = _execute(tmp_path, "first")
    archive = tmp_path / first["artifact_relpath"]
    original_bytes = archive.read_bytes()
    stat = export_source.stat()
    os.utime(export_source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    touched = _execute(tmp_path, "touched")
    assert touched["cache_hit"] is True
    assert archive.read_bytes() == original_bytes
    _rewrite(export_source, 75)
    changed = _execute(tmp_path, "changed")
    assert changed["cache_hit"] is False
    with ZipFile(tmp_path / changed["artifact_relpath"]) as zipped:
        member = next(name for name in zipped.namelist() if name.endswith(".parquet"))
        assert pd.read_parquet(io.BytesIO(zipped.read(member)))["value"].tolist() == [75.0]
        manifest = json.loads(zipped.read("manifest.json"))
    assert manifest["dependency_verification"]["status"] == "verified"
    assert manifest == service.load_job_manifest(tmp_path, "changed")
    assert json.loads((archive.parent / "manifest.json").read_text())["dependency_verification"]["status"] == "verified"


@pytest.mark.parametrize("failure", ["change", "read_error"])
def test_materialization_conflict_retains_candidate_and_prior_binding(tmp_path, export_source, monkeypatch, failure):
    first = _execute(tmp_path, "first")
    prior = (tmp_path / first["artifact_relpath"]).read_bytes()
    index = tmp_path / "export/features/cache/index.json"
    _rewrite(export_source, 45)
    index_before = index.read_bytes()
    original = service._materialize_export_payloads

    def materialize(*args, **kwargs):
        result = original(*args, **kwargs)
        if failure == "change":
            _rewrite(export_source, 75)
        else:
            from wepppy.nodb.mods.features_export import dependency_tracker
            def read_error(path):
                raise PermissionError("injected final dependency read denial")
            monkeypatch.setattr(dependency_tracker, "_hash_file_sha256", read_error)
        return result

    monkeypatch.setattr(service, "_materialize_export_payloads", materialize)
    with pytest.raises(service.FeaturesExportServiceError) as error:
        _execute(tmp_path, "failed")
    assert (error.value.status_code, error.value.code) == (409, "changed_source")
    assert index.read_bytes() == index_before
    assert (tmp_path / first["artifact_relpath"]).read_bytes() == prior
    manifest = service.load_job_manifest(tmp_path, "failed")
    assert manifest["dependency_verification"]["status"] == ("rejected" if failure == "change" else "error")
    candidate = tmp_path / "export/features/artifacts" / manifest["artifact_id"]
    assert json.loads((candidate / "manifest.json").read_text()) == manifest
    assert list(candidate.rglob("*.parquet"))


def test_companion_native_success_stale_rejection_and_historical_publication(tmp_path, export_source):
    from osgeo import ogr
    original = _execute(tmp_path, "original", "geopackage")
    companion = service.co_create_post_wepp_geodatabase_artifact(
        tmp_path, source_job_id="original", source_job_result=original,
    )
    archive = tmp_path / companion["artifact_relpath"]
    prior = archive.read_bytes()
    with ZipFile(archive) as zipped:
        assert "README.md" in zipped.namelist()
        manifest = json.loads(zipped.read("manifest.json"))
        gdb = next(name.split("/", 1)[0] for name in zipped.namelist() if ".gdb/" in name)
    assert manifest["dependency_verification"]["status"] == "verified"
    assert manifest == json.loads((tmp_path / companion["manifest_relpath"]).read_text())
    dataset = ogr.Open(f"/vsizip/{archive}/{gdb}")
    assert dict(next(iter(dataset.GetLayer(0))).items())["value"] == 25.0
    hit = _execute(tmp_path, "companion-hit", "geodatabase")
    assert hit["cache_hit"] is True
    assert hit["artifact_relpath"] == companion["artifact_relpath"]
    entries = service.load_cache_index(tmp_path)["entries"].values()
    companion_entry = next(entry for entry in entries if entry["artifact_relpath"] == companion["artifact_relpath"])
    assert all(layer["format"] == "geodatabase" for layer in companion_entry["layer_outputs"])
    assert all(layer["artifact_relpath"] == "features_export.gdb" for layer in service.load_job_manifest(tmp_path, "companion-hit")["layers"])
    index = tmp_path / "export/features/cache/index.json"
    before_index = index.read_bytes()
    _rewrite(export_source, 75)
    with pytest.raises(service.FeaturesExportServiceError, match="inputs changed"):
        service.co_create_post_wepp_geodatabase_artifact(tmp_path, source_job_id="original", source_job_result=original)
    assert index.read_bytes() == before_index
    assert archive.read_bytes() == prior
    published = service.publish_profile_artifact(tmp_path, profile="prep-wepp-geodatabase", job_id="original", job_result=companion)
    assert published["dependency_fingerprint"] == manifest["dependency_snapshot"]["fingerprint"]
    assert service.resolve_published_artifact_path(tmp_path, profile="prep-wepp-geodatabase")[0] == archive
    current = _execute(tmp_path, "current", "geodatabase")
    assert current["cache_hit"] is False


@pytest.mark.parametrize("failure", ["change", "disk_full"])
def test_companion_retry_keeps_accepted_artifacts_and_publications(tmp_path, export_source, monkeypatch, failure):
    original = _execute(tmp_path, "original", "geopackage")
    entries = service.publish_profile_execution_artifacts(
        tmp_path, requested_profile="prep-wepp-gpkg-gdb", job_id="original", job_result=original,
    )
    retained = [tmp_path / entry["artifact_relpath"] for entry in entries.values()]
    retained += [tmp_path / "export/features/cache/index.json", tmp_path / "export/features/published/index.json",
                 (tmp_path / original["artifact_relpath"]).parent / "manifest.json"]
    before = {path: path.read_bytes() for path in retained}
    convert = service.convert_geopackage_to_openfilegdb

    def conversion(*args, **kwargs):
        result = convert(*args, **kwargs)
        if failure == "disk_full":
            raise OSError(28, "injected ENOSPC after native conversion")
        _rewrite(export_source, 75)
        return result

    monkeypatch.setattr(service, "convert_geopackage_to_openfilegdb", conversion)
    with pytest.raises((OSError, service.FeaturesExportServiceError)):
        service.publish_profile_execution_artifacts(
            tmp_path, requested_profile="prep-wepp-gpkg-gdb", job_id="original", job_result=original,
        )
    assert {path: path.read_bytes() for path in retained} == before
    candidates = [json.loads(path.read_text()) for path in (tmp_path / "export/features/artifacts").glob("*/manifest.json")]
    assert any(item.get("dependency_verification", {}).get("status") in {"error", "rejected"} for item in candidates)


def test_native_packaging_failure_retains_gdb_and_partial_zip(tmp_path, export_source, monkeypatch):
    from wepppy.nodb.mods.features_export.exporters import geodatabase
    from wepppy.nodb.mods.features_export.exporters import FeaturesExportWriterError
    original = _execute(tmp_path, "original", "geopackage")
    before = (tmp_path / "export/features/cache/index.json").read_bytes()
    captured = {}

    def fail_packaging(base_name, format, **kwargs):
        target = Path(base_name)
        captured.update({path: path.read_bytes() for path in target.rglob("*") if path.is_file()})
        assert captured  # actual ogr2ogr output, not a fake conversion
        target.with_suffix(".gdb.zip").write_bytes(b"partial archive")
        raise OSError(28, "injected native packaging ENOSPC")

    monkeypatch.setattr(geodatabase.shutil, "make_archive", fail_packaging)
    with pytest.raises(FeaturesExportWriterError, match="Failed to package"):
        service.co_create_post_wepp_geodatabase_artifact(tmp_path, source_job_id="original", source_job_result=original)
    assert {path: path.read_bytes() for path in captured} == captured
    assert (tmp_path / "export/features/cache/index.json").read_bytes() == before
    directory = next(iter(captured)).parent.parent
    assert (directory / "features_export.gdb.zip").read_bytes() == b"partial archive"
    assert json.loads((directory / "manifest.json").read_text())["dependency_verification"]["status"] == "error"


def test_companion_rejects_request_version_change_with_identical_inputs(tmp_path, export_source, monkeypatch):
    original = _execute(tmp_path, "original", "geopackage")
    index = tmp_path / "export/features/cache/index.json"
    before = index.read_bytes()
    build_key = service.build_cache_key

    def changed_version(*args, **kwargs):
        return build_key(*args, **{**kwargs, "export_version_marker": "next-export-version"})

    monkeypatch.setattr(service, "build_cache_key", changed_version)
    with pytest.raises(service.FeaturesExportServiceError) as error:
        service.co_create_post_wepp_geodatabase_artifact(tmp_path, source_job_id="original", source_job_result=original)
    assert error.value.code == "changed_source"
    assert index.read_bytes() == before
    assert len(list((tmp_path / "export/features/artifacts").iterdir())) == 1


def test_initial_digest_read_error_has_no_metadata_fallback(tmp_path, export_source, monkeypatch):
    from wepppy.nodb.mods.features_export import dependency_tracker

    def denied(path):
        raise PermissionError("dependency access denied")

    monkeypatch.setattr(dependency_tracker, "_hash_file_sha256", denied)
    with pytest.raises(service.FeaturesExportServiceError) as error:
        _execute(tmp_path, "denied")
    assert error.value.code == "changed_source"
    assert isinstance(error.value.__cause__, PermissionError)
    assert not (tmp_path / "export/features/cache/index.json").exists()


def test_historical_publication_and_download_survive_missing_source(tmp_path, export_source):
    original = _execute(tmp_path, "original", "geopackage")
    export_source.unlink()
    published = service.publish_profile_artifact(tmp_path, profile="prep-wepp", job_id="original", job_result=original)
    path, relpath = service.resolve_published_artifact_path(tmp_path, profile="prep-wepp")
    assert path.is_file() and relpath == original["artifact_relpath"] == published["artifact_relpath"]
    assert service.resolve_download_artifact_path(tmp_path, job_id="original", job_result=original)[0] == path
