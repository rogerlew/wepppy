from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
geopandas = pytest.importorskip("geopandas")
if getattr(geopandas, "__wepppy_stub__", False):
    pytest.skip("geopandas stubbed", allow_module_level=True)
from rasterio.transform import from_origin

from tests.culverts.test_culverts_runner import (
    _fake_build_raster_mask,
    _init_base_project,
    _make_topo_files,
    _write_culvert_points,
    _write_raster,
    _write_watersheds,
)
import wepppy.nodb.culverts_runner as culverts_runner_module
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Climate, Landuse, Soils, Watershed, Wepp
from wepppy.nodb.core.watershed import NoOutletFoundError
from wepppy.nodb.status_messenger import StatusMessenger
import wepppy.rq.culvert_rq as culvert_rq_module
from wepppy.rq.culvert_rq import run_culvert_run_rq
from wepppy.topo.watershed_collection import WatershedFeature
from wepppy.weppcloud.utils import helpers as wepp_helpers


pytestmark = [pytest.mark.integration, pytest.mark.nodb]


def _write_culvert_points_custom(
    path: Path, point_id: object, coords: tuple[float, float]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:32611"}},
        "features": [
            {
                "type": "Feature",
                "properties": {"Point_ID": point_id},
                "geometry": {"type": "Point", "coordinates": [coords[0], coords[1]]},
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_culvert_batch_orchestration_writes_run_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-20250101"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    _make_topo_files(topo_dir)
    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path, point_ids=[1, 2])
    culvert_points_path = culverts_dir / "culvert_points.geojson"
    _write_culvert_points(culvert_points_path, point_ids=[1, 2])

    # Create dummy landuse and soils rasters (required by _process_culvert_run)
    transform = from_origin(500000.0, 4100000.0, 10.0, 10.0)
    crs = "EPSG:32611"
    dummy_raster = np.ones((3, 3), dtype=np.uint8)
    landuse_dir = batch_root / "landuse"
    soils_dir = batch_root / "soils"
    _write_raster(landuse_dir / "nlcd.tif", dummy_raster, transform, crs)
    _write_raster(soils_dir / "ssurgo.tif", dummy_raster, transform, crs)

    base_runid = "batch;;culvert_base;;_base"
    base_src = tmp_path / "batch" / "culvert_base" / "_base"
    _init_base_project(base_src)

    def _fake_get_wd(runid: str, *args, **kwargs) -> str:
        if runid == base_runid:
            return str(base_src)
        return wepp_helpers.get_wd(runid, *args, **kwargs)

    monkeypatch.setattr(culverts_runner_module, "get_wd", _fake_get_wd)

    metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    model_parameters = {
        "schema_version": "culvert-model-params-v1",
        "base_project_runid": base_runid,
    }
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(model_parameters), encoding="utf-8"
    )

    def _noop(*_args, **_kwargs) -> None:
        return None

    def _landuse_build(self: Landuse, **_kwargs) -> None:
        if Path(self.wd).name == "1":
            raise RuntimeError("landuse fail")
        return None

    monkeypatch.setattr(StatusMessenger, "publish", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(Watershed, "find_outlet", _noop)
    monkeypatch.setattr(Watershed, "build_subcatchments", _noop)
    monkeypatch.setattr(Watershed, "abstract_watershed", _noop)
    monkeypatch.setattr(Landuse, "build", _landuse_build)
    monkeypatch.setattr(Soils, "build", _noop)
    monkeypatch.setattr(Climate, "build", _noop)
    monkeypatch.setattr(Wepp, "clean", _noop)
    monkeypatch.setattr(Wepp, "prep_hillslopes", _noop)
    monkeypatch.setattr(Wepp, "run_hillslopes", _noop)
    monkeypatch.setattr(Wepp, "prep_watershed", _noop)
    monkeypatch.setattr(Wepp, "run_watershed", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_hillslope_interchange", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_totalwatsed3", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_watershed_interchange", _noop)
    monkeypatch.setattr(culvert_rq_module, "activate_query_engine_for_run", _noop)
    monkeypatch.setattr(culvert_rq_module, "_generate_masked_stream_junctions", _noop)

    for run_id in ("1", "2"):
        runid = f"culvert;;{batch_uuid};;{run_id}"
        run_culvert_run_rq(runid, batch_uuid, run_id)
        run_wd = batch_root / "runs" / run_id
        assert (run_wd / "ron.nodb").is_file()

    runid = f"culvert;;{batch_uuid};;2"
    run_culvert_run_rq(runid, batch_uuid, "2")

    culvert_rq_module._final_culvert_batch_complete_rq(batch_uuid)

    run1_metadata = json.loads(
        (batch_root / "runs" / "1" / "run_metadata.json").read_text(encoding="utf-8")
    )
    run2_metadata = json.loads(
        (batch_root / "runs" / "2" / "run_metadata.json").read_text(encoding="utf-8")
    )

    assert run1_metadata["status"] == "failed"
    assert run1_metadata["error"]["type"] == "RuntimeError"
    assert run1_metadata["error"]["message"] == "landuse fail"
    assert run2_metadata["status"] == "success"
    assert "error" not in run2_metadata

    assert run1_metadata["runid"] == f"culvert;;{batch_uuid};;1"
    assert run1_metadata["point_id"] == "1"
    assert run2_metadata["runid"] == f"culvert;;{batch_uuid};;2"
    assert run2_metadata["point_id"] == "2"
    assert run2_metadata["culvert_batch_uuid"] == batch_uuid
    assert run2_metadata["config"] == "culvert.cfg"

    runner = CulvertsRunner.getInstance(str(batch_root))
    assert runner is not None
    assert runner.completed_at is not None
    summary = runner.summary
    assert summary is not None
    assert summary["total"] == 2
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert summary["skipped_no_outlet"] == 0

    manifest_text = (batch_root / "runs_manifest.md").read_text(encoding="utf-8")
    assert "Runs Manifest" in manifest_text
    assert f"culvert;;{batch_uuid};;1" in manifest_text
    assert f"culvert;;{batch_uuid};;2" in manifest_text


def test_culvert_run_outside_watershed_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-outside"
    batch_root = culverts_root / batch_uuid
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path, point_ids=[1])
    culvert_points_path = culverts_dir / "culvert_points.geojson"
    _write_culvert_points_custom(culvert_points_path, 1, (600000.0, 4200000.0))

    metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif", "resolution_m": 10.0},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    model_parameters = {"schema_version": "culvert-model-params-v1"}
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(model_parameters), encoding="utf-8"
    )

    runid = f"culvert;;{batch_uuid};;1"
    run_culvert_run_rq(runid, batch_uuid, "1")

    run_metadata = json.loads(
        (batch_root / "runs" / "1" / "run_metadata.json").read_text(encoding="utf-8")
    )
    assert run_metadata["status"] == "failed"
    assert run_metadata["error"]["type"] == "CulvertPointOutsideWatershedError"


def test_culvert_run_minimum_area_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-min-area"
    batch_root = culverts_root / batch_uuid
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path, point_ids=[1])
    watersheds_payload = json.loads(
        watersheds_path.read_text(encoding="utf-8")
    )
    watersheds_payload["features"][0]["properties"]["area_sqm"] = 1.0
    watersheds_path.write_text(json.dumps(watersheds_payload), encoding="utf-8")

    culvert_points_path = culverts_dir / "culvert_points.geojson"
    _write_culvert_points(culvert_points_path, point_ids=[1])

    metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif", "resolution_m": 10.0},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    model_parameters = {"schema_version": "culvert-model-params-v1"}
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(model_parameters), encoding="utf-8"
    )

    runid = f"culvert;;{batch_uuid};;1"
    run_culvert_run_rq(runid, batch_uuid, "1")

    run_metadata = json.loads(
        (batch_root / "runs" / "1" / "run_metadata.json").read_text(encoding="utf-8")
    )
    assert run_metadata["status"] == "failed"
    assert run_metadata["error"]["type"] == "WatershedAreaBelowMinimumError"


def test_culvert_run_seeds_outlet_on_no_outlet_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    culverts_root = tmp_path / "culverts"
    monkeypatch.setenv("CULVERTS_ROOT", str(culverts_root))

    batch_uuid = "batch-seed"
    batch_root = culverts_root / batch_uuid
    topo_dir = batch_root / "topo"
    culverts_dir = batch_root / "culverts"
    batch_root.mkdir(parents=True)

    _make_topo_files(topo_dir)
    watersheds_path = culverts_dir / "watersheds.geojson"
    _write_watersheds(watersheds_path, point_ids=[1])
    culvert_points_path = culverts_dir / "culvert_points.geojson"
    _write_culvert_points(culvert_points_path, point_ids=[1])

    transform = from_origin(500000.0, 4100000.0, 10.0, 10.0)
    crs = "EPSG:32611"
    dummy_raster = np.ones((3, 3), dtype=np.uint8)
    landuse_dir = batch_root / "landuse"
    soils_dir = batch_root / "soils"
    _write_raster(landuse_dir / "nlcd.tif", dummy_raster, transform, crs)
    _write_raster(soils_dir / "ssurgo.tif", dummy_raster, transform, crs)

    base_runid = "batch;;culvert_base;;_base"
    base_src = tmp_path / "batch" / "culvert_base" / "_base"
    _init_base_project(base_src)

    def _fake_get_wd(runid: str, *args, **kwargs) -> str:
        if runid == base_runid:
            return str(base_src)
        return wepp_helpers.get_wd(runid, *args, **kwargs)

    monkeypatch.setattr(culverts_runner_module, "get_wd", _fake_get_wd)
    monkeypatch.setattr(WatershedFeature, "build_raster_mask", _fake_build_raster_mask)

    metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif", "resolution_m": 10.0},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    model_parameters = {
        "schema_version": "culvert-model-params-v1",
        "base_project_runid": base_runid,
    }
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(model_parameters), encoding="utf-8"
    )

    seeded: dict[str, tuple[int, int]] = {}

    def _fake_extend(_path: Path, candidate: tuple[int, int]) -> bool:
        seeded["candidate"] = candidate
        return True

    def _fake_seed(
        row: int,
        col: int,
        netful_path: Path,
        flovec_path: Path,
    ) -> None:
        seeded["seeded"] = (row, col)

    class _DummyOutlet:
        def __init__(self, pixel_coords: tuple[int, int]) -> None:
            self.pixel_coords = pixel_coords

    class _DummyWbt:
        def __init__(self, wbt_wd: Path) -> None:
            self.netful = str(wbt_wd / "netful.tif")
            self.flovec = str(wbt_wd / "flovec.tif")
            self.chnjnt = str(wbt_wd / "chnjnt.tif")

    def _fake_find_outlet(self: Watershed, watershed_feature=None) -> None:
        if watershed_feature is not None:
            raise NoOutletFoundError(
                "Candidate 0: exited raster at row 1, col 2 without hitting a stream."
            )
        self._outlet = _DummyOutlet((2, 1))

    def _fake_ensure_wbt(self: Watershed) -> _DummyWbt:
        wbt_wd = Path(self.wbt_wd)
        wbt_wd.mkdir(parents=True, exist_ok=True)
        return _DummyWbt(wbt_wd)

    def _noop(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(culvert_rq_module, "_extend_watershed_mask_to_candidate", _fake_extend)
    monkeypatch.setattr(culvert_rq_module, "_seed_outlet_pixel", _fake_seed)
    monkeypatch.setattr(culvert_rq_module, "_generate_masked_stream_junctions", _noop)
    monkeypatch.setattr(culvert_rq_module, "_ensure_outlet_junction", _noop)
    monkeypatch.setattr(StatusMessenger, "publish", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(Watershed, "find_outlet", _fake_find_outlet)
    monkeypatch.setattr(Watershed, "_ensure_wbt", _fake_ensure_wbt)
    monkeypatch.setattr(Watershed, "build_subcatchments", _noop)
    monkeypatch.setattr(Watershed, "abstract_watershed", _noop)
    monkeypatch.setattr(Landuse, "clean", _noop)
    monkeypatch.setattr(Soils, "clean", _noop)
    monkeypatch.setattr(Landuse, "symlink_landuse_map", _noop)
    monkeypatch.setattr(Soils, "symlink_soils_map", _noop)
    monkeypatch.setattr(Landuse, "build", _noop)
    monkeypatch.setattr(Soils, "build", _noop)
    monkeypatch.setattr(Climate, "build", _noop)
    monkeypatch.setattr(Wepp, "clean", _noop)
    monkeypatch.setattr(Wepp, "prep_hillslopes", _noop)
    monkeypatch.setattr(Wepp, "run_hillslopes", _noop)
    monkeypatch.setattr(Wepp, "prep_watershed", _noop)
    monkeypatch.setattr(Wepp, "run_watershed", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_hillslope_interchange", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_totalwatsed3", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_watershed_interchange", _noop)
    monkeypatch.setattr(culvert_rq_module, "activate_query_engine_for_run", _noop)

    runid = f"culvert;;{batch_uuid};;1"
    run_culvert_run_rq(runid, batch_uuid, "1")

    run_metadata = json.loads(
        (batch_root / "runs" / "1" / "run_metadata.json").read_text(encoding="utf-8")
    )
    assert run_metadata["status"] == "success"
    assert seeded["candidate"] == (1, 2)
    assert seeded["seeded"] == (1, 2)
