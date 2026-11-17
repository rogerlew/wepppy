from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import wepppy.nodb.mods.roads.roads as roads_module
import wepppy.nodb.mods.omni.omni as omni_module
from wepppy.microservices.vector_upload_normalization import (
    RetentionActor,
    prepare_vector_upload,
    validate_feature_collection_geometries,
)
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.mods.ag_fields import AgFields
from wepppy.nodb.mods.omni.omni import Omni
from wepppy.nodb.mods.omni.omni_contrast_status_report_service import (
    OmniContrastStatusReportService,
)
from wepppy.nodb.mods.omni.omni_contrast_build_service import OmniContrastBuildService
from wepppy.nodb.mods.roads.monotonic_segments import MonotonicConversionSummary
from wepppy.nodb.mods.roads.roads import Roads
from wepppy.topo.watershed_collection.watershed_collection import WatershedCollection


pytestmark = pytest.mark.integration


class _Reservation:
    reservation_id = "exact-downstream"

    def bind_attempt(self, _attempt_dir: Path) -> None:
        return None

    def commit(self, _exact_bytes: int) -> None:
        return None

    def release_prewrite(self) -> None:
        return None


class _Ledger:
    def reserve(self, **_kwargs):
        return _Reservation()


class _Lease:
    def assert_owned(self) -> None:
        return None

    def release(self) -> None:
        return None


def _source(fixture_root: Path, geometry: str, suffix: str) -> Path:
    fixture_suffix = "parquet" if suffix in {"parquet", "geoparquet"} else suffix
    return fixture_root / f"{geometry}.{fixture_suffix}"


def _prepare(
    *,
    project: Path,
    fixture_root: Path,
    converter_url: str,
    geometry: str,
    suffix: str,
    workflow: str,
    allowed: tuple[str, ...],
):
    attempts = project / "vector_upload_attempts"
    source = _source(fixture_root, geometry, suffix)
    with source.open("rb") as stream:
        return prepare_vector_upload(
            raw_filename=f"{geometry}.{suffix}",
            stream=stream,
            endpoint_max_bytes=10 * 1024 * 1024,
            attempt_root=attempts,
            evidence_roots=(attempts,),
            filesystem_root=project,
            project_key=f"exact-downstream:{workflow}:{suffix}",
            workflow=workflow,
            project_identity="exact-downstream",
            actor=RetentionActor("human", 1),
            validator=lambda _path, payload: validate_feature_collection_geometries(payload, allowed),
            converter_url=converter_url,
            ledger=_Ledger(),
            scope_lease_factory=lambda _key: _Lease(),
        )


@pytest.fixture()
def exact_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    converter_url = os.getenv("VECTOR_UPLOAD_INTEGRATION_URL")
    fixture_root_value = os.getenv("VECTOR_UPLOAD_INTEGRATION_FIXTURES")
    if not converter_url or not fixture_root_value:
        pytest.skip("exact converter integration environment is not configured")
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    monkeypatch.setattr(omni_module, "RedisScopeLeaseFactory", lambda: lambda _scope: _Lease())
    return converter_url, Path(fixture_root_value)


@pytest.mark.parametrize("suffix", ("geojson", "zip", "parquet", "geoparquet"))
def test_final5_roads_detached_reload_and_monotonic_artifact(
    exact_environment,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    converter_url, fixture_root = exact_environment
    project = tmp_path / f"roads-{suffix}"
    project.mkdir()
    controller = Roads(str(project), "disturbed9002-wbt-mofe.cfg")
    with controller.locked():
        controller._enabled = True
    prepared = _prepare(
        project=project,
        fixture_root=fixture_root,
        converter_url=converter_url,
        geometry="line",
        suffix=suffix,
        workflow="roads",
        allowed=("LineString", "MultiLineString"),
    )
    canonical = Path(controller.roads_upload_dir) / "roads.uploaded.geojson"
    prepared.publish_transactional(
        mutation=lambda candidate, commit: controller.set_uploaded_geojson(
            str(candidate), publication_commit=commit
        ),
        canonical_path=canonical,
        canonical_relative_path="roads/roads.uploaded.geojson",
    )

    relief = project / "dem/wbt/relief.tif"
    netful = project / "dem/wbt/netful.tif"
    subwta = project / "dem/wbt/subwta.tif"
    relief.parent.mkdir(parents=True, exist_ok=True)
    for path in (relief, netful, subwta):
        path.write_text(path.stem, encoding="ascii")
    monkeypatch.setattr(Roads, "ron_instance", property(lambda _self: SimpleNamespace(dem_fn=str(project / "dem/dem.vrt"))))
    monkeypatch.setattr(
        Roads,
        "watershed_instance",
        property(lambda _self: SimpleNamespace(
            delineation_backend_is_wbt=True,
            relief=str(relief),
            netful=str(netful),
            subwta=str(subwta),
        )),
    )

    def convert(**kwargs):
        output = Path(kwargs["output_geojson_path"])
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = json.loads(canonical.read_text(encoding="utf-8"))
        payload["features"][0]["properties"].update({
            "segment_id": "roads-seg-000001",
            "DESIGN": "Inslope_bd",
            "topaz_id_chn_lowpoint": 24,
            "topaz_id_hill_lowpoint": 21,
            "_roads_routing_eligibility": "channel_associated",
            "_roads_non_channel_routable": False,
        })
        output.write_text(json.dumps(payload), encoding="utf-8")
        Path(kwargs["low_points_output_geojson_path"]).write_text(
            '{"type":"FeatureCollection","features":[]}', encoding="ascii"
        )
        return MonotonicConversionSummary(1, 1, 0, 1, 1.0, 0.5)

    monkeypatch.setattr(roads_module, "convert_geojson_file_to_monotonic_segments", convert)
    controller.prepare_segments()
    reloaded = Roads.load_detached(str(project))
    downstream = json.loads(Path(reloaded.roads_monotonic_geojson_path).read_text())
    assert downstream["features"][0]["properties"]["segment_id"] == "roads-seg-000001"
    assert reloaded.query_status()["status"] == "prepared"


@pytest.mark.parametrize("suffix", ("geojson", "zip", "parquet", "geoparquet"))
def test_final5_agfields_detached_reload_and_rotation_parquet(
    exact_environment,
    tmp_path: Path,
    suffix: str,
) -> None:
    converter_url, fixture_root = exact_environment
    project = tmp_path / f"ag-fields-{suffix}"
    project.mkdir()
    controller = AgFields(str(project), "disturbed9002-wbt-mofe.cfg")
    prepared = _prepare(
        project=project,
        fixture_root=fixture_root,
        converter_url=converter_url,
        geometry="polygon",
        suffix=suffix,
        workflow="ag_fields",
        allowed=("Polygon", "MultiPolygon"),
    )
    canonical = Path(controller.ag_fields_dir) / "fields.WGS.geojson"
    prepared.publish_transactional(
        mutation=lambda candidate, commit: controller.validate_field_boundary_geojson(
            candidate,
            source_filename=f"fields.{suffix}",
            publication_commit=commit,
        ),
        canonical_path=canonical,
        canonical_relative_path="ag_fields/fields.WGS.geojson",
    )
    reloaded = AgFields.load_detached(str(project))
    table = pd.read_parquet(reloaded.rotation_schedule_parquet)
    assert table["field_id"].tolist() == [1]
    assert reloaded.field_boundaries_source_filename == f"fields.{suffix}"


@pytest.mark.parametrize("suffix", ("geojson", "zip", "parquet", "geoparquet"))
def test_final5_batch_detached_reload_and_target_watershed(
    exact_environment,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    converter_url, fixture_root = exact_environment
    project = tmp_path / f"batch-{suffix}"
    project.mkdir()
    monkeypatch.setattr(BatchRunner, "_init_base_project", lambda _self: None)
    controller = BatchRunner(str(project), "batch/default_batch.cfg", "dummy_base.cfg")
    controller.runid_template_state = {
        "template": "{properties['label']}",
        "status": "valid",
        "summary": {"is_valid": True},
    }
    prepared = _prepare(
        project=project,
        fixture_root=fixture_root,
        converter_url=converter_url,
        geometry="polygon",
        suffix=suffix,
        workflow="batch_runner",
        allowed=("Polygon", "MultiPolygon"),
    )
    canonical = Path(controller.resources_dir) / "watershed.geojson"

    def publish(candidate: Path, commit) -> None:
        controller.publish_geojson_transactional(
            candidate,
            canonical,
            publication_commit=commit,
        )

    prepared.publish_transactional(
        mutation=publish,
        canonical_path=canonical,
        canonical_relative_path="resources/watershed.geojson",
    )
    reloaded = BatchRunner.load_detached(str(project))
    feature = next(iter(reloaded.get_watershed_collection()))
    target = project / "dem/target_watershed.geojson"
    target.parent.mkdir(parents=True)
    feature.save_geojson(str(target))
    payload = json.loads(target.read_text())
    assert payload["features"][0]["properties"]["field_id"] == 1


@pytest.mark.parametrize("suffix", ("geojson", "zip", "parquet", "geoparquet"))
def test_final5_omni_detached_reload_and_dry_run_status_report(
    exact_environment,
    tmp_path: Path,
    suffix: str,
) -> None:
    converter_url, fixture_root = exact_environment
    project = tmp_path / f"omni-{suffix}"
    project.mkdir()
    controller = Omni(str(project), "0.cfg")
    prepared = _prepare(
        project=project,
        fixture_root=fixture_root,
        converter_url=converter_url,
        geometry="polygon",
        suffix=suffix,
        workflow="omni_dry_run",
        allowed=("Polygon", "MultiPolygon"),
    )
    canonical = project / "_pups/omni/contrasts/_uploads/exact/areas.geojson"

    def publish(candidate: Path) -> None:
        canonical.parent.mkdir(parents=True)
        shutil.copy2(candidate, canonical)
        OmniContrastBuildService.prevalidate_user_defined_geojson(str(canonical))
        controller.parse_inputs({
            "omni_contrast_selection_mode": "user_defined_areas",
            "omni_contrast_geojson_path": str(canonical),
            "omni_contrast_geojson_name_key": "label",
        })

    prepared.publish(
        mutation=publish,
        canonical_path=canonical,
        canonical_relative_path="_pups/omni/contrasts/_uploads/exact/areas.geojson",
    )
    reloaded = Omni.load_detached(str(project))
    assert Path(reloaded._contrast_geojson_path).read_bytes() == canonical.read_bytes()
    report = OmniContrastStatusReportService().contrast_status_report(reloaded)
    assert report == {"selection_mode": "user_defined_areas", "items": []}
