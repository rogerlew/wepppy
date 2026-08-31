from __future__ import annotations

from dataclasses import dataclass, replace
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import project_config_update_routes as routes
import wepppy.nodb.project_config_update as project_update
from wepppy.nodb.config_builder.resolver import resolve_builder_capability_graph
from wepppy.nodb.config_builder.schema import BuilderSelections
from wepppy.nodb.config_builder.snapshot import resolve_builder_candidate
from wepppy.nodb.locales.capability_graph import CapabilityGraphError
from wepppy.nodb.project_config_snapshot import materialize_preset_snapshot
from wepppy.nodb.project_config_update import (
    CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
    ConfigUpdateAddition,
    ConfigUpdatePreview,
    ConfigUpdateResult,
    ConfigUpdateRegistryError,
    ConfigUpdateUnavailableError,
    ConfigUpdateStatus,
    JOURNAL_NAME,
)
from wepppy.project_config_serialization import parse_config_text, serialize_config

pytestmark = pytest.mark.microservice


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def set(self, key, value, *, nx=False, ex=None):
        if nx and key in self.values: return False
        self.values[key] = value; return True
    def get(self, key): return self.values.get(key)
    def delete(self, key): return int(self.values.pop(key, None) is not None)


@dataclass
class Enqueued:
    id: str


class FakeQueue:
    calls: list[dict] = []

    def __init__(self, **_kwargs): pass
    def enqueue_call(self, func, *, args, timeout, job_id):
        self.calls.append({"func": func, "args": args, "timeout": timeout, "job_id": job_id})
        return Enqueued(job_id)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    claims = {"token_class": "user", "sub": "42"}
    preview = ConfigUpdatePreview(
        True, "pcu1-preview", (ConfigUpdateAddition("new", "option", "true", "preset", "rev-2"),),
        "config.cfg", "a" * 64, "b" * 64, True,
    )
    redis_client = FakeRedis()
    FakeQueue.calls = []
    monkeypatch.setattr(routes, "require_jwt", lambda *_a, **_k: claims)
    monkeypatch.setattr(routes, "authorize_run_access", lambda *_a, **_k: None)
    monkeypatch.setattr(routes, "authorize_run_mutation", lambda *_a, **_k: None)
    monkeypatch.setattr(routes, "get_wd", lambda _runid: "/wc1/runs/run-1")
    monkeypatch.setattr(routes, "preview_project_config_update", lambda _wd, **_kwargs: preview)
    @contextmanager
    def preview_guard(_wd, **_kwargs):
        yield preview
    monkeypatch.setattr(routes, "project_config_update_preview_guard", preview_guard)
    monkeypatch.setattr(routes, "project_config_digest_warning", lambda _wd: True)
    monkeypatch.setattr(
        routes,
        "project_config_update_status",
        lambda _wd: ConfigUpdateStatus("a" * 64, None, "config.cfg"),
    )
    monkeypatch.setattr(
        routes, "project_config_update_reconciliation", lambda _wd, _preview_id: None
    )
    monkeypatch.setattr(routes, "project_config_update_enabled", lambda: True)
    monkeypatch.setattr(routes.redis, "Redis", lambda **_kwargs: redis_client)
    monkeypatch.setattr(routes, "Queue", FakeQueue)
    monkeypatch.setattr(routes, "new_rq_job_id", lambda: "job-update-1")
    monkeypatch.setattr(routes, "_application_revision", lambda: "route-revision")
    with TestClient(rq_engine.app) as http:
        yield http, claims, preview, redis_client


def test_availability_and_preview_are_synchronous_and_complete(client) -> None:
    http, _claims, preview, _redis = client
    availability = http.get("/api/runs/run-1/config/project-config/update-availability")
    response = http.get("/api/runs/run-1/config/project-config/update-preview")

    assert availability.status_code == 200
    assert availability.json() == {
        "available": True,
        "preview_id": preview.preview_id,
        "digest_warning": True,
        "current_digest": "a" * 64,
        "update_kind": "additive",
        "acknowledgment_required": False,
        "last_update": None,
    }
    assert response.status_code == 200
    assert response.json()["preview_id"] == preview.preview_id
    assert response.json()["digest_warning"] is True
    assert response.json()["additions"] == [{
        "section": "new", "option": "option", "value": "true",
        "source_id": "preset", "source_revision": "rev-2",
    }]


def test_apply_rejects_stale_preview_without_enqueue(client) -> None:
    http, _claims, _preview, _redis = client
    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={"preview_id": "pcu1-stale", "trigger": {"section": "new", "option": "option"}},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_config_preview"
    assert FakeQueue.calls == []


def test_apply_enqueues_once_and_reports_active_conflict(client) -> None:
    http, _claims, preview, _redis = client
    body = {"preview_id": preview.preview_id, "trigger": {"section": "new", "option": "option"}}
    accepted = http.post("/api/runs/run-1/config/project-config/update-apply", json=body)
    conflict = http.post("/api/runs/run-1/config/project-config/update-apply", json=body)

    assert accepted.status_code == 202
    assert accepted.json() == {"job_id": "job-update-1"}
    assert len(FakeQueue.calls) == 1
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "config_update_in_progress"


def test_preview_requires_mutation_authority(client, monkeypatch: pytest.MonkeyPatch) -> None:
    http, _claims, _preview, _redis = client

    def reject(*_args, **_kwargs):
        raise routes.AuthError("owner required", status_code=403, code="forbidden")

    monkeypatch.setattr(routes, "authorize_run_mutation", reject)
    response = http.get("/api/runs/run-1/config/project-config/update-preview")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_disabled_backend_returns_no_availability_and_no_enqueue(client, monkeypatch: pytest.MonkeyPatch) -> None:
    http, _claims, _preview, _redis = client
    monkeypatch.setattr(routes, "project_config_update_enabled", lambda: False)
    availability = http.get("/api/runs/run-1/config/project-config/update-availability")
    apply = http.post("/api/runs/run-1/config/project-config/update-apply", json={})
    assert availability.json() == {
        "available": False,
        "preview_id": None,
        "digest_warning": True,
        "current_digest": "a" * 64,
        "update_kind": None,
        "acknowledgment_required": False,
        "last_update": None,
        "reason": "updates_disabled",
    }
    assert apply.status_code == 409
    assert FakeQueue.calls == []


def test_nested_omni_route_uses_top_level_config_authority(client, monkeypatch: pytest.MonkeyPatch) -> None:
    http, _claims, preview, _redis = client
    resolved: list[str] = []
    monkeypatch.setattr(routes, "get_wd", lambda runid: resolved.append(runid) or "/wc1/runs/run-1")

    response = http.get(
        "/api/runs/run-1;;omni;;scenario-a/config/project-config/update-preview"
    )
    apply = http.post(
        "/api/runs/run-1;;omni;;scenario-a/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 200
    assert apply.status_code == 202
    assert resolved == ["run-1", "run-1"]
    assert FakeQueue.calls[0]["args"][0] == "run-1"


def test_capability_refresh_requires_exact_acknowledgment_before_reservation(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, _preview, redis_client = client
    refresh = {
        "acknowledgment": {
            "required": True,
            "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
            "text": "warning",
        },
        "changes": [],
    }
    preview = ConfigUpdatePreview(
        True,
        "pcu1-refresh",
        (),
        "config.cfg",
        "a" * 64,
        "a" * 64,
        False,
        "b" * 64,
        "capability_refresh",
        refresh,
    )
    monkeypatch.setattr(routes, "preview_project_config_update", lambda _wd, **_kwargs: preview)
    @contextmanager
    def preview_guard(_wd, **_kwargs):
        yield preview
    monkeypatch.setattr(routes, "project_config_update_preview_guard", preview_guard)

    missing = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={"preview_id": preview.preview_id},
    )

    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == (
        "capability_refresh_acknowledgment_required"
    )
    assert redis_client.values == {}
    assert FakeQueue.calls == []

    for acknowledgment in (
        {"accepted": False, "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION},
        {"accepted": True, "revision": "unknown-revision"},
        {
            "accepted": True,
            "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
            "unknown": True,
        },
    ):
        rejected = http.post(
            "/api/runs/run-1/config/project-config/update-apply",
            json={
                "preview_id": preview.preview_id,
                "capability_acknowledgment": acknowledgment,
            },
        )
        assert rejected.status_code == 400
        assert rejected.json()["error"]["code"] == (
            "capability_refresh_acknowledgment_required"
        )
    assert redis_client.values == {}
    assert FakeQueue.calls == []

    accepted = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "capability_acknowledgment": {
                "accepted": True,
                "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
            },
        },
    )

    assert accepted.status_code == 202
    assert FakeQueue.calls[0]["args"] == (
        "run-1",
        "config",
        "pcu1-refresh",
        "route-revision",
        None,
        None,
        True,
        CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
    )


def test_apply_rejects_preflight_failure_before_redis_or_queue(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, preview, redis_client = client

    @contextmanager
    def rejected_guard(_wd, **_kwargs):
        raise ConfigUpdateUnavailableError(
            "Pending amendment journal exceeds the canonical artifact size limit"
        )
        yield  # pragma: no cover

    monkeypatch.setattr(routes, "project_config_update_preview_guard", rejected_guard)
    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"].endswith("size limit")
    assert redis_client.values == {}
    assert FakeQueue.calls == []


def test_apply_real_preflight_rejects_incomplete_refresh_before_reservation(
    client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    http, _claims, _preview, redis_client = client
    selections = BuilderSelections(
        locale="europe", dem="europe-eudem-v1-1", delineation_backend="wbt",
        watershed_representation="single-ofe", wepp_binary="wepp_260803",
        soil="esdac-europe", landuse="corine-2018", climate="vanilla_cligen",
        climate_station_database="cligen-stations-ghcn",
        capability_profile="europe-capabilities",
    )
    candidate = resolve_builder_candidate(selections)
    materialize_preset_snapshot(tmp_path, candidate.artifact)
    config_path = tmp_path / "config.cfg"
    manifest_path = tmp_path / "config-manifest.json"
    config = parse_config_text(config_path.read_text(encoding="utf-8"))
    del config["general"]["dem_db"]
    config_bytes = serialize_config(config)
    config_path.write_bytes(config_bytes)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config"]["sha256"] = hashlib.sha256(config_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    graph = resolve_builder_capability_graph("europe")
    refreshed = replace(graph, provider_revision="9" * 64)
    refreshed.validate()
    monkeypatch.setattr(
        project_update,
        "resolve_builder_capability_graph",
        lambda _locale_id, **_kwargs: refreshed,
    )
    monkeypatch.setattr(routes, "get_wd", lambda _runid: str(tmp_path))
    monkeypatch.setattr(
        routes,
        "project_config_update_preview_guard",
        project_update.project_config_update_preview_guard,
    )
    monkeypatch.setattr(
        routes,
        "project_config_update_reconciliation",
        project_update.project_config_update_reconciliation,
    )
    before = config_path.read_bytes(), manifest_path.read_bytes()

    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": "pcu1-hostile",
            "capability_acknowledgment": {
                "accepted": True,
                "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "config_update_unavailable"
    assert "selection-bearing" in response.json()["error"]["details"]
    assert (config_path.read_bytes(), manifest_path.read_bytes()) == before
    assert not (tmp_path / JOURNAL_NAME).exists()
    assert redis_client.values == {}
    assert FakeQueue.calls == []


def test_registry_preflight_failure_is_diagnostic_503_without_reservation(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, preview, redis_client = client

    @contextmanager
    def rejected_guard(_wd, **_kwargs):
        raise ConfigUpdateRegistryError("registry document read failed")
        yield  # pragma: no cover

    monkeypatch.setattr(routes, "project_config_update_preview_guard", rejected_guard)
    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.json()["error"]["code"] == "builder_registry_error"
    assert response.json()["error"]["details"] == "registry document read failed"
    assert response.json()["error_id"]
    assert redis_client.values == {}
    assert FakeQueue.calls == []


def test_resolver_graph_failure_is_diagnostic_503_without_reservation(
    client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    http, _claims, _preview, redis_client = client
    selections = BuilderSelections(
        locale="europe", dem="europe-eudem-v1-1", delineation_backend="wbt",
        watershed_representation="single-ofe", wepp_binary="wepp_260803",
        soil="esdac-europe", landuse="corine-2018", climate="vanilla_cligen",
        climate_station_database="cligen-stations-ghcn",
        capability_profile="europe-capabilities",
    )
    materialize_preset_snapshot(
        tmp_path, resolve_builder_candidate(selections).artifact
    )
    config_path = tmp_path / "config.cfg"
    manifest_path = tmp_path / "config-manifest.json"
    before = config_path.read_bytes(), manifest_path.read_bytes()
    monkeypatch.setattr(routes, "get_wd", lambda _runid: str(tmp_path))
    monkeypatch.setattr(
        routes,
        "project_config_update_status",
        project_update.project_config_update_status,
    )
    monkeypatch.setattr(
        routes,
        "project_config_update_preview_guard",
        project_update.project_config_update_preview_guard,
    )
    monkeypatch.setattr(
        routes,
        "project_config_update_reconciliation",
        project_update.project_config_update_reconciliation,
    )
    monkeypatch.setattr(
        project_update,
        "resolve_builder_capability_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CapabilityGraphError("live provider graph failed validation")
        ),
    )

    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": "pcu1-hostile",
            "capability_acknowledgment": {
                "accepted": True,
                "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION,
            },
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "builder_registry_error"
    assert "live provider graph failed validation" in response.json()["error"]["details"]
    assert response.headers["Retry-After"] == "5"
    assert redis_client.values == {}
    assert FakeQueue.calls == []
    assert (config_path.read_bytes(), manifest_path.read_bytes()) == before


def test_stale_preview_precedes_new_acknowledgment_shape(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, _preview, redis_client = client
    refresh = ConfigUpdatePreview(
        True,
        "pcu1-new-refresh",
        (),
        "config.cfg",
        "a" * 64,
        "a" * 64,
        False,
        "b" * 64,
        "capability_refresh",
        {"acknowledgment": {"required": True, "revision": CAPABILITY_REFRESH_ACKNOWLEDGMENT_REVISION, "text": "warning"}},
    )

    @contextmanager
    def refresh_guard(_wd, **_kwargs):
        yield refresh

    monkeypatch.setattr(routes, "project_config_update_preview_guard", refresh_guard)
    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": "pcu1-old-additive",
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_config_preview"
    assert redis_client.values == {}
    assert FakeQueue.calls == []


def test_latest_matching_preview_returns_recovered_without_enqueue(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, preview, _redis = client
    monkeypatch.setattr(
        routes,
        "project_config_update_reconciliation",
        lambda _wd, _preview_id: ConfigUpdateResult(
            True,
            4,
            "a" * 64,
            "b" * 64,
            (),
            True,
            "additive",
        ),
    )

    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "applied": True,
        "recovered": True,
        "sequence": 4,
        "prior_digest": "a" * 64,
        "resulting_digest": "b" * 64,
    }
    assert FakeQueue.calls == []


def test_apply_rechecks_recovery_when_commit_wins_preview_guard_race(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, preview, _redis = client
    unavailable = replace(preview, available=False, preview_id=None, additions=())

    @contextmanager
    def unavailable_guard(_wd, **_kwargs):
        yield unavailable

    recovered = ConfigUpdateResult(
        True, 5, "a" * 64, "b" * 64, (), True, "additive"
    )
    reconciliation_results = iter((None, recovered))
    monkeypatch.setattr(routes, "project_config_update_preview_guard", unavailable_guard)
    monkeypatch.setattr(
        routes,
        "project_config_update_reconciliation",
        lambda _wd, _preview_id: next(reconciliation_results),
    )

    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "applied": True,
        "recovered": True,
        "sequence": 5,
        "prior_digest": "a" * 64,
        "resulting_digest": "b" * 64,
    }
    assert FakeQueue.calls == []


def test_recovered_apply_rejects_wrong_route_config_before_success(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, preview, _redis = client
    monkeypatch.setattr(
        routes,
        "project_config_update_reconciliation",
        lambda _wd, _preview_id: ConfigUpdateResult(
            True, 4, "a" * 64, "b" * 64, (), True, "additive"
        ),
    )

    response = http.post(
        "/api/runs/run-1/wrong-config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "config_update_unavailable"
    assert "Route config" in response.json()["error"]["details"]
    assert FakeQueue.calls == []


def test_apply_reports_malformed_update_state_before_queue_reservation(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, _claims, preview, redis_client = client
    monkeypatch.setattr(
        routes,
        "project_config_update_status",
        lambda _wd: (_ for _ in ()).throw(
            project_update.ConfigUpdateError("journal resulting digest is invalid")
        ),
    )

    response = http.post(
        "/api/runs/run-1/config/project-config/update-apply",
        json={
            "preview_id": preview.preview_id,
            "trigger": {"section": "new", "option": "option"},
        },
    )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "message": "Project config update state is invalid.",
        "details": "journal resulting digest is invalid",
        "code": "config_update_unavailable",
    }
    assert redis_client.values == {}
    assert FakeQueue.calls == []
