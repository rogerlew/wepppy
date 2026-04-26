from __future__ import annotations

import contextlib
import time

import pytest

TestClient = pytest.importorskip("fastapi.testclient").TestClient

from tests.microservices._wepp_payload_doubles import GroupedSoilsDummy, GroupedWatershedDummy
import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine import bootstrap_routes
from wepppy.microservices.rq_engine import wepp_run_payload
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.redis_prep import TaskEnum
from wepppy.weppcloud.bootstrap.api_shared import BootstrapOperationError, BootstrapOperationResult
from wepppy.weppcloud.utils import auth_tokens

pytestmark = pytest.mark.microservice


def _stub_auth(monkeypatch: pytest.MonkeyPatch, *, claims: dict | None = None) -> None:
    resolved_claims = claims or {
        "sub": "7",
        "email": "user@example.com",
        "scope": " ".join(
            [
                bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE,
                bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE,
                bootstrap_routes.BOOTSTRAP_READ_SCOPE,
                bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE,
            ]
        ),
    }
    monkeypatch.setattr(
        bootstrap_routes,
        "require_jwt",
        lambda request, required_scopes=None: resolved_claims,
    )
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-1") -> None:
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            return DummyJob()

    class DummyRedis:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(bootstrap_routes, "Queue", DummyQueue)
    monkeypatch.setattr(bootstrap_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(bootstrap_routes, "acquire_wepp_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(bootstrap_routes, "release_wepp_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(bootstrap_routes, "ensure_no_active_wepp_job", lambda _runid, _prep, _redis_conn: None)


def _stub_prep(monkeypatch: pytest.MonkeyPatch, tasks: list[TaskEnum]) -> None:
    class DummyPrep:
        def remove_timestamp(self, task: TaskEnum) -> None:
            tasks.append(task)

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr(bootstrap_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


def _make_dummy_bootstrap_wepp(
    *,
    bootstrap_enabled: bool = True,
    persist_error: Exception | None = None,
):
    class DummyWepp:
        def __init__(self) -> None:
            self.bootstrap_enabled = bootstrap_enabled
            self._job_id = None
            self._job_key = None
            self.persist_job_hint_calls: list[dict[str, str]] = []

        @property
        def job_id(self):
            return self._job_id

        @property
        def job_key(self):
            return self._job_key

        def persist_job_hint(self, *, job_id: str, job_key: str) -> None:
            if persist_error is not None:
                raise persist_error
            self.persist_job_hint_calls.append({"job_id": job_id, "job_key": job_key})
            normalized_job_id = str(job_id).strip()
            normalized_job_key = str(job_key).strip()
            self._job_id = normalized_job_id if normalized_job_id else None
            self._job_key = normalized_job_key if normalized_job_key else None

    return DummyWepp()


def _issue_rq_token(
    monkeypatch: pytest.MonkeyPatch,
    *,
    scopes: list[str] | None = None,
    audience: str = "rq-engine",
    issued_at: int | None = None,
    expires_in: int = 3600,
    jti: str = "bootstrap-test-jti",
) -> str:
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRET", "unit-test-secret")
    monkeypatch.delenv("WEPP_AUTH_JWT_SECRETS", raising=False)
    auth_tokens.get_jwt_config.cache_clear()
    payload = auth_tokens.issue_token(
        "7",
        scopes=scopes or [bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE],
        audience=audience,
        issued_at=issued_at,
        expires_in=expires_in,
        extra_claims={
            "jti": jti,
            "token_class": "user",
            "email": "user@example.com",
        },
    )
    return payload["token"]


def test_bootstrap_enable_enqueues_job(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(
        bootstrap_routes,
        "enable_bootstrap_operation",
        lambda runid, actor: BootstrapOperationResult(
            payload={
                "enabled": False,
                "queued": True,
                "job_id": "enable-1",
                "message": "Bootstrap enable job enqueued.",
                "status_url": "/rq-engine/api/jobstatus/enable-1",
            },
            status_code=202,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 202
    assert response.json() == {
        "enabled": False,
        "queued": True,
        "job_id": "enable-1",
        "message": "Bootstrap enable job enqueued.",
        "status_url": "/rq-engine/api/jobstatus/enable-1",
    }


def test_bootstrap_enable_scope_only_token_works(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, scopes=[bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE])
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(
        bootstrap_routes,
        "enable_bootstrap_operation",
        lambda runid, actor: BootstrapOperationResult(payload={"queued": True, "job_id": "enable-2"}, status_code=202),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 202
    assert response.json() == {"queued": True, "job_id": "enable-2"}


def test_bootstrap_enable_rejects_rq_enqueue_without_bootstrap_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, scopes=["rq:enqueue"])
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE in payload["error"]["message"]


def test_bootstrap_enable_rejects_missing_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, scopes=["runs:read"])
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert bootstrap_routes.BOOTSTRAP_ENABLE_SCOPE in payload["error"]["message"]


def test_bootstrap_enable_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    now = int(time.time())
    token = _issue_rq_token(
        monkeypatch,
        issued_at=now - 120,
        expires_in=60,
    )
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "expired" in payload["error"]["message"].lower()


def test_bootstrap_enable_rejects_audience_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, audience="other-service")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(rq_auth, "_check_revocation", lambda _jti: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert "audience" in payload["error"]["message"].lower()


def test_bootstrap_enable_rejects_revoked_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _issue_rq_token(monkeypatch, jti="revoked-jti")
    headers = {"Authorization": f"Bearer {token}"}

    def _raise_revoked(_jti: str) -> None:
        raise rq_auth.AuthError("Token has been revoked", status_code=403, code="forbidden")

    monkeypatch.setattr(
        rq_auth,
        "_check_revocation",
        _raise_revoked,
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable", headers=headers)

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["message"] == "Token has been revoked"


def test_bootstrap_enable_maps_auth_runtime_error_to_canonical_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap_routes,
        "require_jwt",
        lambda request, required_scopes=None: (_ for _ in ()).throw(RuntimeError("auth backend unavailable")),
    )
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Failed to authorize request"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp-npprep",
        "/api/runs/run-1/cfg/run-wepp-watershed-no-prep",
        "/api/runs/run-1/cfg/run-swat-noprep",
    ],
)
def test_bootstrap_noprep_endpoints_map_auth_runtime_error_to_canonical_payload(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    monkeypatch.setattr(
        bootstrap_routes,
        "require_jwt",
        lambda request, required_scopes=None: (_ for _ in ()).throw(RuntimeError("auth backend unavailable")),
    )
    monkeypatch.setattr(bootstrap_routes, "authorize_run_access", lambda claims, runid: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Failed to authorize request"


def test_bootstrap_enable_rejects_when_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)

    def _raise_busy(runid: str, actor: str):
        raise BootstrapOperationError("bootstrap lock busy", status_code=409, code="conflict")

    monkeypatch.setattr(bootstrap_routes, "enable_bootstrap_operation", _raise_busy)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/enable")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "bootstrap lock busy"


def test_bootstrap_mint_token_requires_user_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"token_class": "session", "sub": "session-1", "scope": bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE})

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/mint-token")

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "User identity claims are required to mint bootstrap tokens"


def test_bootstrap_mint_token_returns_clone_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(
        monkeypatch,
        claims={"sub": "42", "email": "owner@example.com", "scope": bootstrap_routes.BOOTSTRAP_TOKEN_MINT_SCOPE},
    )
    monkeypatch.setattr(
        bootstrap_routes,
        "mint_bootstrap_token_operation",
        lambda runid, user_email, user_id: BootstrapOperationResult(
            payload={"clone_url": f"https://{user_id}:token@example.test/git/ru/run-1/.git"},
            status_code=200,
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/mint-token")

    assert response.status_code == 200
    assert response.json() == {"clone_url": "https://42:token@example.test/git/ru/run-1/.git"}


def test_bootstrap_checkout_requires_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE})
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/checkout", json={})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "sha required"


def test_bootstrap_checkout_invalid_json_payload_falls_back_to_missing_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(
        monkeypatch,
        claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE},
    )
    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/bootstrap/checkout",
            data="{not-json}",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "sha required"


def test_bootstrap_checkout_rejects_when_lock_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_CHECKOUT_SCOPE})

    monkeypatch.setattr(
        bootstrap_routes,
        "bootstrap_checkout_operation",
        lambda runid, sha, actor: (_ for _ in ()).throw(
            BootstrapOperationError("bootstrap lock busy", status_code=409, code="conflict")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/bootstrap/checkout", json={"sha": "abc1234"})

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "bootstrap lock busy"


def test_bootstrap_commits_allows_read_when_admin_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch, claims={"sub": "7", "email": "user@example.com", "scope": bootstrap_routes.BOOTSTRAP_READ_SCOPE})
    monkeypatch.setattr(
        bootstrap_routes,
        "bootstrap_commits_operation",
        lambda runid: BootstrapOperationResult(payload={"commits": [{"sha": "abc1234"}]}, status_code=200),
    )

    with TestClient(rq_engine.app) as client:
        response = client.get("/api/runs/run-1/cfg/bootstrap/commits")

    assert response.status_code == 200
    assert response.json() == {"commits": [{"sha": "abc1234"}]}


def test_bootstrap_run_wepp_npprep_enqueues(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-77")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    dummy_wepp = _make_dummy_bootstrap_wepp()
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: dummy_wepp)
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-77"
    assert set(tasks) == {
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
        TaskEnum.run_omni_scenarios,
        TaskEnum.run_path_cost_effective,
    }
    assert dummy_wepp.job_id == "job-77"
    assert dummy_wepp.job_key == "run_wepp_noprep_rq"
    assert dummy_wepp.persist_job_hint_calls == [
        {"job_id": "job-77", "job_key": "run_wepp_noprep_rq"}
    ]


@pytest.mark.parametrize(
    ("endpoint", "job_id", "job_key"),
    [
        ("/api/runs/run-1/cfg/run-wepp-npprep", "job-bootstrap-201", "run_wepp_noprep_rq"),
        ("/api/runs/run-1/cfg/run-wepp-watershed-no-prep", "job-bootstrap-202", "run_wepp_watershed_noprep_rq"),
    ],
)
def test_bootstrap_wepp_noprep_persists_job_id_to_wepp_nodb(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    job_id: str,
    job_key: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id=job_id)
    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    dummy_wepp = _make_dummy_bootstrap_wepp()
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: dummy_wepp)
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert dummy_wepp.job_id == job_id
    assert dummy_wepp.job_key == job_key
    assert dummy_wepp.persist_job_hint_calls == [{"job_id": job_id, "job_key": job_key}]


def test_bootstrap_run_swat_noprep_persists_job_hint_to_wepp_nodb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-swat-501")
    _stub_prep(monkeypatch, [])

    dummy_wepp = _make_dummy_bootstrap_wepp()
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: dummy_wepp)
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-swat-noprep", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-swat-501"}
    assert dummy_wepp.job_id == "job-swat-501"
    assert dummy_wepp.job_key == "run_swat_noprep_rq"
    assert dummy_wepp.persist_job_hint_calls == [
        {"job_id": "job-swat-501", "job_key": "run_swat_noprep_rq"}
    ]


def test_bootstrap_run_wepp_noprep_job_hint_persist_failure_after_enqueue_returns_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-bootstrap-hint-failed")
    _stub_prep(monkeypatch, [])

    monkeypatch.setattr(
        bootstrap_routes.Wepp,
        "getInstance",
        lambda wd: _make_dummy_bootstrap_wepp(persist_error=RuntimeError("nodb write failed")),
    )
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        bootstrap_routes.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-bootstrap-hint-failed"}
    assert len(exception_calls) == 1
    args, _kwargs = exception_calls[0]
    assert "failed to persist NoDb WEPP job hint" in str(args[0])
    assert "unexpected" not in str(args[0])


def test_bootstrap_run_wepp_noprep_job_hint_lock_contention_after_enqueue_returns_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-bootstrap-hint-lock")
    _stub_prep(monkeypatch, [])

    monkeypatch.setattr(
        bootstrap_routes.Wepp,
        "getInstance",
        lambda wd: _make_dummy_bootstrap_wepp(
            persist_error=NoDbAlreadyLockedError(
                "already locked owner=alice token=secret-token"
            )
        ),
    )
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        bootstrap_routes.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        bootstrap_routes.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-bootstrap-hint-lock"}
    assert len(warning_calls) == 1
    args, _kwargs = warning_calls[0]
    assert "hint persistence lock contention after enqueue" in str(args[0])
    warning_args_text = " ".join(str(arg) for arg in args)
    assert "owner=" not in warning_args_text
    assert "token=" not in warning_args_text
    assert exception_calls == []


def test_bootstrap_run_wepp_noprep_job_hint_unexpected_failure_after_enqueue_returns_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-bootstrap-hint-unexpected")
    _stub_prep(monkeypatch, [])

    monkeypatch.setattr(
        bootstrap_routes.Wepp,
        "getInstance",
        lambda wd: _make_dummy_bootstrap_wepp(persist_error=ValueError("unexpected nodb value")),
    )
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    exception_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        bootstrap_routes.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        bootstrap_routes.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append((args, kwargs)),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-bootstrap-hint-unexpected"}
    assert warning_calls == []
    assert len(exception_calls) == 1
    args, _kwargs = exception_calls[0]
    assert "failed to persist NoDb WEPP job hint" in str(args[0])
    assert "unexpected" in str(args[0])


def test_bootstrap_run_wepp_npprep_sparse_payload_preserves_existing_booleans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-78")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    class DummyWepp:
        def __init__(self) -> None:
            self.bootstrap_enabled = True
            self.dss_excluded_channel_orders = [1, 2]
            self._prep_details_on_run_completion = True
            self._arc_export_on_run_completion = True
            self._legacy_arc_export_on_run_completion = True
            self._dss_export_on_run_completion = True
            self._job_id = None
            self._job_key = None

        def parse_inputs(self, payload) -> None:
            return None

        @contextlib.contextmanager
        def locked(self):
            yield self

        @property
        def job_id(self):
            return self._job_id

        @property
        def job_key(self):
            return self._job_key

        def persist_job_hint(self, *, job_id: str, job_key: str) -> None:
            normalized_job_id = str(job_id).strip()
            normalized_job_key = str(job_key).strip()
            self._job_id = normalized_job_id if normalized_job_id else None
            self._job_key = normalized_job_key if normalized_job_key else None

    dummy_soils = GroupedSoilsDummy(
        clip_soils=True,
        clip_soils_depth=300,
        clip_soils_minimum=True,
        clip_soils_minimum_depth=120.0,
        rosetta_wc_fc_from_disturbed_bd_override=True,
    )
    dummy_watershed = GroupedWatershedDummy(
        clip_hillslopes=True,
        clip_hillslope_length=222,
    )
    dummy_wepp = DummyWepp()

    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: dummy_wepp)

    wepp_cls = type("DummyWeppClass", (), {"getInstance": staticmethod(lambda wd: dummy_wepp)})
    soils_cls = type("DummySoilsClass", (), {"getInstance": staticmethod(lambda wd: dummy_soils)})
    watershed_cls = type(
        "DummyWatershedClass",
        (),
        {"getInstance": staticmethod(lambda wd: dummy_watershed)},
    )
    ron_cls = type("DummyRonClass", (), {"getInstance": staticmethod(lambda wd: type("R", (), {"mods": []})())})

    def _apply_payload(wd: str, payload: dict):
        return wepp_run_payload.apply_wepp_run_payload(
            wd,
            payload,
            wepp_cls=wepp_cls,
            soils_cls=soils_cls,
            watershed_cls=watershed_cls,
            ron_cls=ron_cls,
        )

    monkeypatch.setattr(bootstrap_routes, "apply_wepp_run_payload", _apply_payload)

    with TestClient(rq_engine.app) as client:
        sparse_response = client.post(
            "/api/runs/run-1/cfg/run-wepp-npprep",
            json={"initial_sat": 0.2},
        )
        assert sparse_response.status_code == 200
        assert dummy_soils.clip_soils is True
        assert dummy_soils.clip_soils_minimum is True
        assert dummy_soils.rosetta_wc_fc_from_disturbed_bd_override is True
        assert dummy_watershed.clip_hillslopes is True
        assert dummy_wepp._prep_details_on_run_completion is True
        assert dummy_wepp._arc_export_on_run_completion is True
        assert dummy_wepp._legacy_arc_export_on_run_completion is True
        assert dummy_wepp._dss_export_on_run_completion is True

        clear_response = client.post(
            "/api/runs/run-1/cfg/run-wepp-npprep",
            json={
                "clip_soils": False,
                "clip_soils_minimum": False,
                "rosetta_wc_fc_from_disturbed_bd_override": False,
                "clip_hillslopes": False,
                "prep_details_on_run_completion": False,
                "arc_export_on_run_completion": False,
                "legacy_arc_export_on_run_completion": False,
                "dss_export_on_run_completion": False,
            },
        )

    assert clear_response.status_code == 200
    assert dummy_soils.clip_soils is False
    assert dummy_soils.clip_soils_minimum is False
    assert dummy_soils.rosetta_wc_fc_from_disturbed_bd_override is False
    assert dummy_watershed.clip_hillslopes is False
    assert dummy_wepp._prep_details_on_run_completion is False
    assert dummy_wepp._arc_export_on_run_completion is False
    assert dummy_wepp._legacy_arc_export_on_run_completion is False
    assert dummy_wepp._dss_export_on_run_completion is False
    assert dummy_soils.grouped_update_calls == [
        {
            "clip_soils": None,
            "clip_soils_depth": None,
            "clip_soils_minimum": None,
            "clip_soils_minimum_depth": None,
            "rosetta_wc_fc_from_disturbed_bd_override": None,
            "initial_sat": 0.2,
        },
        {
            "clip_soils": False,
            "clip_soils_depth": None,
            "clip_soils_minimum": False,
            "clip_soils_minimum_depth": None,
            "rosetta_wc_fc_from_disturbed_bd_override": False,
            "initial_sat": None,
        },
    ]
    assert dummy_watershed.grouped_update_calls == [
        {
            "clip_hillslopes": False,
            "clip_hillslope_length": None,
        }
    ]
    assert len(dummy_soils.dump_calls) == 2
    assert len(dummy_watershed.dump_calls) == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp-npprep",
        "/api/runs/run-1/cfg/run-wepp-watershed-no-prep",
    ],
)
def test_bootstrap_wepp_noprep_maps_nodb_lock_conflict_from_payload_apply(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-unused")
    _stub_prep(monkeypatch, [])
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: _make_dummy_bootstrap_wepp())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(
        bootstrap_routes,
        "apply_wepp_run_payload",
        lambda *args, **kwargs: (
            _ for _ in ()
        ).throw(NoDbAlreadyLockedError("already locked owner=alice token=secret-token")),
    )
    warning_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        bootstrap_routes.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={"clip_soils": True})

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "conflict"
    assert payload["error"]["message"] == bootstrap_routes.NODB_LOCK_CONFLICT_CLIENT_MESSAGE
    assert "owner=alice" not in payload["error"]["message"]
    assert "secret-token" not in payload["error"]["message"]
    assert len(warning_calls) == 1
    warning_args, _warning_kwargs = warning_calls[0]
    assert "payload apply lock conflict" in str(warning_args[0])
    warning_args_text = " ".join(str(arg) for arg in warning_args)
    assert "owner=" not in warning_args_text
    assert "token=" not in warning_args_text


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp-npprep",
        "/api/runs/run-1/cfg/run-wepp-watershed-no-prep",
    ],
)
def test_bootstrap_wepp_noprep_parse_failure_skips_payload_apply(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-unused")
    _stub_prep(monkeypatch, [])
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: _make_dummy_bootstrap_wepp())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(
        bootstrap_routes,
        "parse_request_payload",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad body")),
    )
    monkeypatch.setattr(
        bootstrap_routes,
        "apply_wepp_run_payload",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("payload apply should not be called")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={"clip_soils": True})

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "bad body"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp-npprep",
        "/api/runs/run-1/cfg/run-wepp-watershed-no-prep",
    ],
)
def test_bootstrap_wepp_noprep_validation_failure_skips_grouped_dumps(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-unused")
    _stub_prep(monkeypatch, [])

    class DummyWepp:
        bootstrap_enabled = True
        dss_excluded_channel_orders = [1, 2]
        _run_wepp_ui = True
        _run_wepp_watershed = True
        _run_pmet = True
        _run_frost = False
        _run_tcr = False
        _run_snow = True

        def parse_inputs(self, payload) -> None:
            return None

        @contextlib.contextmanager
        def locked(self):
            yield self

    class DummySoils:
        class_name = "soils"
        clip_soils = False
        clip_soils_depth = 300
        clip_soils_minimum = False
        clip_soils_minimum_depth = 0.0
        rosetta_wc_fc_from_disturbed_bd_override = False
        initial_sat = 0.75

        def __init__(self) -> None:
            self.dump_calls: list[dict[str, object]] = []
            self._locked = False

        def lock(self) -> None:
            self._locked = True

        def unlock(self) -> None:
            self._locked = False

        def dump(self) -> None:
            self.dump_calls.append(self.snapshot_wepp_run_payload_updates())

        def snapshot_wepp_run_payload_updates(self) -> dict[str, object]:
            return {
                "clip_soils": self.clip_soils,
                "clip_soils_depth": self.clip_soils_depth,
                "clip_soils_minimum": self.clip_soils_minimum,
                "clip_soils_minimum_depth": self.clip_soils_minimum_depth,
                "rosetta_wc_fc_from_disturbed_bd_override": self.rosetta_wc_fc_from_disturbed_bd_override,
                "initial_sat": self.initial_sat,
            }

        def restore_wepp_run_payload_updates(self, snapshot: dict[str, object]) -> None:
            self.clip_soils = bool(snapshot["clip_soils"])
            self.clip_soils_depth = snapshot["clip_soils_depth"]
            self.clip_soils_minimum = bool(snapshot["clip_soils_minimum"])
            self.clip_soils_minimum_depth = snapshot["clip_soils_minimum_depth"]
            self.rosetta_wc_fc_from_disturbed_bd_override = bool(
                snapshot["rosetta_wc_fc_from_disturbed_bd_override"]
            )
            self.initial_sat = snapshot["initial_sat"]

        def stage_wepp_run_payload_updates(self, **kwargs) -> bool:
            return True

    class DummyWatershed:
        class_name = "watershed"
        clip_hillslopes = False
        clip_hillslope_length = 300.0

        def __init__(self) -> None:
            self.dump_calls: list[dict[str, object]] = []
            self._locked = False

        def lock(self) -> None:
            self._locked = True

        def unlock(self) -> None:
            self._locked = False

        def dump(self) -> None:
            self.dump_calls.append(self.snapshot_wepp_run_payload_updates())

        def snapshot_wepp_run_payload_updates(self) -> dict[str, object]:
            return {
                "clip_hillslopes": self.clip_hillslopes,
                "clip_hillslope_length": self.clip_hillslope_length,
            }

        def restore_wepp_run_payload_updates(self, snapshot: dict[str, object]) -> None:
            self.clip_hillslopes = bool(snapshot["clip_hillslopes"])
            self.clip_hillslope_length = snapshot["clip_hillslope_length"]

        def stage_wepp_run_payload_updates(self, **kwargs) -> bool:
            return True

    dummy_wepp = DummyWepp()
    dummy_soils = DummySoils()
    dummy_watershed = DummyWatershed()

    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: dummy_wepp)

    wepp_cls = type("W", (), {"getInstance": staticmethod(lambda _wd: dummy_wepp)})
    soils_cls = type("S", (), {"getInstance": staticmethod(lambda _wd: dummy_soils)})
    watershed_cls = type("WS", (), {"getInstance": staticmethod(lambda _wd: dummy_watershed)})
    ron_cls = type("R", (), {"getInstance": staticmethod(lambda _wd: type("Ron", (), {"mods": []})())})

    def _apply_payload(wd: str, payload: dict):
        return wepp_run_payload.apply_wepp_run_payload(
            wd,
            payload,
            wepp_cls=wepp_cls,
            soils_cls=soils_cls,
            watershed_cls=watershed_cls,
            ron_cls=ron_cls,
        )

    monkeypatch.setattr(bootstrap_routes, "apply_wepp_run_payload", _apply_payload)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            endpoint,
            json={
                "clip_soils": True,
                "clip_soils_depth": 100,
                "clip_soils_minimum": True,
                "clip_soils_minimum_depth": 200,
            },
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_soil_depth_range"
    assert dummy_soils.dump_calls == []
    assert dummy_watershed.dump_calls == []


def test_bootstrap_run_swat_noprep_rejects_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_auth(monkeypatch)
    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: type("W", (), {"bootstrap_enabled": False})())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-swat-noprep")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Bootstrap is not enabled for this run"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp-npprep",
        "/api/runs/run-1/cfg/run-wepp-watershed-no-prep",
    ],
)
def test_bootstrap_wepp_noprep_returns_409_when_singleflight_conflict(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-409")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: _make_dummy_bootstrap_wepp())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(bootstrap_routes, "acquire_wepp_submit_lock", lambda _runid, _owner: True)
    monkeypatch.setattr(bootstrap_routes, "release_wepp_submit_lock", lambda _runid, _owner: None)
    monkeypatch.setattr(
        bootstrap_routes,
        "ensure_no_active_wepp_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            bootstrap_routes.WeppSingleFlightConflict("WEPP job already active for this run.")
        ),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 409
    payload = response.json()
    assert "already active" in payload["error"]["message"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/runs/run-1/cfg/run-wepp-npprep",
        "/api/runs/run-1/cfg/run-wepp-watershed-no-prep",
    ],
)
def test_bootstrap_wepp_noprep_returns_409_when_submit_lock_busy(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-lock")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: _make_dummy_bootstrap_wepp())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(bootstrap_routes, "acquire_wepp_submit_lock", lambda _runid, _owner: False)

    with TestClient(rq_engine.app) as client:
        response = client.post(endpoint, json={})

    assert response.status_code == 409
    payload = response.json()
    assert "enqueue already in progress" in payload["error"]["message"]


def test_bootstrap_noprep_release_lock_failure_after_enqueue_returns_job_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_auth(monkeypatch)
    _stub_queue(monkeypatch, job_id="job-release")

    tasks: list[TaskEnum] = []
    _stub_prep(monkeypatch, tasks)

    monkeypatch.setattr(bootstrap_routes.Wepp, "getInstance", lambda wd: _make_dummy_bootstrap_wepp())
    monkeypatch.setattr(bootstrap_routes, "get_wd", lambda runid, prefer_active=False: "/tmp/run")
    monkeypatch.setattr(
        bootstrap_routes,
        "release_wepp_submit_lock",
        lambda _runid, _owner: (_ for _ in ()).throw(RuntimeError("release failed")),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/run-wepp-npprep", json={})

    assert response.status_code == 200
    assert response.json() == {"job_id": "job-release"}
