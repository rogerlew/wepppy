"""Independent service boundary checks on disposable actual export artifacts."""
import json
import os

import pytest

from tests.nodb.mods.test_features_export_freshness import export_source, _execute
from wepppy.nodb.mods.features_export import service


def test_initial_read_denial_has_explicit_service_error(tmp_path, export_source):
    assert os.geteuid() != 0, "Probe requires the ordinary unprivileged service identity"
    payload = {"format": "parquet", "units": "si", "layers": ["test.attributes"]}
    service.prepare_export_submission(tmp_path, payload)
    mode = export_source.stat().st_mode
    export_source.chmod(0)
    try:
        with pytest.raises(service.FeaturesExportServiceError) as failure:
            service.prepare_export_submission(tmp_path, payload)
        assert (failure.value.code, failure.value.status_code) == ("changed_source", 409)
        assert isinstance(failure.value.__cause__, PermissionError)
    finally:
        export_source.chmod(mode)


@pytest.mark.parametrize("change", ["version", "request", "producer_proof"])
def test_companion_rejects_mismatched_producer_before_conversion(tmp_path, export_source, monkeypatch, change):
    source = _execute(tmp_path, "source", "geopackage")
    index = tmp_path / "export/features/cache/index.json"
    before = index.read_bytes()
    if change == "version":
        original = service.build_cache_key

        def changed_version(*args, **kwargs):
            kwargs["export_version_marker"] = "security-review-version-change"
            return original(*args, **kwargs)

        monkeypatch.setattr(service, "build_cache_key", changed_version)
    elif change == "request":
        original = service.resolve_published_profile_request

        def changed_request(*args, **kwargs):
            name, payload = original(*args, **kwargs)
            return name, {**payload, "crs": "utm"}

        monkeypatch.setattr(service, "resolve_published_profile_request", changed_request)
    else:
        manifest_path = (tmp_path / source["artifact_relpath"]).parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        del manifest["dependency_verification"]
        manifest_path.write_text(json.dumps(manifest))

    def unexpected_conversion(*args, **kwargs):
        pytest.fail("Conversion ran despite mismatched producer evidence")

    monkeypatch.setattr(service, "convert_geopackage_to_openfilegdb", unexpected_conversion)
    with pytest.raises(service.FeaturesExportServiceError) as failure:
        service.co_create_post_wepp_geodatabase_artifact(
            tmp_path, source_job_id="source", source_job_result=source,
        )
    assert (failure.value.code, failure.value.status_code) == ("changed_source", 409)
    assert index.read_bytes() == before
    assert len(list((tmp_path / "export/features/artifacts").iterdir())) == 1


def test_historical_publication_survives_missing_current_inputs(tmp_path, export_source):
    source = _execute(tmp_path, "source", "geopackage")
    archive = tmp_path / source["artifact_relpath"]
    before = archive.read_bytes()
    export_source.unlink()
    (tmp_path / "geometry.geojson").unlink()
    published = service.publish_profile_artifact(
        tmp_path, profile="prep-wepp", job_id="source", job_result=source,
    )
    resolved, _ = service.resolve_published_artifact_path(tmp_path, profile="prep-wepp")
    assert resolved == archive
    assert archive.read_bytes() == before
    assert published["artifact_relpath"] == source["artifact_relpath"]
