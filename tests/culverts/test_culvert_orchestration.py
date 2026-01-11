from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import from_origin

from tests.culverts.test_culverts_runner import (
    _init_base_project,
    _make_topo_files,
    _write_culvert_points,
    _write_raster,
    _write_watersheds,
)
import wepppy.nodb.culverts_runner as culverts_runner_module
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Climate, Landuse, Soils, Watershed, Wepp
from wepppy.nodb.status_messenger import StatusMessenger
import wepppy.rq.culvert_rq as culvert_rq_module
from wepppy.rq.culvert_rq import run_culvert_run_rq
from wepppy.weppcloud.utils import helpers as wepp_helpers


pytestmark = [pytest.mark.integration, pytest.mark.nodb]


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
