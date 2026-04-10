from __future__ import annotations

from typing import Any

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import orchestration_read_routes
from wepppy.microservices.rq_engine import schema_defaults_routes
from wepppy.microservices.rq_engine import session_routes
from wepppy.microservices.rq_engine import setup_discovery_routes
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.microservice

RUNID = "run-1"
CONFIG = "disturbed9002_wbt"


def _issue_token(monkeypatch: pytest.MonkeyPatch, *, scopes: list[str], runs: list[str] | None = None) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "tester",
        scopes=scopes,
        audience="rq-engine",
        runs=runs,
        extra_claims={"jti": "test-jti", "token_class": "service"},
    )
    return payload["token"]


def _sample_schema_runtime() -> schema_defaults_routes.RuntimeState:
    return schema_defaults_routes.RuntimeState(
        runid=RUNID,
        config=CONFIG,
        active_mods=("disturbed", "wepp"),
        region="conus",
        states={
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "watershed_csa": 10.0,
            "watershed_mcl": 75.0,
            "delineation_backend": "wbt",
            "climate_built": False,
            "climate_mode_code": 11,
            "climate_mode": "gridmet_prism",
            "climate_has_station": True,
            "climate_station_required": False,
            "landuse_built": True,
            "landuse_mode": "nlcd",
            "soils_built": True,
            "soils_mode": "ssurgo",
            "initial_sat": 0.75,
            "wepp_has_run": False,
            "disturbed_enabled": True,
            "sbs_upload_supported": True,
            "disturbed_sbs_uploaded": True,
            "disturbed_sol_ver": 2018.0,
            "map_center": [-116.3, 45.65],
            "map_bounds": [-116.5, 45.5, -116.1, 45.8],
            "map_zoom": 11.0,
            "map_zoom_resolution_m_per_px": 9.6,
            "dem_coverage_source": "3dep",
            "uploaded_dem_filename": "dem.tif",
        },
        generated_at="2026-04-10T23:01:00Z",
        run_state_revision="runstate:run-1:abc123def456",
    )


def _sample_orchestration_runtime() -> dict[str, Any]:
    return {
        "runid": RUNID,
        "config": CONFIG,
        "active_mods": ("disturbed", "debris_flow", "ash"),
        "states": {
            "has_dem": True,
            "watershed_has_channels": True,
            "watershed_has_outlet": True,
            "watershed_is_abstracted": True,
            "watershed_subcatchment_count": 42,
            "climate_built": False,
            "climate_station_ready": True,
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
        "step_job": {},
        "generated_at": "2026-04-10T10:22:31Z",
    }


def _install_memory_redis(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    store: dict[str, Any] = {}

    class MemoryRedis:
        def get(self, key: str) -> Any:
            return store.get(key)

        def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False) -> bool:
            if nx and key in store:
                return False
            store[key] = value
            return True

        def delete(self, key: str) -> int:
            if key in store:
                del store[key]
                return 1
            return 0

        def close(self) -> None:
            return None

    monkeypatch.setattr(session_routes.redis, "Redis", lambda **kwargs: MemoryRedis())
    return store


def _stub_controller_state_auth(monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    monkeypatch.setattr(
        setup_discovery_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": scope},
    )
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": scope},
    )
    monkeypatch.setattr(
        orchestration_read_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": scope},
    )
    monkeypatch.setattr(schema_defaults_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(orchestration_read_routes, "authorize_run_access", lambda claims, runid: None)


@pytest.mark.parametrize("scope", ("rq:status", "rq:read"))
def test_controller_state_routes_accept_rollout_compatible_read_scopes(
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
) -> None:
    _stub_controller_state_auth(monkeypatch, scope)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())
    monkeypatch.setattr(
        orchestration_read_routes,
        "_load_runtime_state",
        lambda runid, config: _sample_orchestration_runtime(),
    )

    with TestClient(rq_engine.app) as client:
        assert client.get("/api/configs").status_code == 200
        assert client.get(f"/api/runs/{RUNID}/{CONFIG}/controllers").status_code == 200
        assert client.get(f"/api/runs/{RUNID}/{CONFIG}/pipeline").status_code == 200


def test_status_scope_stays_outside_mutation_scope_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/build-climate",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert "rq:enqueue" in payload["error"]["message"]


def test_session_token_includes_read_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    scopes = response.json()["scopes"]
    assert "rq:read" in scopes
    assert "rq:status" in scopes


def test_session_token_rejects_stale_run_state_precondition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setattr(session_routes, "_load_run_state_revision", lambda runid, config: "runstate:run-1:current")

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Run-State-Match": "runstate:run-1:stale",
            },
        )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "stale_run_state"
    assert payload["current_run_state_revision"] == "runstate:run-1:current"


def test_session_token_rejects_stale_run_state_from_request_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setattr(session_routes, "_load_run_state_revision", lambda runid, config: "runstate:run-1:current")

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={"Authorization": f"Bearer {token}"},
            json={"expected_run_state_revision": "runstate:run-1:stale"},
        )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "stale_run_state"
    assert payload["current_run_state_revision"] == "runstate:run-1:current"


def test_session_token_precondition_header_takes_precedence_over_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setattr(session_routes, "_load_run_state_revision", lambda runid, config: "runstate:run-1:current")

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Run-State-Match": "runstate:run-1:current",
            },
            json={"expected_run_state_revision": "runstate:run-1:stale"},
        )

    assert response.status_code == 200


def test_session_token_malformed_json_returns_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "idem-malformed-json",
                "Content-Type": "application/json",
            },
            content='{"expected_run_state_revision":',
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_session_token_idempotency_key_length_limit_returns_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "x" * 201,
                "Content-Type": "application/json",
            },
            json={"note": "too-long-key"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_session_token_rejects_non_object_json_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "idem-non-object-json",
                "Content-Type": "application/json",
            },
            json=["unexpected", "array"],
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_session_token_rejects_non_json_body_when_idempotency_key_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "idem-multipart",
            },
            files={"upload": ("demo.txt", b"hello", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_session_token_rejects_duplicate_idempotent_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idem-session-1",
        "Content-Type": "application/json",
    }

    with TestClient(rq_engine.app) as client:
        first = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers=headers,
            json={"note": "same"},
        )
        second = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers=headers,
            json={"note": "same"},
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_replay_rejected"


def test_session_token_rejects_idempotency_payload_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[RUNID])
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idem-session-2",
        "Content-Type": "application/json",
    }

    with TestClient(rq_engine.app) as client:
        first = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers=headers,
            json={"note": "first"},
        )
        second = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers=headers,
            json={"note": "second"},
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_key_conflict"


def test_session_token_public_fallback_rejects_duplicate_idempotent_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_routes, "_is_same_origin_cookie_request", lambda request: True)
    monkeypatch.setattr(session_routes, "_run_is_public", lambda runid: True)
    monkeypatch.setattr(
        session_routes,
        "_resolve_session_id_from_cookie",
        lambda request: (_ for _ in ()).throw(session_routes.AuthError("Missing session cookie", status_code=401)),
    )
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    _install_memory_redis(monkeypatch)

    headers = {
        "Idempotency-Key": "idem-public-fallback",
        "Content-Type": "application/json",
    }

    with TestClient(rq_engine.app) as client:
        first = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers=headers,
            json={"note": "same"},
        )
        second = client.post(
            f"/api/runs/{RUNID}/{CONFIG}/session-token",
            headers=headers,
            json={"note": "same"},
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_replay_rejected"


def test_issue_session_token_descriptor_matches_runtime_auth_concurrency_policies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": "rq:read"},
    )
    monkeypatch.setattr(schema_defaults_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())

    with TestClient(rq_engine.app) as client:
        endpoints_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints")
        assert endpoints_response.status_code == 200

        operations = endpoints_response.json()["operations"]
        descriptor = next(op for op in operations if op["operation_id"] == "rq_engine_issue_session_token")
        assert descriptor["accepted_auth"] == ["bearer_jwt", "session_cookie_same_origin"]
        assert descriptor["auth_requirements"]["bearer_jwt"]["required_scope"] == ["rq:status"]
        assert descriptor["write_precondition"]["required"] is False
        assert descriptor["write_precondition"]["accepted"] == ["x_run_state_match", "expected_run_state_revision"]
        assert descriptor["idempotency_policy"]["supported"] is True
        assert descriptor["idempotency_policy"]["replay_behavior"] == "reject_duplicate"
        assert descriptor["idempotency_policy"]["key_locations"] == ["header:Idempotency-Key"]
        assert descriptor["idempotency_policy"]["dedupe_window_seconds"] == session_routes._idempotency_ttl_seconds()

        errors_response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints/rq_engine_issue_session_token/errors")
        assert errors_response.status_code == 200

    error_codes = {entry["error_code"] for entry in errors_response.json()["errors"]}
    assert "stale_run_state" in error_codes
    assert "idempotency_replay_rejected" in error_codes
    assert "idempotency_key_conflict" in error_codes


def test_issue_session_token_descriptor_uses_env_overridden_idempotency_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RQ_ENGINE_SESSION_TOKEN_IDEMPOTENCY_TTL_SECONDS", "30")
    monkeypatch.setattr(
        schema_defaults_routes,
        "require_jwt",
        lambda request: {"sub": "svc", "token_class": "service", "scope": "rq:read"},
    )
    monkeypatch.setattr(schema_defaults_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(schema_defaults_routes, "_load_runtime_state", lambda runid, config: _sample_schema_runtime())

    with TestClient(rq_engine.app) as client:
        response = client.get(f"/api/runs/{RUNID}/{CONFIG}/endpoints")

    assert response.status_code == 200
    operations = response.json()["operations"]
    descriptor = next(op for op in operations if op["operation_id"] == "rq_engine_issue_session_token")
    assert descriptor["idempotency_policy"]["dedupe_window_seconds"] == 30


def test_session_token_precondition_invalid_grouped_runid_returns_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda jti: None)
    monkeypatch.setattr(session_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(session_routes, "_store_session_marker", lambda runid, session_id, ttl: None)
    monkeypatch.setattr(
        schema_defaults_routes,
        "_load_runtime_state",
        lambda runid, config: (_ for _ in ()).throw(ValueError("invalid grouped runid")),
    )

    grouped_runid = "unknown;;foo;;bar"
    grouped_runid_url = "unknown%3B%3Bfoo%3B%3Bbar"
    token = _issue_token(monkeypatch, scopes=["rq:status"], runs=[grouped_runid])

    with TestClient(rq_engine.app) as client:
        response = client.post(
            f"/api/runs/{grouped_runid_url}/{CONFIG}/session-token",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Run-State-Match": "runstate:run-1:stale",
            },
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
