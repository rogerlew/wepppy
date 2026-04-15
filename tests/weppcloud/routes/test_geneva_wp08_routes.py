from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.geneva_bp as geneva_module
from wepppy.nodb.mods.geneva.errors import GenevaGuardrailError, GenevaValidationError
from wepppy.nodb.mods.geneva.schemas import (
    default_geneva_config,
    merge_config,
    validate_measure_id,
)
from wepppy.nodb.mods.geneva.collaborators.batch_run_service import GenevaBatchRunService
from wepppy.nodb.mods.geneva.collaborators.frequency_panel_service import GenevaFrequencyPanelService


pytestmark = pytest.mark.routes

RUN_ID = "geneva-wp08-run"
CONFIG = "0"


class GenevaRouteStub:
    def __init__(self) -> None:
        self._enabled = True
        self._config = default_geneva_config().to_payload()
        self._config["enabled"] = self._enabled

        self.guard_error: GenevaGuardrailError | None = None
        self.frequency_panel_service = GenevaFrequencyPanelService()
        self.batch_run_service = GenevaBatchRunService()

        self._status_payload: dict[str, Any] = {
            "status": "completed_with_gaps",
            "status_message": "Geneva batch completed with unavailable storms.",
            "progress": {
                "completed": 1,
                "total": 2,
                "unit": "storms",
                "percent": 50.0,
                "updated_at": "2026-04-15T00:00:00Z",
            },
            "active_job_id": None,
            "last_job_id": "rq-last-1",
        }
        self._results_payload: dict[str, Any] = {
            "status": "completed_with_gaps",
            "last_prepare_summary": {
                "hru_count": 2,
                "hru_area_total_acres": 1.2,
                "hsg_provenance_counts": {"coded_lookup": 2},
            },
            "last_run_summary": {
                "batch_id": "batch-123",
                "datasource_ids": ["cligen_freq", "noaa14_pds"],
                "storm_count_total": 2,
                "storm_count_completed": 1,
                "storm_count_failed": 0,
                "storm_count_unavailable": 1,
                "artifacts": {
                    "batch_summary_relpath": "geneva/batch_summary.json",
                    "frequency_panel_relpath": "geneva/frequency_panel.json",
                },
            },
            "warnings": [{"code": "source_missing"}],
            "errors": [],
        }
        self._frequency_panel_payload: dict[str, Any] = {
            "schema_version": 1,
            "datasource_ids": ["cligen_freq", "noaa14_pds"],
            "durations_minutes": [30],
            "ari_years": [10],
            "distribution_type": "neh4_type_b",
            "cells": [
                {
                    "storm_id": "cligen_30m_10y",
                    "datasource_id": "cligen_freq",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "depth_mm": 20.0,
                    "intensity_mm_per_hr": 40.0,
                    "distribution_type": "neh4_type_b",
                    "availability": "available",
                    "reason_code": None,
                },
                {
                    "storm_id": "noaa14_30m_10y",
                    "datasource_id": "noaa14_pds",
                    "duration_minutes": 30,
                    "ari_years": 10,
                    "depth_mm": None,
                    "intensity_mm_per_hr": None,
                    "distribution_type": "neh4_type_b",
                    "availability": "unavailable",
                    "reason_code": "source_missing",
                },
            ],
            "warnings": [],
        }

    @property
    def enabled(self) -> bool:
        return self._enabled

    def get_config(self) -> dict[str, Any]:
        payload = dict(self._config)
        payload["enabled"] = self._enabled
        return payload

    def set_enabled(self, enabled: bool) -> None:
        if self.guard_error is not None and enabled is True:
            raise self.guard_error
        self._enabled = bool(enabled)
        self._config["enabled"] = self._enabled

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        updates = dict(payload)
        updates.pop("enabled", None)
        try:
            merged = merge_config(self.get_config(), updates)
        except ValueError as exc:
            raise GenevaValidationError(
                str(exc),
                code="invalid_input",
                details=str(exc),
                status_code=400,
            ) from exc
        self._config = merged.to_payload()
        self._config["enabled"] = self._enabled
        return dict(self._config)

    def assert_task_guardrails(self) -> None:
        if not self._enabled:
            raise GenevaValidationError(
                "Geneva mod is disabled.",
                code="mod_disabled",
                details="Enable Geneva before running this action.",
                status_code=400,
            )
        if self.guard_error is not None:
            raise self.guard_error

    def mark_job_queued(self, job_id: str, *, status_message: str) -> None:
        self._status_payload["status"] = "running"
        self._status_payload["status_message"] = status_message
        self._status_payload["active_job_id"] = job_id
        self._status_payload["last_job_id"] = job_id

    def status_payload(self) -> dict[str, Any]:
        return dict(self._status_payload)

    def results_payload(self) -> dict[str, Any]:
        return dict(self._results_payload)

    def frequency_panel_payload(self) -> dict[str, Any]:
        return dict(self._frequency_panel_payload)

    def query_summary_payload(
        self,
        *,
        datasource_id: str = "all",
        ari_years: list[int] | tuple[int, ...] | None = None,
        measure: str = "peak_discharge",
    ) -> dict[str, Any]:
        selected_measure = validate_measure_id(measure)
        datasource_filter = str(datasource_id or "all")
        if datasource_filter not in {"all", "cligen_freq", "noaa14_pds"}:
            raise GenevaValidationError(
                "datasource_id must be one of panel datasource_ids or all",
                code="invalid_input",
                details=datasource_filter,
                status_code=400,
            )
        ari_filter = sorted(set(int(value) for value in (ari_years or [10])))
        event_table = [
            {
                "storm_id": "cligen_30m_10y",
                "datasource_id": "cligen_freq",
                "duration_minutes": 30,
                "depth_mm": 20.0,
                "intensity_mm_per_hr": 40.0,
                "distribution_type": "neh4_type_b",
                "ari_years": 10,
                "peak_discharge": 1.2,
                "time_to_peak": 5.0,
                "runoff_volume": 100.0,
                "runoff_depth": 4.0,
            }
        ]
        return {
            "filters": {
                "datasource_id": datasource_filter,
                "ari_years": ari_filter,
                "measure": selected_measure,
            },
            "assumptions": {
                "arc_condition": "arc_ii",
                "storm_distribution_assumption": "neh4_type_b",
                "uniform_rainfall_assumed": True,
            },
            "chart": {
                "x_axis": "intensity_mm_per_hr",
                "y_axis": "selected_measure",
                "series": [
                    {
                        "ari_years": 10,
                        "points": [
                            {
                                "storm_id": "cligen_30m_10y",
                                "duration_minutes": 30,
                                "datasource_id": "cligen_freq",
                                "x": 40.0,
                                "y": event_table[0][selected_measure],
                            }
                        ],
                    }
                ],
            },
            "event_table": event_table,
            "warnings": [],
        }


@pytest.fixture()
def geneva_wp08_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rq_environment,
) -> Any:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(geneva_module.geneva_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    context = SimpleNamespace(active_root=run_dir)
    monkeypatch.setattr(geneva_module, "load_run_context", lambda _runid, _config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda _runid, _config, require_owner=False: None)

    stub = GenevaRouteStub()
    monkeypatch.setattr(geneva_module, "_ensure_geneva_controller", lambda _wd, _cfg_fn: stub)

    captured: Dict[str, Any] = {}

    def _fake_render_template(template: str, **context: Any) -> str:
        captured["template"] = template
        captured["context"] = context
        return "rendered"

    monkeypatch.setattr(geneva_module, "render_template", _fake_render_template)

    redis_conn_factory = rq_environment.redis_conn_factory(label="geneva-rq-redis")
    monkeypatch.setattr(geneva_module.redis, "Redis", lambda **kwargs: redis_conn_factory())
    monkeypatch.setattr(geneva_module, "Queue", rq_environment.queue_class(default_job_id="rq-geneva-1"))

    with app.test_client() as client:
        yield client, stub, captured, rq_environment


def test_config_routes_get_and_set(geneva_wp08_client: Any) -> None:
    client, stub, _, _ = geneva_wp08_client

    get_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/config")
    assert get_response.status_code == 200
    get_payload = get_response.get_json()
    assert get_payload["schema_version"] == 1
    assert get_payload["enabled"] is True

    post_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/geneva/config",
        json={"lambda_mode": "0.05", "default_hsg_code": 2},
    )
    assert post_response.status_code == 200
    post_payload = post_response.get_json()
    assert post_payload["lambda_mode"] == "0.05"
    assert post_payload["default_hsg_code"] == 2
    assert stub.get_config()["lambda_mode"] == "0.05"


def test_config_route_rejects_non_boolean_enabled(geneva_wp08_client: Any) -> None:
    client, _, _, _ = geneva_wp08_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/api/geneva/config",
        json={"enabled": "true"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["details"] == "enabled must be boolean"


def test_task_routes_return_canonical_rq_submission_envelope(geneva_wp08_client: Any) -> None:
    client, stub, _, rq_environment = geneva_wp08_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/geneva/prepare_hrus",
        json={"schema_version": 1, "force_rebuild": True},
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload == {
        "job_id": "rq-geneva-1",
        "status_url": "/rq-engine/api/jobstatus/rq-geneva-1",
        "message": "Job enqueued.",
    }
    assert stub.status_payload()["active_job_id"] == "rq-geneva-1"

    assert len(rq_environment.recorder.queue_calls) == 1
    call = rq_environment.recorder.queue_calls[0]
    assert call.func is geneva_module.run_geneva_prepare_hrus_rq
    assert call.args[0] == RUN_ID
    assert call.args[1] == CONFIG
    assert call.args[2] == {"schema_version": 1, "force_rebuild": True}


def test_build_frequency_panel_rejects_reserved_distribution_id(geneva_wp08_client: Any) -> None:
    client, _, _, _ = geneva_wp08_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/geneva/build_frequency_panel",
        json={"schema_version": 1, "distribution_type": "uniform"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_input"
    assert "unsupported in v1" in payload["error"]["message"]


def test_build_frequency_panel_rejects_non_integer_schema_version(geneva_wp08_client: Any) -> None:
    client, _, _, _ = geneva_wp08_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/geneva/build_frequency_panel",
        json={"schema_version": "bad"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["details"] == "schema_version must equal 1"


def test_run_batch_rejects_invalid_datasource_id(geneva_wp08_client: Any) -> None:
    client, _, _, _ = geneva_wp08_client

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/geneva/run_batch",
        json={
            "schema_version": 1,
            "event_filter": {"datasource_ids": ["bad_source"]},
            "hyetograph": {"distribution_type": "neh4_type_b", "time_step_minutes": 1.0},
            "runoff_model": {"timing_method": "kirpich"},
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_input"
    assert "datasource_id must be one of" in payload["error"]["message"]


def test_status_results_and_frequency_panel_contracts(geneva_wp08_client: Any) -> None:
    client, _, _, _ = geneva_wp08_client

    status_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/status")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["status"] == "completed_with_gaps"
    assert status_payload["progress"]["completed"] == 1
    assert status_payload["progress"]["total"] == 2

    results_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/results")
    assert results_response.status_code == 200
    results_payload = results_response.get_json()
    assert results_payload["status"] == "completed_with_gaps"
    assert results_payload["last_run_summary"]["storm_count_unavailable"] == 1
    assert results_payload["last_run_summary"]["artifacts"]["batch_summary_relpath"] == "geneva/batch_summary.json"

    panel_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/frequency_panel")
    assert panel_response.status_code == 200
    panel_payload = panel_response.get_json()
    assert panel_payload["datasource_ids"] == ["cligen_freq", "noaa14_pds"]
    assert panel_payload["cells"][1]["reason_code"] == "source_missing"


def test_query_and_report_summary_payloads_stay_in_sync(geneva_wp08_client: Any) -> None:
    client, _, captured, _ = geneva_wp08_client

    query_response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/query/geneva/summary"
        "?datasource_id=cligen_freq&ari_years=10&measure=runoff_depth"
    )
    assert query_response.status_code == 200
    query_payload = query_response.get_json()
    assert query_payload["filters"]["datasource_id"] == "cligen_freq"
    assert query_payload["filters"]["measure"] == "runoff_depth"

    report_response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/report/geneva/summary"
        "?datasource_id=cligen_freq&ari_years=10&measure=runoff_depth"
    )
    assert report_response.status_code == 200
    assert captured["template"] == "reports/geneva/summary.htm"
    assert captured["context"]["summary_payload"] == query_payload


def test_task_route_propagates_unsupported_backend_guard(geneva_wp08_client: Any) -> None:
    client, stub, _, _ = geneva_wp08_client
    stub.guard_error = GenevaGuardrailError(
        "Geneva requires the WBT delineation backend.",
        code="unsupported_backend",
        details="Enable Geneva only for runs with delineation_backend_is_wbt=true.",
        status_code=400,
    )

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/geneva/prepare_hrus",
        json={"schema_version": 1, "force_rebuild": False},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "unsupported_backend"
    assert payload["error"]["details"] == "Enable Geneva only for runs with delineation_backend_is_wbt=true."


def test_task_route_propagates_unsupported_domain_guard(geneva_wp08_client: Any) -> None:
    client, stub, _, _ = geneva_wp08_client
    stub.guard_error = GenevaGuardrailError(
        "Geneva v1 is US-only and requires NLCD + US NRCS-compatible HSG inputs.",
        code="unsupported_domain",
        details={"outside_us": True},
        status_code=400,
    )

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/geneva/run_batch",
        json={
            "schema_version": 1,
            "event_filter": {"datasource_ids": ["cligen_freq"]},
            "hyetograph": {"distribution_type": "neh4_type_b", "time_step_minutes": 1.0},
            "runoff_model": {"timing_method": "kirpich"},
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "unsupported_domain"
    assert payload["error"]["details"] == {"outside_us": True}
