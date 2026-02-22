from __future__ import annotations

import logging
from contextlib import nullcontext
from pathlib import Path

import pandas as pd
import pytest

from wepppy.nodb.mods.path_ce.data_loader import PathCEDataError, SolverInputs
from wepppy.nodb.mods.path_ce.path_ce_solver import PathCESolverError, SolverResult
from wepppy.nodb.mods.path_ce.path_cost_effective import PathCostEffective

pytestmark = pytest.mark.unit


def _build_controller(tmp_path: Path, *, config: dict | None = None) -> PathCostEffective:
    controller = PathCostEffective.__new__(PathCostEffective)
    controller.wd = str(tmp_path)
    controller.logger = logging.getLogger("tests.nodb.path_ce.path_cost_effective")

    path_dir = tmp_path / "path"
    path_dir.mkdir(parents=True, exist_ok=True)
    controller._path_dir = str(path_dir)

    controller._config = config or {
        "post_fire_scenario": "post_fire",
        "undisturbed_scenario": "undisturbed",
        "sdyd_threshold": 0.0,
        "sddc_threshold": 0.0,
        "slope_range": [None, None],
        "severity_filter": None,
        "mulch_costs": {},
        "treatment_options": [
            {
                "label": "T1",
                "scenario": "treat_s1",
                "quantity": 1.0,
                "unit_cost": 10.0,
                "fixed_cost": 0.0,
            }
        ],
    }

    controller._results = {}
    controller._status = "idle"
    controller._status_message = "Waiting for configuration."
    controller._progress = 0.0

    controller.locked = lambda: nullcontext()
    return controller


def _build_solver_inputs() -> SolverInputs:
    return SolverInputs(
        data=pd.DataFrame([{"wepp_id": 1, "topaz_id": 10, "Landuse": 105, "area": 10000.0}]),
        treatments=["T1"],
        treatment_costs=[10.0],
        treatment_quantities=[1.0],
        fixed_costs=[0.0],
        scenario_lookup={"T1": "treat_s1"},
    )


def _build_solver_result() -> SolverResult:
    untreatable = pd.DataFrame(
        {
            "wepp_id": pd.Series([], dtype="int64"),
            "final_Sdyd": pd.Series([], dtype="float64"),
        }
    )
    return SolverResult(
        selected_hillslopes=[1],
        treatment_hillslopes={"T1": [1]},
        total_sddc_reduction=12.5,
        final_sddc=100.0,
        hillslopes_sdyd=pd.DataFrame([{"wepp_id": 1, "final_Sdyd": 1.0}]),
        untreatable_sdyd=untreatable,
        total_cost=42.0,
        total_fixed_cost=0.0,
        status="Optimal",
        used_secondary=False,
    )


def test_run_success_records_running_states_and_stores_completed_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_controller(tmp_path)
    solver_inputs = _build_solver_inputs()
    solver_result = _build_solver_result()
    artifact_paths = {
        "analysis": "path/analysis_frame.parquet",
        "sdyd": "path/hillslope_sdyd.parquet",
        "untreatable": "path/untreatable_hillslopes.parquet",
    }

    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.load_solver_inputs",
        lambda *_args, **_kwargs: solver_inputs,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.run_path_cost_effective_solver",
        lambda *_args, **_kwargs: solver_result,
    )
    monkeypatch.setattr(PathCostEffective, "_persist_solver_outputs", lambda *_args, **_kwargs: artifact_paths)

    status_events: list[tuple[str, str | None, float | None]] = []
    original_set_status = PathCostEffective.set_status

    def _recording_set_status(
        self: PathCostEffective,
        status: str,
        *,
        message: str | None = None,
        progress: float | None = None,
    ) -> None:
        status_events.append((status, message, progress))
        original_set_status(self, status, message=message, progress=progress)

    monkeypatch.setattr(controller, "set_status", _recording_set_status.__get__(controller, PathCostEffective))

    stored: list[dict] = []
    original_store_results = PathCostEffective.store_results

    def _recording_store_results(self: PathCostEffective, results: dict) -> None:
        stored.append(dict(results))
        original_store_results(self, results)

    monkeypatch.setattr(controller, "store_results", _recording_store_results.__get__(controller, PathCostEffective))

    payload = controller.run()

    assert [event[0] for event in status_events] == ["running", "running", "running"]
    assert [event[1] for event in status_events] == [
        "Loading PATH inputs",
        "Running optimization model",
        "Persisting solver outputs",
    ]
    assert [event[2] for event in status_events] == [0.1, 0.55, 0.85]

    assert controller.status == "completed"
    assert controller.progress == pytest.approx(1.0)
    assert controller.results == payload
    assert stored == [payload]

    assert payload["analysis_artifact"] == artifact_paths["analysis"]
    assert payload["sdyd_artifact"] == artifact_paths["sdyd"]
    assert payload["untreatable_artifact"] == artifact_paths["untreatable"]

    assert payload["status"] == solver_result.status
    assert payload["used_secondary"] == solver_result.used_secondary
    assert payload["selected_hillslopes"] == solver_result.selected_hillslopes
    assert payload["treatment_hillslopes"] == solver_result.treatment_hillslopes
    assert payload["total_cost"] == solver_result.total_cost
    assert payload["total_fixed_cost"] == solver_result.total_fixed_cost
    assert payload["total_sddc_reduction"] == solver_result.total_sddc_reduction
    assert payload["final_sddc"] == solver_result.final_sddc


def test_run_marks_failed_when_load_solver_inputs_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_controller(tmp_path)
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.load_solver_inputs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PathCEDataError("missing inputs")),
    )

    with pytest.raises(PathCEDataError, match="missing inputs"):
        controller.run()

    assert controller.status == "failed"
    assert controller.status_message == "missing inputs"


def test_run_marks_failed_when_solver_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_controller(tmp_path)
    solver_inputs = _build_solver_inputs()

    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.load_solver_inputs",
        lambda *_args, **_kwargs: solver_inputs,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.run_path_cost_effective_solver",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PathCESolverError("solver failed")),
    )

    with pytest.raises(PathCESolverError, match="solver failed"):
        controller.run()

    assert controller.status == "failed"
    assert controller.status_message == "solver failed"


def test_run_marks_failed_and_reraises_when_persist_step_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _build_controller(tmp_path)
    solver_inputs = _build_solver_inputs()
    solver_result = _build_solver_result()

    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.load_solver_inputs",
        lambda *_args, **_kwargs: solver_inputs,
    )
    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective.run_path_cost_effective_solver",
        lambda *_args, **_kwargs: solver_result,
    )
    monkeypatch.setattr(
        PathCostEffective,
        "_persist_solver_outputs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("disk full")),
    )

    with pytest.raises(RuntimeError, match="disk full"):
        controller.run()

    assert controller.status == "failed"
    assert controller.status_message.startswith("Failed to persist solver outputs:")
    assert controller.status_message.endswith("disk full")


def test_persist_solver_outputs_warns_on_catalog_update_failure_and_returns_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    controller = _build_controller(tmp_path)
    solver_inputs = _build_solver_inputs()
    solver_result = _build_solver_result()

    def _raise_catalog(*_args, **_kwargs):
        raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(
        "wepppy.nodb.mods.path_ce.path_cost_effective._update_catalog_entry",
        _raise_catalog,
    )

    with caplog.at_level(logging.WARNING):
        paths = controller._persist_solver_outputs(solver_inputs, solver_result)

    assert paths == {
        "analysis": "path/analysis_frame.parquet",
        "sdyd": "path/hillslope_sdyd.parquet",
        "untreatable": "path/untreatable_hillslopes.parquet",
    }

    assert (tmp_path / paths["analysis"]).exists()
    assert (tmp_path / paths["sdyd"]).exists()
    assert (tmp_path / paths["untreatable"]).exists()

    assert any("Failed to refresh catalog for PATH CE artifacts" in record.message for record in caplog.records)
