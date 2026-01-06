from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.culverts.test_culverts_runner import _make_topo_files, _write_watersheds
from wepppy.nodb.culverts_runner import CulvertsRunner
from wepppy.nodb.core import Climate, Landuse, Soils, Watershed, Wepp
from wepppy.nodb.status_messenger import StatusMessenger
import wepppy.rq.culvert_rq as culvert_rq_module
from wepppy.rq.culvert_rq import run_culvert_batch_rq


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

    metadata = {
        "dem": {"path": "topo/hydro-enforced-dem.tif"},
        "watersheds": {"path": "culverts/watersheds.geojson"},
    }
    model_parameters = {"schema_version": "culvert-model-params-v1"}
    (batch_root / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    (batch_root / "model-parameters.json").write_text(
        json.dumps(model_parameters), encoding="utf-8"
    )

    def _noop(*_args, **_kwargs) -> None:
        return None

    def _landuse_build(self: Landuse) -> None:
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
    monkeypatch.setattr(Wepp, "_check_and_set_baseflow_map", _noop)
    monkeypatch.setattr(Wepp, "_check_and_set_phosphorus_map", _noop)
    monkeypatch.setattr(Wepp, "prep_hillslopes", _noop)
    monkeypatch.setattr(Wepp, "run_hillslopes", _noop)
    monkeypatch.setattr(Wepp, "prep_watershed", _noop)
    monkeypatch.setattr(Wepp, "run_watershed", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_hillslope_interchange", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_totalwatsed3", _noop)
    monkeypatch.setattr(culvert_rq_module, "ensure_watershed_interchange", _noop)
    monkeypatch.setattr(culvert_rq_module, "activate_query_engine_for_run", _noop)

    run_culvert_batch_rq(batch_uuid)

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
