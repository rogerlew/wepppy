from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.watershed_bp as watershed_bp_module
from wepppy.weppcloud.utils import helpers as helpers_module

RUN_ID = "terrain-run"
CONFIG = "cfg"

pytestmark = pytest.mark.unit


@pytest.fixture()
def terrain_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    app = Flask("terrain-api-test")
    app.config["TESTING"] = True
    app.register_blueprint(watershed_bp_module.watershed_bp)

    run_root = tmp_path / "runs" / RUN_ID
    run_root.mkdir(parents=True, exist_ok=True)
    dem_path = run_root / "dem" / "dem.tif"
    dem_path.parent.mkdir(parents=True, exist_ok=True)
    dem_path.write_text("dem")

    context = SimpleNamespace(active_root=run_root)

    monkeypatch.setattr(watershed_bp_module, "load_run_context", lambda runid, config: context)
    monkeypatch.setattr(helpers_module, "authorize", lambda runid, config: None)

    class RonStub:
        @classmethod
        def getInstance(cls, wd: str):
            assert wd == str(run_root)
            return SimpleNamespace(dem_fn=str(dem_path))

    class TerrainProcessorStub:
        def __init__(self, *, wbt_wd: str, dem_path: str, config, **kwargs):
            _ = kwargs
            self.wbt_wd = wbt_wd
            self.dem_path = dem_path
            self.config = config

        def run(self):
            workspace = Path(self.wbt_wd)
            viz_dir = workspace / "visualization"
            viz_dir.mkdir(parents=True, exist_ok=True)

            artifact_path = viz_dir / "dem_raw_hillshade.tif"
            artifact_path.write_text("artifact")

            manifest_path = viz_dir / "visualization_manifest.json"
            manifest_payload = {
                "entries": [
                    {
                        "artifact_id": "dem_raw_hillshade",
                        "artifact_type": "hillshade",
                        "source_phase": "phase1_dem_preparation",
                        "path": str(artifact_path),
                        "dependencies": ["dem_raw"],
                        "metadata": {"width": 1, "height": 1},
                    }
                ]
            }
            manifest_path.write_text(json.dumps(manifest_payload))

            ui_payload_path = viz_dir / "visualization_ui_payload.json"
            ui_payload_path.write_text(
                json.dumps(
                    {
                        "workspace": str(workspace),
                        "layer_count": 1,
                        "groups": {"hillshade": ["dem_raw_hillshade"]},
                        "layers": manifest_payload["entries"],
                    }
                )
            )

            return SimpleNamespace(
                executed_phases=(
                    "phase1_dem_preparation",
                    "phase2_conditioning_flow_stack",
                    "phase5_visualization_artifacts",
                ),
                invalidated_phases=(),
                helper_invalidated_phases=(),
                changed_config_keys=(),
                current_dem_path=str(artifact_path),
                artifacts_by_phase={
                    "phase5_visualization_artifacts": {
                        "visualization_manifest_json": str(manifest_path),
                        "visualization_ui_payload_json": str(ui_payload_path),
                        "dem_raw_hillshade": str(artifact_path),
                    }
                },
                visualization_manifest_path=str(manifest_path),
                provenance=({"step": "stub"},),
                basin_summaries=(),
            )

    monkeypatch.setattr(watershed_bp_module, "Ron", RonStub)
    monkeypatch.setattr(watershed_bp_module, "TerrainProcessor", TerrainProcessorStub)

    with app.test_client() as client:
        yield client



def test_query_terrain_processor_config_returns_defaults(terrain_client) -> None:
    response = terrain_client.get(f"/runs/{RUN_ID}/{CONFIG}/query/terrain_processor/config")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["config"]["conditioning"] == "breach"
    assert payload["config"]["visualization_max_pixels"] == 100_000_000



def test_set_terrain_processor_config_persists_payload(terrain_client) -> None:
    response = terrain_client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/set_terrain_processor_config/",
        json={
            "conditioning": "breach_least_cost",
            "blc_dist_m": 300.0,
            "blc_max_cost": 9.5,
            "blc_fill": False,
            "outlet_mode": "multiple",
            "outlets": [[1.0, 2.0], [3.0, 4.0]],
        },
    )

    assert response.status_code == 200
    content = response.get_json()["Content"]
    assert content["config"]["conditioning"] == "breach_least_cost"
    assert content["config"]["blc_fill"] is False
    assert content["config"]["outlet_mode"] == "multiple"

    query = terrain_client.get(f"/runs/{RUN_ID}/{CONFIG}/query/terrain_processor/config")
    payload = query.get_json()
    assert payload["config"]["blc_max_cost"] == pytest.approx(9.5)



def test_run_terrain_processor_exposes_manifest_and_artifact_urls(terrain_client) -> None:
    run_response = terrain_client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/run_terrain_processor/",
        json={"config": {"outlet_mode": "auto"}},
    )

    assert run_response.status_code == 200
    content = run_response.get_json()["Content"]
    manifest_entries = content["visualization_manifest"]["entries"]
    assert len(manifest_entries) == 1

    entry = manifest_entries[0]
    assert entry["relative_path"] == "visualization/dem_raw_hillshade.tif"
    assert entry["url"].endswith("/resources/terrain_processor/visualization/dem_raw_hillshade.tif")

    artifact_response = terrain_client.get(entry["url"])
    assert artifact_response.status_code == 200
    assert artifact_response.data == b"artifact"

    result_query = terrain_client.get(f"/runs/{RUN_ID}/{CONFIG}/query/terrain_processor/last_result")
    result_payload = result_query.get_json()["result"]
    assert result_payload is not None

    manifest_query = terrain_client.get(f"/runs/{RUN_ID}/{CONFIG}/query/terrain_processor/manifest")
    manifest_payload = manifest_query.get_json()
    assert manifest_payload["manifest"]["entries"]
    assert manifest_payload["ui_payload"]["layers"]
