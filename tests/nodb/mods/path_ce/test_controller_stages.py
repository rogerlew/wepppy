"""Real-controller orchestration tests on fixture run artifacts.

Builds PathCostEffective via the __new__ harness (no NoDbBase/Redis init),
assembles a run directory from the austere-inaction fixtures, and exercises
the actual stage pipeline: validate → prepare_data → solve → run_sweep →
results, plus the failure and cache policies.
"""

from __future__ import annotations

import json
import logging
import shutil
from contextlib import nullcontext
from pathlib import Path

import pytest

pytest.importorskip("pulp")
pd = pytest.importorskip("pandas")

from wepppy.nodb.mods.path_ce.path_ce_solver import PathCESolverError
from wepppy.nodb.mods.path_ce.path_cost_effective import (
    PathCostEffective,
    _normalize_config,
)
from wepppy.nodb.mods.path_ce.preconditions import PathCEPreconditionError
from wepppy.nodb.mods.path_ce.presets import default_treatments

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "path_ce"

pytestmark = pytest.mark.unit


def _assemble_run_dir(tmp_path: Path) -> Path:
    src = FIXTURES / "austere_inaction"
    wd = tmp_path / "run"
    (wd / "omni").mkdir(parents=True)
    (wd / "watershed").mkdir()
    for name in (
        "scenarios.hillslope_summaries.parquet",
        "contrasts.out.parquet",
        "scenarios.out.parquet",
        "contrast_id_definitions.psv",
    ):
        shutil.copy(src / name, wd / "omni" / name)
    shutil.copy(src / "hillslopes.parquet", wd / "watershed" / "hillslopes.parquet")
    geo = wd / "dem" / "wbt"
    geo.mkdir(parents=True)
    (geo / "subcatchments.WGS.geojson").write_text("{}")
    (geo / "channels.WGS.geojson").write_text("{}")
    return wd


def _build_controller(wd: Path, config: dict | None = None) -> PathCostEffective:
    controller = PathCostEffective.__new__(PathCostEffective)
    controller.wd = str(wd)
    controller.logger = logging.getLogger("tests.nodb.path_ce.controller_stages")
    path_dir = wd / "path"
    path_dir.mkdir(parents=True, exist_ok=True)
    controller._path_dir = str(path_dir)
    controller._config = _normalize_config(
        config
        or {"sdyd_threshold": 15.0, "sddc_threshold": 48.2}
    )
    controller._results = {}
    controller._status = "idle"
    controller._status_message = ""
    controller._progress = 0.0
    controller.locked = lambda: nullcontext()
    return controller


@pytest.fixture(autouse=True)
def _stub_render_report(monkeypatch):
    """Rendering is unconditional; stub the Quarto stage for unit tests.

    The render-specific tests below override this with their own doubles."""
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.render_report",
        lambda wd, config, artifacts, subcatchments, channels: "path/report/PATH_CE_Report.html",
    )


@pytest.fixture()
def controller(tmp_path):
    return _build_controller(_assemble_run_dir(tmp_path))


def test_full_run_produces_artifacts_and_results(controller):
    messages: list[str] = []
    payload = controller.run(status_callback=messages.append)

    assert payload["primary_status"] == 1
    assert payload["selected_hillslopes"] == [12]
    assert payload["schema_mode"] == "grouped"
    # acre cost basis: 167.85 ha * 2.47105 * 2475 * 0.5 (+500 fixed reported separately)
    assert payload["total_cost"] == pytest.approx(513272.61, abs=0.01)
    assert payload["sweep"]["n_errors"] == 0
    assert payload["sweep"]["reused"] is False
    assert controller.status == "completed"
    assert controller.progress == 1.0

    path_dir = Path(controller.wd) / "path"
    for rel in payload["artifacts"].values():
        assert (Path(controller.wd) / rel).exists(), rel

    selection = pd.read_parquet(path_dir / "selection.parquet")
    assert selection["treatment"].tolist() == ["0.5 tons/acre"]
    assert selection["scenario"].tolist() == ["mulch_15_sbs_map"]
    assert selection["cost"].sum() == pytest.approx(513272.61, abs=0.01)

    sweep = pd.read_parquet(path_dir / "sweep.parquet")
    assert "error" in sweep.columns
    assert (sweep["error"] == "").all()
    assert set(json.loads(sweep["selected_hillslopes"].iloc[0])) <= {12, 15, 18}

    assert any("Validating" in m for m in messages)
    assert any("threshold sweep" in m for m in messages)
    # rendering is unconditional (stubbed above): the report always attaches
    assert payload["report"]["html"] == "path/report/PATH_CE_Report.html"


def test_second_run_reuses_sweep_cache(controller):
    controller.run()
    payload = controller.run()
    assert payload["sweep"]["reused"] is True

    # sub-integer threshold changes keep the same grid anchors — reuse is correct
    controller._config = _normalize_config({"sdyd_threshold": 15.0, "sddc_threshold": 48.0})
    payload = controller.run()
    assert payload["sweep"]["reused"] is True

    # an anchor-changing threshold invalidates the cache
    controller._config = _normalize_config({"sdyd_threshold": 15.0, "sddc_threshold": 40.0})
    payload = controller.run()
    assert payload["sweep"]["reused"] is False

    # a treatment change invalidates the cache
    treatments = [t for t in default_treatments() if t["scenario"] == "mulch_60_sbs_map"]
    controller._config = _normalize_config(
        {"sdyd_threshold": 15.0, "sddc_threshold": 48.2, "treatments": treatments}
    )
    payload = controller.run()
    assert payload["sweep"]["reused"] is False


def test_run_uses_single_config_snapshot(controller, monkeypatch):
    """A mid-run config mutation must not leak into later stages or the snapshot."""
    original_prepare = PathCostEffective.prepare_data

    def _mutating_prepare(self, report=None):
        # simulate a concurrent config POST landing mid-run
        self._config = _normalize_config({"sdyd_threshold": 1.0, "sddc_threshold": 0.0})
        return original_prepare(self, report)

    monkeypatch.setattr(PathCostEffective, "prepare_data", _mutating_prepare)
    payload = controller.run()

    assert payload["config_snapshot"]["sddc_threshold"] == 48.2
    # solve ran with the entry snapshot (48.2 is primary-feasible; 0.0 is not)
    assert payload["primary_status"] == 1


def test_precondition_failure_sets_failed_status(controller):
    treatments = default_treatments()
    # mulch_90 has no scenarios/contrasts in the fixture
    treatments[2]["scenario"] = "mulch_90_sbs_map"
    treatments[2]["label"] = "3 tons/acre"
    controller._config = _normalize_config(
        {"sdyd_threshold": 15.0, "sddc_threshold": 48.2, "treatments": treatments}
    )

    with pytest.raises(PathCEPreconditionError) as exc_info:
        controller.run()

    assert controller.status == "failed"
    assert "mulch_90_sbs_map" in controller.status_message
    assert any("run Omni" in e for e in exc_info.value.report.errors)


def test_sweep_failing_every_cell_fails_the_run(controller, monkeypatch):
    error_row = {
        "sddc_threshold": 49, "sdyd_threshold": 0, "model_primary_status": None,
        "selected_hillslopes": None, "treatment_hillslopes": None,
        "total_Sddc_reduction": float("nan"), "final_Sddc": float("nan"),
        "hillslopes_sdyd": None, "sdyd_df": None, "untreatable_sdyd": None,
        "total_cost": float("nan"), "total_fixed_cost": float("nan"),
        "untreatable_sdyd_increase": None, "error": "RuntimeError('boom')",
    }
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.all_thresholds",
        lambda *a, **k: pd.DataFrame([error_row, error_row]),
    )

    with pytest.raises(PathCESolverError, match="every cell"):
        controller.run()
    assert controller.status == "failed"
    # no successful manifest is written for an all-failed sweep
    assert not (Path(controller.wd) / "path" / "sweep_manifest.json").exists()


def test_render_stage_always_invoked(tmp_path, monkeypatch):
    wd = _assemble_run_dir(tmp_path)
    controller = _build_controller(
        wd, {"sdyd_threshold": 15.0, "sddc_threshold": 48.2}
    )
    calls = {}

    def _fake_render(wd_arg, config, artifacts, subcatchments, channels):
        calls["config"] = config
        calls["subcatchments"] = subcatchments
        calls["channels"] = channels
        return "path/report/PATH_CE_Report.html"

    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.render_report", _fake_render
    )
    payload = controller.run()

    assert payload["report"]["html"] == "path/report/PATH_CE_Report.html"
    assert payload["report"]["skipped_reason"] is None
    assert calls["subcatchments"] == "dem/wbt/subcatchments.WGS.geojson"
    assert calls["config"]["sddc_threshold"] == 48.2


def test_render_skipped_without_geojson(tmp_path):
    wd = _assemble_run_dir(tmp_path)
    shutil.rmtree(wd / "dem")
    controller = _build_controller(
        wd, {"sdyd_threshold": 15.0, "sddc_threshold": 48.2}
    )
    payload = controller.run()

    assert payload["report"]["html"] is None
    assert "geojson" in payload["report"]["skipped_reason"]
    assert controller.status == "completed"


def test_results_are_detached_copies(controller):
    payload = controller.run()
    payload["selected_hillslopes"].append(999)
    assert 999 not in controller.results["selected_hillslopes"]
    view = controller.results
    view["treatments"].append("bogus")
    assert "bogus" not in controller.results["treatments"]
