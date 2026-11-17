from __future__ import annotations

import json
import os
import shutil
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union

import wepppy.nodb.batch_runner as batch_module
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
from wepppy.nodb.core import Ron, Watershed
from tests.microservices.test_vector_upload_exact_converter import (
    assert_feature_equivalence, assert_receipt, exact_converter_environment,
)
from wepppy.nodb.mods.roads.roads import Roads


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
    relative = {
        "roads": "roads/vector_upload_attempts",
        "ag_fields": "ag_fields/vector_upload_attempts",
        "batch_runner": "resources/vector_upload_attempts",
        "omni_run": "_pups/omni/contrasts/vector_upload_attempts",
        "omni_dry_run": "_pups/omni/contrasts/vector_upload_attempts",
    }[workflow]
    attempts = project / relative
    # Receiving routes create the workflow directory before retention admission.
    attempts.parent.mkdir(parents=True, exist_ok=True)
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
    converter_url, fixture_root = exact_converter_environment()
    monkeypatch.setenv("VECTOR_UPLOAD_BINARY_ENABLED", "true")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", os.fspath(tmp_path))
    monkeypatch.setattr(omni_module, "RedisScopeLeaseFactory", lambda: lambda _scope: _Lease())
    return converter_url, fixture_root


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

    assert_receipt(prepared, _source(fixture_root, "line", suffix), canonical)
    baseline = json.loads((fixture_root / "line.geojson").read_text())
    assert_feature_equivalence(json.loads(canonical.read_text()), baseline)
    # Actual projected rasters cover the whole input line with a monotonic plane.
    raster_dir = project / "dem/wbt"
    raster_dir.mkdir(parents=True)
    project_crs = "EPSG:32611"
    transformer = Transformer.from_crs("EPSG:4326", project_crs, always_xy=True)
    points = [transformer.transform(*point) for point in baseline["features"][0]["geometry"]["coordinates"]]
    xs, ys = zip(*points)
    transform = from_bounds(min(xs)-1000, min(ys)-1000, max(xs)+1000, max(ys)+1000, 64, 64)
    relief, netful, subwta = (raster_dir / name for name in ("relief.tif", "netful.tif", "subwta.tif"))
    for path, values, nodata in (
        (relief, np.tile(np.arange(64, dtype="float32"), (64, 1)), -9999),
        (netful, np.full((64, 64), 24, dtype="float32"), 0),
        (subwta, np.full((64, 64), 21, dtype="float32"), 0),
    ):
        with rasterio.open(path, "w", driver="GTiff", width=64, height=64, count=1,
                           dtype="float32", crs=project_crs, transform=transform, nodata=nodata) as dataset:
            dataset.write(values, 1)
    monkeypatch.setattr(Roads, "ron_instance", property(lambda _self: SimpleNamespace(dem_fn=str(relief))))
    monkeypatch.setattr(Roads, "watershed_instance", property(lambda _self: SimpleNamespace(
        delineation_backend_is_wbt=True, relief=str(relief), netful=str(netful), subwta=str(subwta),
    )))
    controller.prepare_segments()
    reloaded = Roads.load_detached(str(project))
    downstream = json.loads(Path(reloaded.roads_monotonic_geojson_path).read_text())
    lowpoints = json.loads(Path(reloaded.roads_low_points_geojson_path).read_text())
    assert downstream["features"]
    for feature in downstream["features"]:
        for key, value in baseline["features"][0]["properties"].items():
            assert feature["properties"][key] == value
        assert feature["properties"]["segment_id"].startswith("roads-seg-")
    combined = unary_union([shape(feature["geometry"]) for feature in downstream["features"]])
    assert combined.hausdorff_distance(shape(baseline["features"][0]["geometry"])) < 1e-8
    assert len(lowpoints["features"]) == len(downstream["features"])
    assert reloaded.query_status()["status"] == "prepared"
    # Compare complete generated geometry and properties with the GeoJSON control.
    reference = project / "reference.geojson"
    roads_module.convert_geojson_file_to_monotonic_segments(
        input_geojson_path=fixture_root / "line.geojson", dem_path=relief,
        output_geojson_path=reference, channel_raster_path=netful, topaz_id_raster_path=subwta,
    )
    assert_feature_equivalence(downstream, json.loads(reference.read_text()))


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
    expected = json.loads((fixture_root / "polygon.geojson").read_text())
    assert table.to_dict(orient="records") == [feature["properties"] for feature in expected["features"]]
    assert_feature_equivalence(json.loads(canonical.read_text()), expected)
    assert_receipt(prepared, _source(fixture_root, "polygon", suffix), canonical)
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
    assert_receipt(prepared, _source(fixture_root, "polygon", suffix), canonical)
    feature = next(iter(reloaded.get_watershed_collection()))
    base = Path(reloaded.base_wd)
    (base / "dem").mkdir(parents=True)
    Ron(str(base), "disturbed9002-wbt-mofe.cfg")
    generated = project / "runs" / feature.runid
    monkeypatch.setattr(batch_module, "get_wd", lambda _runid: str(generated))
    # Skip unrelated simulation stages, while executing the real workspace clone,
    # controller rebinding, watershed selection/save and boundary registration.
    monkeypatch.setattr(BatchRunner, "is_task_enabled", lambda _self, _task: False)
    monkeypatch.setattr(BatchRunner, "_resync_base_project_attributes_owned", lambda *_args: None)
    monkeypatch.setattr(batch_module, "_clear_batch_leaf_nodb_state", lambda *_args: ())
    monkeypatch.setattr(batch_module, "redisprep_snapshot_guard", lambda *_args: nullcontext())
    prep = SimpleNamespace(timestamps_report=lambda: {}, remove_all_timestamp=lambda: None)
    monkeypatch.setattr(batch_module.RedisPrep, "getInstance", lambda *_args: prep)
    for name in ("Watershed", "Landuse", "Soils", "Wepp", "Climate"):
        monkeypatch.setattr(batch_module, name, SimpleNamespace(getInstance=lambda *_args: SimpleNamespace()))
    for name in ("RAP_TS", "OpenET_TS"):
        monkeypatch.setattr(batch_module, name, SimpleNamespace(tryGetInstance=lambda *_args: None))
    reloaded.run_batch_hillslopes(feature)
    target = generated / "dem/target_watershed.geojson"
    expected = json.loads((fixture_root / "polygon.geojson").read_text())
    expected["features"][0]["properties"].update(index=0, runid="fixture")
    assert_feature_equivalence(json.loads(target.read_text()), expected)
    generated_ron = Ron.load_detached(str(generated))
    assert generated_ron._boundary.endswith(f"{feature.runid}/browse/dem/target_watershed.geojson")
    assert generated_ron._boundary_name == "target_watershed"


@pytest.mark.parametrize("suffix", ("geojson", "zip", "parquet", "geoparquet"))
@pytest.mark.parametrize("workflow", ("omni_run", "omni_dry_run"))
def test_final5_omni_detached_reload_and_generated_build_report(
    exact_environment,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
    workflow: str,
) -> None:
    converter_url, fixture_root = exact_environment
    project = tmp_path / f"{workflow}-{suffix}"
    project.mkdir()
    controller = Omni(str(project), "0.cfg")
    prepared = _prepare(
        project=project,
        fixture_root=fixture_root,
        converter_url=converter_url,
        geometry="polygon",
        suffix=suffix,
        workflow=workflow,
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
    assert_receipt(prepared, _source(fixture_root, "polygon", suffix), canonical)
    expected = json.loads((fixture_root / "polygon.geojson").read_text())
    assert_feature_equivalence(json.loads(canonical.read_text()), expected)
    # Detached loading is the readback boundary; rebuild through an attached
    # instance, whose runtime logger is initialized by the normal loader.
    Omni.cleanup_run_instances(str(project))
    reloaded = Omni.getInstance(str(project))
    # Both build entry points read actual polygons and produce the report,
    # contrast sidecar, PSV definition and raster-derived overlay themselves.
    hillslopes = project / "hillslopes.geojson"
    hillslopes.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"TopazID": "21"},
         "geometry": expected["features"][0]["geometry"]},
    ]}))
    raster = project / "subwta.tif"
    with rasterio.open(raster, "w", driver="GTiff", width=10, height=10, count=1,
                       dtype="int32", crs="EPSG:4326", nodata=0,
                       transform=from_bounds(-116, 44, -115.9, 44.1, 10, 10)) as dataset:
        dataset.write(np.full((10, 10), 21, dtype="int32"), 1)
    watershed = SimpleNamespace(
        subwta_utm_shp=str(hillslopes), subwta=str(raster),
        translator_factory=lambda: SimpleNamespace(top2wepp={"21": "1"}),
    )
    monkeypatch.setattr(Watershed, "getInstance", lambda *_args: watershed)
    Ron(str(project), "disturbed9002-wbt-mofe.cfg")
    monkeypatch.setattr(omni_module, "require_feature_allowed", lambda *_args: None)
    pairs = [{"control_scenario": "uniform_low", "contrast_scenario": "mulch"}]
    if workflow == "omni_dry_run":
        report = reloaded.build_contrasts_dry_run_report(None, None, contrast_pairs=pairs)
    else:
        reloaded.build_contrasts(None, None, contrast_pairs=pairs)
        report = OmniContrastStatusReportService().contrast_status_report(reloaded)
    detached = Omni.load_detached(str(project))
    records = [json.loads(line) for line in (project / "_pups/omni/contrasts/build_report.ndjson").read_text().splitlines()]
    assert len(records) == len(expected["features"])
    assert records[0] == {
        "contrast_id": 1, "control_scenario": "uniform_low", "contrast_scenario": "mulch",
        "wepp_id": None, "topaz_id": None, "obj_param": None, "running_obj_param": None,
        "pct_cumulative": None, "selection_mode": "user_defined_areas", "feature_index": 1,
        "area_label": "fixture", "n_hillslopes": 1, "topaz_ids": ["21"], "pair_index": 1,
    }
    assert report == OmniContrastStatusReportService().contrast_status_report(detached)
    assert len(report["items"]) == 1
    assert report["items"][0]["area_label"] == "fixture"
    assert report["items"][0]["n_hillslopes"] == 1
    sidecar = Path(detached._contrast_sidecar_path(1)).read_text().strip().split("\t")
    assert sidecar == ["21", str(project / "_pups/omni/scenarios/mulch/wepp/output/H1")]
    overlay = json.loads(Path(detached._contrast_ids_geojson_path()).read_text())
    assert_receipt(prepared, _source(fixture_root, "polygon", suffix), canonical)
    assert len(overlay["features"]) == 1
    assert shape(overlay["features"][0]["geometry"]).equals(shape(expected["features"][0]["geometry"]))
