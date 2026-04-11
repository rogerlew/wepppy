from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import orchestration_read_routes

pytestmark = pytest.mark.microservice

PIPELINE_PATH = "/api/runs/run-1/disturbed9002_wbt/pipeline"
READINESS_PATH = "/api/runs/run-1/disturbed9002_wbt/readiness"
UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _stub_auth(monkeypatch: pytest.MonkeyPatch, scope: str, *, token_class: str = "service") -> None:
    monkeypatch.setattr(
        orchestration_read_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": token_class, "scope": scope},
    )
    monkeypatch.setattr(orchestration_read_routes, "authorize_run_access", lambda claims, runid: None)


def _assert_canonical_error(payload: dict[str, Any], *, code: str | None = None) -> None:
    assert set(payload).issuperset({"error"})
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["error"].get("message"), str)
    assert isinstance(payload["error"].get("details"), str)
    if code is not None:
        assert payload["error"].get("code") == code


def _sample_runtime_state() -> dict[str, Any]:
    return {
        "runid": "run-1",
        "config": "disturbed9002_wbt",
        "active_mods": ("disturbed", "debris_flow", "ash"),
        "states": {
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "climate_built": False,
            "climate_station_ready": False,
            "climate_mode": None,
            "landuse_built": True,
            "landuse_mode": "nlcd",
            "soils_built": True,
            "soils_mode": "ssurgo",
            "wepp_has_run": False,
            "wepp_hillslopes_run": False,
            "wepp_watershed_run": False,
            "disturbed_enabled": True,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver_selected": True,
        },
        "step_completion_ts": {
            "fetch-dem-and-build-channels": 100,
            "set-outlet": 110,
            "build-subcatchments-and-abstract-watershed": 120,
            "upload-sbs": 200,
            "build-climate": None,
            "build-landuse": 150,
            "build-soils": 140,
            "prep-wepp-watershed": 130,
            "run-wepp": 160,
            "run-wepp-watershed": 170,
            "build-rusle": 125,
            "run-ash": None,
            "run-debris-flow": None,
        },
        "step_job": {
            "build-climate": {
                "job_id": "rq-222",
                "status": "failed",
                "ended_at": "2026-04-10T09:21:49Z",
                "exc_info": "Missing station selection for selected climate mode.",
            }
        },
        "generated_at": "2026-04-10T10:22:31Z",
    }


def _sample_baseline_runtime_state() -> dict[str, Any]:
    runtime = _sample_runtime_state()
    runtime["config"] = "single_hillslope"
    runtime["active_mods"] = ()
    runtime["states"]["disturbed_enabled"] = False
    runtime["states"]["disturbed_sbs_uploaded"] = False
    runtime["states"]["disturbed_sol_ver_selected"] = False
    runtime["states"]["climate_station_ready"] = True
    runtime["step_completion_ts"]["upload-sbs"] = None
    runtime["step_completion_ts"]["run-ash"] = None
    runtime["step_completion_ts"]["run-debris-flow"] = None
    runtime["step_job"] = {}
    return runtime


def _sample_empty_timeline_runtime_state(generated_at: str) -> dict[str, Any]:
    runtime = _sample_baseline_runtime_state()
    runtime["step_completion_ts"] = {step_id: None for step_id in runtime["step_completion_ts"]}
    runtime["step_job"] = {}
    runtime["generated_at"] = generated_at
    return runtime


def _step_by_id(payload: dict[str, Any], step_id: str) -> dict[str, Any]:
    return next(step for step in payload["steps"] if step["step_id"] == step_id)


def test_orchestration_routes_require_auth() -> None:
    with TestClient(rq_engine.app) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 401
    _assert_canonical_error(pipeline_response.json(), code="unauthorized")
    assert readiness_response.status_code == 401
    _assert_canonical_error(readiness_response.json(), code="unauthorized")


def test_orchestration_routes_reject_wrong_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:enqueue")

    with TestClient(rq_engine.app) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 403
    _assert_canonical_error(pipeline_response.json(), code="forbidden")
    assert readiness_response.status_code == 403
    _assert_canonical_error(readiness_response.json(), code="forbidden")


@pytest.mark.parametrize("path", (PIPELINE_PATH, READINESS_PATH))
def test_orchestration_routes_reject_run_access_and_do_not_load_state(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(
        orchestration_read_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": "rq:status"},
    )
    monkeypatch.setattr(
        orchestration_read_routes,
        "authorize_run_access",
        lambda claims, runid: (_ for _ in ()).throw(
            orchestration_read_routes.AuthError("run access denied", status_code=403, code="forbidden")
        ),
    )
    load_calls = {"count": 0}

    def _never_load(runid: str, config: str) -> dict[str, Any]:
        load_calls["count"] += 1
        return _sample_runtime_state()

    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", _never_load)

    with TestClient(rq_engine.app) as client:
        response = client.get(path)

    assert response.status_code == 403
    _assert_canonical_error(response.json(), code="forbidden")
    assert load_calls["count"] == 0


@pytest.mark.parametrize("scope", ("rq:status", "rq:read"))
def test_orchestration_routes_accept_supported_scopes(
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
) -> None:
    _stub_auth(monkeypatch, scope)
    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", lambda runid, config: _sample_runtime_state())

    with TestClient(rq_engine.app) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 200
    assert readiness_response.status_code == 200


def test_pipeline_payload_contract_and_invalidation_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", lambda runid, config: _sample_runtime_state())

    with TestClient(rq_engine.app) as client:
        response = client.get(PIPELINE_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "contract_version",
        "deployment_revision",
        "run_state_domain",
        "run_state_revision",
        "run_state_vector",
        "updated_at",
        "data_state",
        "data_updated_at",
        "etag",
        "runid",
        "config",
        "active_mods",
        "recent_invalidations",
        "steps",
    }
    assert payload["runid"] == "run-1"
    assert payload["config"] == "disturbed9002_wbt"
    assert payload["active_mods"] == ["disturbed", "debris_flow", "ash"]
    assert payload["run_state_domain"] == "orchestration"
    assert payload["run_state_revision"].startswith("runstate:run-1:")
    assert payload["run_state_vector"] == {
        "orchestration_revision": payload["run_state_revision"],
        "metadata_revision": None,
        "outputs_revision": None,
    }
    assert payload["data_state"] == "materialized"
    assert payload["data_updated_at"] == payload["updated_at"]
    assert payload["etag"].startswith('W/"pipeline:run-1:')

    steps_by_id = {entry["step_id"]: entry for entry in payload["steps"]}
    assert steps_by_id["build-landuse"]["status"] == "ready"
    assert steps_by_id["build-landuse"]["can_run_now"] is True
    assert steps_by_id["build-landuse"]["invalidated_by_operation_id"] == "rq_engine_upload_sbs"
    assert steps_by_id["run-wepp"]["status"] == "blocked"

    invalidation = next(
        item for item in payload["recent_invalidations"] if item["source_operation_id"] == "rq_engine_upload_sbs"
    )
    assert set(invalidation["invalidated_steps"]).issuperset(
        {"build-landuse", "build-soils", "run-wepp", "run-wepp-watershed"}
    )


def test_readiness_payload_has_join_safe_blocker_links(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", lambda runid, config: _sample_runtime_state())

    with TestClient(rq_engine.app) as client:
        response = client.get(READINESS_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_state_domain"] == "orchestration"
    assert payload["run_state_vector"]["orchestration_revision"] == payload["run_state_revision"]
    assert payload["data_state"] == "materialized"
    assert payload["data_updated_at"] == payload["updated_at"]
    assert payload["etag"].startswith('W/"readiness:run-1:')
    issue_ids = {issue["issue_id"] for issue in payload["blocking_issues"]}
    assert "issue_climate_station_missing" in issue_ids

    for operation in payload["ineligible_operations"]:
        for issue_id in operation["blocked_by_issue_ids"]:
            assert issue_id in issue_ids

    next_steps = payload["next_actionable_steps"]
    assert next_steps
    assert next_steps[0]["step_id"] == "build-climate"
    assert next_steps[0]["related_issue_ids"] == ["issue_climate_station_missing"]
    priorities = [entry["priority"] for entry in next_steps]
    assert priorities == sorted(priorities)


def test_readiness_next_actionable_steps_are_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", lambda runid, config: _sample_runtime_state())

    with TestClient(rq_engine.app) as client:
        first = client.get(READINESS_PATH).json()
        second = client.get(READINESS_PATH).json()

    assert first["run_state_revision"] == second["run_state_revision"]
    assert first["next_actionable_steps"] == second["next_actionable_steps"]


def test_readiness_next_actionable_steps_are_deterministic_for_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    monkeypatch.setattr(
        orchestration_read_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_baseline_runtime_state(),
    )

    with TestClient(rq_engine.app) as client:
        first = client.get(READINESS_PATH).json()
        second = client.get(READINESS_PATH).json()

    assert first["run_state_revision"] == second["run_state_revision"]
    assert first["next_actionable_steps"] == second["next_actionable_steps"]


def test_orchestration_routes_return_404_for_unknown_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _missing(runid: str, config: str) -> dict[str, Any]:
        raise FileNotFoundError("missing run")

    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", _missing)

    with TestClient(rq_engine.app) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 404
    _assert_canonical_error(pipeline_response.json(), code="not_found")
    assert readiness_response.status_code == 404
    _assert_canonical_error(readiness_response.json(), code="not_found")


def test_orchestration_routes_return_404_for_config_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _mismatch(runid: str, config: str) -> dict[str, Any]:
        raise orchestration_read_routes.RunConfigMismatchError("run config mismatch")

    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", _mismatch)

    with TestClient(rq_engine.app) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 404
    _assert_canonical_error(pipeline_response.json(), code="not_found")
    assert readiness_response.status_code == 404
    _assert_canonical_error(readiness_response.json(), code="not_found")


def test_orchestration_routes_return_500_for_unexpected_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _bad_state(runid: str, config: str) -> dict[str, Any]:
        raise ValueError("malformed state")

    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", _bad_state)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 500
    _assert_canonical_error(pipeline_response.json())
    assert readiness_response.status_code == 500
    _assert_canonical_error(readiness_response.json())


def test_completion_falls_back_to_state_keys_when_timestamp_missing() -> None:
    runtime = _sample_runtime_state()
    runtime["states"]["landuse_built"] = True
    runtime["step_completion_ts"]["build-landuse"] = None
    runtime["step_completion_ts"]["upload-sbs"] = None

    pipeline_payload, _ = orchestration_read_routes._compute_payloads(runtime)
    build_landuse = _step_by_id(pipeline_payload, "build-landuse")
    assert build_landuse["status"] == "completed"


def test_prepare_roads_finished_job_unblocks_run_roads() -> None:
    runtime = _sample_runtime_state()
    runtime["active_mods"] = ("roads",)
    runtime["states"]["disturbed_enabled"] = False
    runtime["states"]["disturbed_sbs_uploaded"] = False
    runtime["states"]["disturbed_sol_ver_selected"] = False
    runtime["step_completion_ts"]["prepare-roads"] = None
    runtime["step_completion_ts"]["run-roads"] = None
    runtime["step_job"] = {
        "prepare-roads": {
            "job_id": "rq-roads-prepare",
            "status": "finished",
            "ended_at": None,
            "exc_info": None,
        }
    }

    pipeline_payload, _ = orchestration_read_routes._compute_payloads(runtime)
    prepare_roads = _step_by_id(pipeline_payload, "prepare-roads")
    run_roads = _step_by_id(pipeline_payload, "run-roads")

    assert prepare_roads["status"] == "completed"
    assert run_roads["status"] == "ready"


def test_run_swat_finished_job_is_completed() -> None:
    runtime = _sample_runtime_state()
    runtime["active_mods"] = ("swat",)
    runtime["states"]["disturbed_enabled"] = False
    runtime["states"]["disturbed_sbs_uploaded"] = False
    runtime["states"]["disturbed_sol_ver_selected"] = False
    runtime["step_job"] = {
        "run-swat": {
            "job_id": "rq-swat-run",
            "status": "finished",
            "ended_at": None,
            "exc_info": None,
        }
    }

    pipeline_payload, _ = orchestration_read_routes._compute_payloads(runtime)
    run_swat = _step_by_id(pipeline_payload, "run-swat")
    assert run_swat["status"] == "completed"


def test_run_state_revision_changes_when_last_attempt_changes() -> None:
    failed_runtime = _sample_runtime_state()
    canceled_runtime = deepcopy(failed_runtime)
    canceled_runtime["step_job"]["build-climate"]["status"] = "canceled"
    canceled_runtime["step_job"]["build-climate"]["ended_at"] = "2026-04-10T09:25:49Z"

    failed_pipeline, failed_readiness = orchestration_read_routes._compute_payloads(failed_runtime)
    canceled_pipeline, canceled_readiness = orchestration_read_routes._compute_payloads(canceled_runtime)

    failed_attempt = _step_by_id(failed_pipeline, "build-climate")["last_attempt"]
    canceled_attempt = _step_by_id(canceled_pipeline, "build-climate")["last_attempt"]

    assert failed_attempt != canceled_attempt
    assert failed_readiness["run_state_revision"] != canceled_readiness["run_state_revision"]


def test_failed_steps_without_precondition_issues_get_join_safe_blocker_ids() -> None:
    runtime = _sample_runtime_state()
    runtime["states"]["climate_station_ready"] = True
    runtime["step_completion_ts"]["build-climate"] = None
    runtime["step_completion_ts"]["upload-sbs"] = None

    _pipeline_payload, readiness_payload = orchestration_read_routes._compute_payloads(runtime)

    ineligible_by_step = {entry["step_id"]: entry for entry in readiness_payload["ineligible_operations"]}
    build_climate = ineligible_by_step["build-climate"]
    assert build_climate["blocked_by_issue_ids"]

    blocking_issue_ids = {issue["issue_id"] for issue in readiness_payload["blocking_issues"]}
    assert set(build_climate["blocked_by_issue_ids"]).issubset(blocking_issue_ids)


def test_failed_last_attempt_redacts_raw_exception_text(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, "rq:status")
    runtime = _sample_runtime_state()
    runtime["step_job"]["build-climate"][
        "exc_info"
    ] = "Traceback (most recent call last):\nRuntimeError: sensitive internal details"
    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", lambda runid, config: runtime)

    with TestClient(rq_engine.app) as client:
        response = client.get(PIPELINE_PATH)

    assert response.status_code == 200
    payload = response.json()
    build_climate = next(step for step in payload["steps"] if step["step_id"] == "build-climate")
    assert build_climate["last_attempt"]["error_message"] == "Last attempt failed. Inspect jobinfo for details."
    assert "Traceback" not in build_climate["last_attempt"]["error_message"]
    assert "sensitive internal details" not in build_climate["last_attempt"]["error_message"]


def test_naive_datetime_values_are_treated_as_utc() -> None:
    naive = orchestration_read_routes._parse_datetime_to_timestamp("2026-04-10T09:21:49")
    aware = orchestration_read_routes._parse_datetime_to_timestamp("2026-04-10T09:21:49Z")
    assert naive == aware


def test_effective_job_status_uses_child_tree_statuses() -> None:
    job_info = {
        "status": "finished",
        "children": {
            "0": [
                {
                    "status": "started",
                    "ended_at": None,
                    "children": {},
                }
            ]
        },
    }
    assert orchestration_read_routes._effective_job_status(job_info) == "started"


def test_effective_job_status_prioritizes_failure_over_non_terminal_children() -> None:
    job_info = {
        "status": "finished",
        "children": {
            "0": [
                {
                    "status": "failed",
                    "ended_at": "2026-04-10T10:00:02Z",
                    "children": {},
                }
            ],
            "1": [
                {
                    "status": "deferred",
                    "ended_at": None,
                    "children": {},
                }
            ],
        },
    }
    assert orchestration_read_routes._effective_job_status(job_info) == "failed"


def test_effective_job_ended_at_uses_latest_child_completion() -> None:
    job_info = {
        "status": "finished",
        "ended_at": "2026-04-10T10:00:00Z",
        "children": {
            "0": [
                {
                    "status": "finished",
                    "ended_at": "2026-04-10T10:00:05Z",
                    "children": {},
                }
            ]
        },
    }
    assert orchestration_read_routes._effective_job_ended_at(job_info) == "2026-04-10T10:00:05Z"


def test_readiness_updated_at_and_etag_are_stable_when_timeline_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")
    calls = {"count": 0}
    fallback_updated_at = "2026-04-10T10:00:00Z"

    def _runtime(runid: str, config: str) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] == 1:
            return _sample_empty_timeline_runtime_state("2026-04-10T10:00:00Z")
        return _sample_empty_timeline_runtime_state("2026-04-10T10:00:01Z")

    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", _runtime)
    monkeypatch.setattr(
        orchestration_read_routes,
        "_runtime_snapshot_updated_at",
        lambda runtime: fallback_updated_at,
    )

    with TestClient(rq_engine.app) as client:
        first = client.get(READINESS_PATH).json()
        second = client.get(READINESS_PATH).json()

    assert first["etag"] == second["etag"]
    assert first["run_state_revision"] == second["run_state_revision"]
    assert first["updated_at"] == second["updated_at"]
    assert first["data_updated_at"] == second["data_updated_at"] == first["updated_at"]
    assert first["data_state"] == second["data_state"] == "materialized"
    assert UTC_TIMESTAMP_RE.match(first["updated_at"])
    assert first["updated_at"] != "1970-01-01T00:00:00Z"
    updated_at = datetime.fromisoformat(first["updated_at"].replace("Z", "+00:00"))
    assert updated_at <= datetime.now(timezone.utc)


def test_orchestration_routes_internal_failures_return_canonical_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch, "rq:status")

    def _boom(runid: str, config: str) -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(orchestration_read_routes, "_load_runtime_state", _boom)

    with TestClient(rq_engine.app, raise_server_exceptions=False) as client:
        pipeline_response = client.get(PIPELINE_PATH)
        readiness_response = client.get(READINESS_PATH)

    assert pipeline_response.status_code == 500
    _assert_canonical_error(pipeline_response.json())
    assert readiness_response.status_code == 500
    _assert_canonical_error(readiness_response.json())
