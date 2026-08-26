import contextlib
import asyncio
import os
from types import SimpleNamespace
from uuid import UUID

import pytest
from rq.exceptions import NoSuchJobError
from starlette.datastructures import FormData

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import fork_archive_routes
from wepppy.weppcloud.utils import helpers as helpers_utils
from wepppy.weppcloud.utils import runid as runid_utils


pytestmark = pytest.mark.microservice


@pytest.mark.parametrize("value", [True, False])
def test_strict_fork_omni_boolean_accepts_json_booleans(value: bool) -> None:
    class Request:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {"skip_omni_scenarios_contrasts": value}

    assert asyncio.run(
        fork_archive_routes._strict_request_boolean(
            Request(),
            "skip_omni_scenarios_contrasts",
        )
    ) is value


@pytest.mark.parametrize("value", [1, 0, [True], ["true"], {"value": True}, "garbage"])
def test_strict_fork_omni_boolean_rejects_non_scalar_json(value: object) -> None:
    class Request:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {"skip_omni_scenarios_contrasts": value}

    with pytest.raises(ValueError):
        asyncio.run(
            fork_archive_routes._strict_request_boolean(
                Request(),
                "skip_omni_scenarios_contrasts",
            )
        )


@pytest.mark.parametrize(
    ("token", "expected"),
    [(token, expected) for expected, tokens in ((True, ("1", "true", "YES", "on")), (False, ("0", "false", "NO", "off"))) for token in tokens],
)
def test_strict_fork_omni_boolean_accepts_form_tokens(token: str, expected: bool) -> None:
    class Request:
        headers = {"content-type": "application/x-www-form-urlencoded"}

        async def form(self):
            return FormData([("skip_omni_scenarios_contrasts", token)])

    assert asyncio.run(
        fork_archive_routes._strict_request_boolean(
            Request(),
            "skip_omni_scenarios_contrasts",
        )
    ) is expected


def test_strict_fork_omni_boolean_rejects_repeated_form_values() -> None:
    class Request:
        headers = {"content-type": "application/x-www-form-urlencoded"}

        async def form(self):
            return FormData(
                [
                    ("skip_omni_scenarios_contrasts", "false"),
                    ("skip_omni_scenarios_contrasts", "true"),
                ]
            )

    with pytest.raises(ValueError):
        asyncio.run(
            fork_archive_routes._strict_request_boolean(
                Request(),
                "skip_omni_scenarios_contrasts",
            )
        )


def _stub_queue(
    monkeypatch: pytest.MonkeyPatch,
    *,
    job_id: str = "job-123",
    enqueue_calls: list[tuple[tuple[object, ...], dict[str, object]]] | None = None,
) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    monkeypatch.setattr(fork_archive_routes, "new_rq_job_id", lambda: job_id)
    constructor_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    class DummyJob:
        id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            constructor_calls.append((args, kwargs))

        def enqueue_call(self, *args, **kwargs):
            if enqueue_calls is not None:
                enqueue_calls.append((args, kwargs))
            return DummyJob()

    class DummyRedis:
        values: dict[str, str] = {}
        hashes: dict[str, dict[str, str]] = {}

        def lock(self, *args, **kwargs):
            class Lock:
                def acquire(self, **_kwargs): return True
                def extend(self, *args, **kwargs): return True
                def release(self): return None
            return Lock()

        def get(self, key):
            return self.values.get(key)

        def set(self, key, value, **kwargs):
            self.values[key] = value
            return True

        def hgetall(self, key):
            return self.hashes.get(key, {})

        def hget(self, key, field):
            return self.hashes.get(key, {}).get(field)

        def hset(self, key, mapping):
            self.hashes[key] = dict(mapping)
            return len(mapping)

        def delete(self, key):
            self.values.pop(key, None)
            self.hashes.pop(key, None)
            return 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def close(self) -> None:
            return None

    monkeypatch.setattr(fork_archive_routes, "Queue", DummyQueue)
    monkeypatch.setattr(fork_archive_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    return constructor_calls


def _stub_prep(
    monkeypatch: pytest.MonkeyPatch,
    *,
    archive_job_id: str | None = None,
):
    monkeypatch.setattr(
        fork_archive_routes,
        "_discover_legacy_fork_root",
        lambda *args, **kwargs: None,
    )
    class DummyPrep:
        def __init__(self) -> None:
            self.archive_job_id = archive_job_id
            self.clear_calls = 0

        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

        def get_rq_job_id(self, key):
            return None

        def get_archive_job_id(self) -> str | None:
            return self.archive_job_id

        def set_archive_job_id(self, job_id: str, *args, **kwargs) -> None:
            self.archive_job_id = job_id

        def clear_archive_job_id(self) -> None:
            self.clear_calls += 1
            self.archive_job_id = None

    prep = DummyPrep()
    monkeypatch.setattr(fork_archive_routes.RedisPrep, "getInstance", lambda wd: prep)
    return prep


class _DummyUserQuery:
    def __init__(self, user) -> None:
        self._user = user
        self._filters: dict[str, object] = {}

    def filter_by(self, **kwargs):
        self._filters = kwargs
        return self

    def first(self):
        user_id = self._filters.get("id")
        if user_id is not None:
            try:
                normalized_id = int(str(user_id))
            except (TypeError, ValueError):
                return None
            return self._user if normalized_id == getattr(self._user, "id", None) else None

        email = self._filters.get("email")
        if email is not None and str(email) == str(getattr(self._user, "email", "")):
            return self._user

        return None


def _patch_user_model_lookup(monkeypatch: pytest.MonkeyPatch, user, user_datastore) -> None:
    class DummyUserModel:
        query = _DummyUserQuery(user)

    class DummyRunModel:
        query = _DummyUserQuery(None)

    monkeypatch.setattr(
        helpers_utils,
        "get_user_models",
        lambda: (DummyRunModel, DummyUserModel, user_datastore),
    )


def test_fork_requires_cap_for_anonymous(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "_ensure_anonymous_access", lambda runid, wd: None)
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])
    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fork")

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["message"] == "CAPTCHA token is required."


def test_fork_requires_cap_for_anonymous_session_claims(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr(fork_archive_routes, "_resolve_bearer_claims", lambda request: {"token_class": "session"})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid, **kwargs: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])
    monkeypatch.setattr(fork_archive_routes, "_ensure_anonymous_access", lambda runid, wd: None)
    monkeypatch.setattr(fork_archive_routes, "_resolve_user_from_claims", lambda claims: (None, None, None))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["message"] == "CAPTCHA token is required."


def test_fork_rejects_non_string_target_runid(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "_resolve_bearer_claims", lambda request: {"token_class": "user"})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid, **kwargs: None)
    monkeypatch.setattr(fork_archive_routes, "_resolve_user_from_claims", lambda claims: (None, None, None))
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            json={"target_runid": 123},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Invalid target_runid"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == "Invalid target_runid"
    assert payload["error_id"]


def test_fork_enqueues_job(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(fork_archive_routes, "_resolve_bearer_claims", lambda request: {"token_class": "user"})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid, **kwargs: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(fork_archive_routes, "has_archive", lambda runid: False)
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(fork_archive_routes, "generate_runid", lambda email=None: "new-run")

    class DummyUserDatastore:
        def create_run(self, *args, **kwargs) -> None:
            return None

    class DummyUser:
        def __init__(self) -> None:
            self.id = 10
            self.email = "user@example.com"
            self.runs: list[object] = []

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    user = DummyUser()
    user_datastore = DummyUserDatastore()
    _patch_user_model_lookup(monkeypatch, user, user_datastore)

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (user, user_datastore, DummyApp()),
    )

    enqueue_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    constructor_calls = _stub_queue(monkeypatch, job_id="job-42", enqueue_calls=enqueue_calls)
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={
                "undisturbify": "true",
                "skip_wepp_runs_output": "true",
                "skip_omni_scenarios_contrasts": "true",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-42"
    assert payload["new_runid"] == "new-run"
    assert payload["undisturbify"] is True
    assert payload["skip_wepp_runs_output"] is True
    assert payload["skip_omni_scenarios_contrasts"] is True
    assert constructor_calls[0][0] == ("fork-archive",)
    assert len(enqueue_calls) == 1
    enqueue_args, enqueue_kwargs = enqueue_calls[0]
    assert enqueue_args[0] is fork_archive_routes.fork_rq
    assert enqueue_args[1] == ("run-1", "new-run", True, True, True)
    assert "timeout" in enqueue_kwargs
    assert enqueue_kwargs["job_id"] == payload["job_id"]


def test_target_association_treats_metadata_as_authoritative() -> None:
    job = SimpleNamespace(
        meta={"runid": "source-run"},
        args=("source-run", "target-run"),
        func_name="wepppy.rq.interchange_rq.run_interchange_migration",
        origin="default",
    )
    assert not fork_archive_routes._job_targets_destination(job, "target-run")


def test_target_association_supports_legacy_migration_run_argument() -> None:
    job = SimpleNamespace(
        meta={},
        args=("/wc1/runs/ta/target-run", "target-run"),
        func_name="wepppy.rq.migrations_rq.migrations_rq",
        origin="default",
    )
    assert fork_archive_routes._job_targets_destination(job, "target-run")


@pytest.mark.parametrize(
    "skip_field",
    [
        {},
        {"skip_wepp_runs_output": "false"},
    ],
)
def test_fork_skip_wepp_runs_output_defaults_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    skip_field: dict[str, str],
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(fork_archive_routes, "_resolve_bearer_claims", lambda request: {"token_class": "user"})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(fork_archive_routes, "has_archive", lambda runid: False)
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(fork_archive_routes, "generate_runid", lambda email=None: "new-run")

    class DummyUserDatastore:
        def create_run(self, *args, **kwargs) -> None:
            return None

    class DummyUser:
        def __init__(self) -> None:
            self.id = 10
            self.email = "user@example.com"
            self.runs: list[object] = []

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    user = DummyUser()
    user_datastore = DummyUserDatastore()
    _patch_user_model_lookup(monkeypatch, user, user_datastore)

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (user, user_datastore, DummyApp()),
    )

    enqueue_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    _stub_queue(monkeypatch, job_id="job-default-skip", enqueue_calls=enqueue_calls)
    _stub_prep(monkeypatch)

    request_data = {"undisturbify": "false"}
    request_data.update(skip_field)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data=request_data,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-default-skip"
    assert payload["new_runid"] == "new-run"
    assert payload["undisturbify"] is False
    assert payload["skip_wepp_runs_output"] is False
    assert len(enqueue_calls) == 1
    enqueue_args, _enqueue_kwargs = enqueue_calls[0]
    assert enqueue_args[0] is fork_archive_routes.fork_rq
    assert enqueue_args[1] == ("run-1", "new-run", False, False, False)


def test_fork_user_mdobre_email_generates_mdobre_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "user", "email": "mdobre@example.com"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])
    monkeypatch.setattr(runid_utils.awesome_codename, "generate_codename", lambda: "storm harbor")

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())

    class DummyUserDatastore:
        def create_run(self, *args, **kwargs) -> None:
            return None

    class DummyUser:
        def __init__(self) -> None:
            self.id = 11
            self.email = "mdobre@example.com"
            self.runs: list[object] = []

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    user = DummyUser()
    user_datastore = DummyUserDatastore()
    _patch_user_model_lookup(monkeypatch, user, user_datastore)

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (user, user_datastore, DummyApp()),
    )

    _stub_queue(monkeypatch, job_id="job-mdobre-user")
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"undisturbify": "false"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-mdobre-user"
    assert payload["new_runid"] == "mdobre-storm-harbor"


def test_fork_session_claims_use_resolved_user_email_for_runid(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "session", "user_id": 7},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())

    class DummyUser:
        def __init__(self) -> None:
            self.id = 7
            self.email = "mdobre@example.com"
            self.runs: list[object] = []

    class DummyRunRecord:
        pass

    class DummyUserDatastore:
        def __init__(self) -> None:
            self.created: list[tuple[str, str, object]] = []

        def create_run(self, runid, source_config, owner):
            self.created.append((runid, source_config, owner))
            return DummyRunRecord()

        def add_run_to_user(self, owner, run_record):
            if run_record not in owner.runs:
                owner.runs.append(run_record)

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    user = DummyUser()
    user_datastore = DummyUserDatastore()
    _patch_user_model_lookup(monkeypatch, user, user_datastore)
    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (user, user_datastore, DummyApp()),
    )

    captured_emails: list[str] = []

    def _fake_generate_runid(email: str | None = None) -> str:
        captured_emails.append(str(email or ""))
        return "mdobre-prefixed-run"

    monkeypatch.setattr(fork_archive_routes, "generate_runid", _fake_generate_runid)

    _stub_queue(monkeypatch, job_id="job-session")
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"undisturbify": "false"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-session"
    assert payload["new_runid"] == "mdobre-prefixed-run"
    assert captured_emails == ["mdobre@example.com"]
    assert len(user_datastore.created) == 1


def test_fork_rebinds_detached_users_before_adding_run_to_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "user", "sub": "1", "email": "mdobre@example.com"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid, **kwargs: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "generate_runid", lambda email=None: "new-run")

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())

    class DummyUser:
        def __init__(self, user_id: int, email: str) -> None:
            self.id = user_id
            self.email = email
            self.runs: list[object] = []

    detached_owner = DummyUser(1, "mdobre@example.com")
    detached_user = DummyUser(1, "mdobre@example.com")
    attached_user = DummyUser(1, "mdobre@example.com")

    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [detached_owner])

    class DummyUserQuery:
        def __init__(self, user: DummyUser) -> None:
            self._user = user
            self._filters: dict[str, object] = {}

        def filter_by(self, **kwargs):
            self._filters = kwargs
            return self

        def first(self) -> DummyUser | None:
            user_id = self._filters.get("id")
            if user_id is not None:
                try:
                    normalized_id = int(str(user_id))
                except (TypeError, ValueError):
                    return None
                return self._user if normalized_id == self._user.id else None
            email = self._filters.get("email")
            if email is not None and str(email) == self._user.email:
                return self._user
            return None

    class DummyUserModel:
        query = DummyUserQuery(attached_user)

    class DummyRunModel:
        query = _DummyUserQuery(None)

    class DummyUserDatastore:
        def __init__(self) -> None:
            self.run_record = object()
            self.create_run_owners: list[DummyUser] = []
            self.added_users: list[DummyUser] = []

        def create_run(self, *args, **kwargs):
            owner = args[2]
            if owner is not attached_user:
                raise RuntimeError("detached owner passed to create_run")
            self.create_run_owners.append(owner)
            return self.run_record

        def add_run_to_user(self, owner, run_record):
            if owner is not attached_user:
                raise RuntimeError("detached owner passed to add_run_to_user")
            self.added_users.append(owner)
            if run_record not in owner.runs:
                owner.runs.append(run_record)

    user_datastore = DummyUserDatastore()

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (detached_user, user_datastore, DummyApp()),
    )
    monkeypatch.setattr(
        helpers_utils,
        "get_user_models",
        lambda: (DummyRunModel, DummyUserModel, user_datastore),
    )

    _stub_queue(monkeypatch, job_id="job-detached")
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"undisturbify": "false"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-detached"
    assert payload["new_runid"] == "new-run"
    assert user_datastore.create_run_owners == [attached_user]
    assert user_datastore.added_users == [attached_user]


def test_fork_failure_returns_stacktrace(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    new_dir = tmp_path / "new"

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "get_primary_wd", lambda runid: str(new_dir))
    monkeypatch.setattr(fork_archive_routes, "has_archive", lambda runid: False)
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    monkeypatch.setattr(fork_archive_routes, "generate_runid", lambda email=None: "new-run")

    def _raise_prep(_wd: str):
        raise RuntimeError("prep failed")

    monkeypatch.setattr(fork_archive_routes.RedisPrep, "getInstance", _raise_prep)
    _stub_queue(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post("/api/runs/run-1/cfg/fork", data={"undisturbify": "true"})

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error forking project"
    details = payload["error"].get("details")
    assert isinstance(details, str)
    assert "RuntimeError: prep failed" in details


def test_fork_target_runid_bypasses_generate_runid(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    requested_runid = "custom-fork-runid"
    target_dir = tmp_path / requested_runid

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service", "email": "mdobre@example.com"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(
        fork_archive_routes,
        "get_wd",
        lambda runid, prefer_active=True: str(run_dir) if runid == "run-1" else str(target_dir),
    )
    monkeypatch.setattr(
        fork_archive_routes,
        "get_primary_wd",
        lambda runid: str(tmp_path / runid),
    )
    monkeypatch.setattr(
        fork_archive_routes,
        "_exists",
        lambda path: True if str(path) == str(run_dir) else False,
    )
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())

    class DummyUserDatastore:
        def create_run(self, *args, **kwargs) -> None:
            return None

    class DummyUser:
        def __init__(self) -> None:
            self.id = 12
            self.email = "mdobre@example.com"
            self.runs: list[object] = []

    class DummyApp:
        @contextlib.contextmanager
        def app_context(self):
            yield

    user = DummyUser()
    user_datastore = DummyUserDatastore()
    _patch_user_model_lookup(monkeypatch, user, user_datastore)

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (user, user_datastore, DummyApp()),
    )

    def _fail_generate_runid(_email: str | None = None) -> str:
        raise AssertionError("generate_runid should not be called when target_runid is provided")

    monkeypatch.setattr(fork_archive_routes, "generate_runid", _fail_generate_runid)

    _stub_queue(monkeypatch, job_id="job-custom-runid")
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"undisturbify": "false", "target_runid": requested_runid},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-custom-runid"
    assert payload["new_runid"] == requested_runid


def test_fork_target_runid_rejects_invalid_identifier(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "user", "email": "mdobre@example.com"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)

    def _fake_get_wd(runid: str, prefer_active: bool = True) -> str:
        if runid == "run-1":
            return str(run_dir)
        raise ValueError("invalid run id")

    monkeypatch.setattr(fork_archive_routes, "get_wd", _fake_get_wd)
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: str(path) == str(run_dir))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"target_runid": "../evil", "undisturbify": "false"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Invalid target_runid"
    assert payload["error"]["code"] == "validation_error"


def test_fork_target_runid_runtime_error_returns_500(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)

    def _fake_get_wd(runid: str, prefer_active: bool = True) -> str:
        if runid == "run-1":
            return str(run_dir)
        raise RuntimeError("get_wd failed")

    monkeypatch.setattr(fork_archive_routes, "get_wd", _fake_get_wd)
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: str(path) == str(run_dir))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"target_runid": "custom-fork", "undisturbify": "false"},
        )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Error forking project"


def test_fork_target_runid_rejects_non_string_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid, prefer_active=True: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: str(path) == str(run_dir))

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            json={"target_runid": 123, "undisturbify": False},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "Invalid target_runid"
    assert payload["error"]["code"] == "validation_error"


def test_fork_target_runid_refuses_overwrite_for_non_profile_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    target_dir = tmp_path / "existing-target"
    target_dir.mkdir()

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service", "email": "mdobre@example.com"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid, **kwargs: None)
    monkeypatch.setattr(
        fork_archive_routes,
        "get_wd",
        lambda runid, prefer_active=True: str(run_dir) if runid == "run-1" else str(target_dir),
    )
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: str(path) in {str(run_dir), str(target_dir)})
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])
    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    _stub_queue(monkeypatch)
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"target_runid": "existing-target", "undisturbify": "false"},
        )

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["message"] == "target_runid already exists"
    assert payload["error"]["code"] == "conflict"


def test_profile_fork_target_has_exclusive_job_claim_and_redis_namespace(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    run_dir = tmp_path / "source"
    run_dir.mkdir()
    profile_root = tmp_path / "profiles" / "fork"
    profile_root.mkdir(parents=True)
    target_dir = profile_root / "leaf"

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda request: {"token_class": "service"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid, **kwargs: None)

    def _get_wd(runid: str, prefer_active: bool = True) -> str:
        if runid == "run-1":
            return str(run_dir)
        if runid == "profile;;fork;;__root_probe__":
            return str(profile_root / "__root_probe__")
        if runid == "profile;;fork;;leaf":
            return str(target_dir)
        raise ValueError(runid)

    monkeypatch.setattr(fork_archive_routes, "get_wd", _get_wd)
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda runid: [])

    class DummyRon:
        config_stem = "cfg"

    monkeypatch.setattr(fork_archive_routes.Ron, "getInstance", lambda wd: DummyRon())
    _stub_prep(monkeypatch)
    enqueued: list[dict[str, object]] = []

    class DummyJob:
        def __init__(self, job_id: str) -> None:
            self.id = job_id

    class DummyQueue:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def enqueue_call(self, *args, **kwargs):
            enqueued.append(kwargs)
            return DummyJob(str(kwargs["job_id"]))

    class DummyRedis:
        values: dict[str, str] = {}
        hashes: dict[str, dict[str, str]] = {}

        def lock(self, *args, **kwargs):
            class Lock:
                def acquire(self, **_kwargs): return True
                def extend(self, *args, **kwargs): return True
                def release(self): return None
            return Lock()

        def get(self, key): return self.values.get(key)
        def set(self, key, value, **kwargs):
            self.values[key] = value
            return True

        def hgetall(self, key): return self.hashes.get(key, {})
        def hget(self, key, field): return self.hashes.get(key, {}).get(field)
        def hset(self, key, mapping):
            self.hashes[key] = dict(mapping)
            return len(mapping)
        def delete(self, key):
            self.values.pop(key, None)
            self.hashes.pop(key, None)
            return 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(fork_archive_routes, "Queue", DummyQueue)
    monkeypatch.setattr(fork_archive_routes.redis, "Redis", lambda **kwargs: DummyRedis())
    monkeypatch.setattr(fork_archive_routes, "redis_connection_kwargs", lambda db: {})
    monkeypatch.setattr(
        fork_archive_routes,
        "reconcile_deferred_workflow",
        lambda *args, **kwargs: SimpleNamespace(state="active", job_ids=("active-fork",)),
    )

    with TestClient(rq_engine.app) as client:
        first = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"target_runid": "profile;;fork;;leaf"},
        )
        second = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"target_runid": "profile;;fork;;leaf"},
        )

    assert first.status_code == 200
    job_id = first.json()["job_id"]
    assert enqueued[0]["job_id"] == job_id
    assert (target_dir / ".redisprep-run-id").read_text(encoding="utf-8") == "profile;;fork;;leaf"
    assert (profile_root / ".leaf.fork-claim").read_text(encoding="utf-8") == job_id
    assert second.status_code == 409


def test_profile_claim_recovery_uses_exact_watched_reconciliation(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    published: list[tuple[str, str]] = []
    finalizer = SimpleNamespace(
        args=("source-run", "profile;;fork;;leaf", "wepp-job"),
        func_name=(
            f"{fork_archive_routes._finish_fork_rq.__module__}."
            f"{fork_archive_routes._finish_fork_rq.__qualname__}"
        ),
        origin="default",
    )
    monkeypatch.setattr(
        fork_archive_routes.Job,
        "fetch",
        lambda job_id, connection: finalizer,
    )
    monkeypatch.setattr(
        fork_archive_routes,
        "reconcile_deferred_workflow",
        lambda job_id, **kwargs: SimpleNamespace(state="canceled"),
    )
    monkeypatch.setattr(
        fork_archive_routes.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    target_wd = tmp_path / "leaf"
    claim_path = tmp_path / ".leaf.fork-claim"
    claim_path.write_text("finalizer-job", encoding="utf-8")

    assert fork_archive_routes._recover_stale_profile_fork_claim(
        str(target_wd),
        "profile;;fork;;leaf",
        redis_conn=object(),
        lease_checkpoint=lambda: None,
    ) is True
    assert not claim_path.exists()
    assert published == [("source-run:fork", "rq:finalizer-job TRIGGER   fork FORK_FAILED")]


def test_target_replacement_reconciles_deferred_bootstrap_enable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_runid = "target-run"
    bootstrap_job = SimpleNamespace(
        func_name=(
            f"{fork_archive_routes.bootstrap_enable_rq.__module__}."
            f"{fork_archive_routes.bootstrap_enable_rq.__qualname__}"
        ),
        origin="default",
        args=(target_runid,),
        meta={},
        get_status=lambda refresh=True: "deferred",
    )
    inventories = iter((("bootstrap-job",), ()))
    monkeypatch.setattr(
        fork_archive_routes,
        "_target_executable_job_ids",
        lambda *_args, **_kwargs: next(inventories),
    )
    monkeypatch.setattr(
        fork_archive_routes.Job,
        "fetch",
        lambda *_args, **_kwargs: bootstrap_job,
    )
    reconciled: list[str] = []

    def reconcile(job_id, **kwargs):
        assert kwargs["association"](bootstrap_job) is True
        reconciled.append(job_id)
        return SimpleNamespace(state="canceled")

    monkeypatch.setattr(fork_archive_routes, "reconcile_deferred_workflow", reconcile)

    conflicts = fork_archive_routes._reconcile_target_deferred_jobs(
        object(), target_runid, lease_checkpoint=lambda: None
    )

    assert reconciled == ["bootstrap-job"]
    assert conflicts == ()


def test_archive_enqueues_job(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})

    constructor_calls = _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            json={"comment": "demo"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-99"
    assert constructor_calls[0][0] == ("fork-archive",)


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    (
        (fork_archive_routes.RqSubmissionConflict("busy"), 409, "conflict"),
        (OSError("lock storage offline"), 503, "service_unavailable"),
    ),
)
def test_archive_maps_admission_failures(
    error: Exception,
    status_code: int,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr(
        fork_archive_routes, "require_jwt", lambda _request, required_scopes=None: {}
    )
    monkeypatch.setattr(
        fork_archive_routes, "authorize_run_access", lambda _claims, _runid: None
    )
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda _runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda _path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda _runid: {})
    _stub_queue(monkeypatch)
    _stub_prep(monkeypatch)

    class FailingAdmission:
        def __enter__(self):
            raise error

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        fork_archive_routes,
        "rq_submission_lock",
        lambda *_args, **_kwargs: FailingAdmission(),
    )

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive", json={"comment": "demo"}
        )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_archive_clears_stale_job_id_when_lookup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(fork_archive_routes.Job, "fetch", lambda *args, **kwargs: (_ for _ in ()).throw(NoSuchJobError("missing")))
    monkeypatch.setattr(
        fork_archive_routes,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: SimpleNamespace(state="missing", job_ids=()),
    )

    _stub_queue(monkeypatch, job_id="job-100")
    prep = _stub_prep(monkeypatch, archive_job_id="stale-job")
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            json={"comment": "demo"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-100"
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "job-100"


def test_archive_returns_conflict_when_existing_job_is_running(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})

    class RunningJob:
        def get_status(self, refresh: bool = False):
            return "started"

    monkeypatch.setattr(fork_archive_routes.Job, "fetch", lambda *args, **kwargs: RunningJob())

    _stub_queue(monkeypatch, job_id="job-unused")
    prep = _stub_prep(monkeypatch, archive_job_id="active-job")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            json={"comment": "demo"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "An archive job is already running for this project"
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "active-job"


def test_archive_preserves_job_id_when_status_lookup_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(
        fork_archive_routes.Job,
        "fetch",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("redis unavailable")),
    )

    _stub_queue(monkeypatch, job_id="job-unused")
    prep = _stub_prep(monkeypatch, archive_job_id="active-job")

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            json={"comment": "demo"},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["message"] == "An archive job is already running for this project"
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "active-job"


def test_restore_clears_stale_job_id_before_enqueue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)
    (archives_dir / "snapshot.zip").write_bytes(b"PK\x05\x06" + (b"\x00" * 18))

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})
    monkeypatch.setattr(fork_archive_routes.Job, "fetch", lambda *args, **kwargs: (_ for _ in ()).throw(NoSuchJobError("missing")))
    monkeypatch.setattr(
        fork_archive_routes,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: SimpleNamespace(state="missing", job_ids=()),
    )

    constructor_calls = _stub_queue(monkeypatch, job_id="job-restore")
    prep = _stub_prep(monkeypatch, archive_job_id="stale-restore")
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/restore-archive",
            json={"archive_name": "snapshot.zip"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-restore"
    assert prep.clear_calls == 0
    assert prep.archive_job_id == "job-restore"
    assert constructor_calls[0][0] == ("fork-archive",)


@pytest.mark.parametrize(
    ("state", "cleanup_error", "expected_status", "should_delete"),
    (
        ("canceled", None, 200, True),
        ("active", None, 400, False),
        ("mismatch", None, 400, False),
        (None, RuntimeError("cleanup failed"), 500, False),
    ),
)
def test_delete_archive_reconciles_before_destructive_mutation(
    state: str | None,
    cleanup_error: Exception | None,
    expected_status: int,
    should_delete: bool,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    archives_dir = run_dir / "archives"
    archives_dir.mkdir(parents=True)
    archive_path = archives_dir / "snapshot.zip"
    archive_path.write_bytes(b"archive")
    events: list[str] = []

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda *_args: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda _runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", os.path.exists)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda _runid: {})
    monkeypatch.setattr(fork_archive_routes, "_archive_job_in_progress", lambda _prep: False)
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *_args: None)
    _stub_queue(monkeypatch)
    prep = _stub_prep(monkeypatch, archive_job_id="old-archive")
    prep.clear_archive_job_id = lambda: events.append("clear-receipt")

    def reconcile(*_args, **_kwargs):
        events.append("reconcile")
        if cleanup_error is not None:
            raise cleanup_error
        return state

    monkeypatch.setattr(fork_archive_routes, "_reconcile_archive_receipt", reconcile)
    real_remove = os.remove

    def remove(path):
        events.append("remove")
        real_remove(path)

    monkeypatch.setattr(fork_archive_routes.os, "remove", remove)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/delete-archive",
            json={"archive_name": "snapshot.zip"},
        )

    assert response.status_code == expected_status
    assert (not archive_path.exists()) is should_delete
    if should_delete:
        assert events == ["reconcile", "remove", "clear-receipt"]
    else:
        assert events == ["reconcile"]


def test_fork_existing_target_reconciles_and_records_before_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    (target_dir / "old.txt").write_text("old", encoding="utf-8")
    events: list[str] = []
    receipt_key = (
        f"{fork_archive_routes.FORK_DESTINATION_RECEIPT_KEY_PREFIX}:target-run"
    )

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_bearer_claims",
        lambda _request: {"token_class": "service", "sub": "operator"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        fork_archive_routes,
        "get_wd",
        lambda runid, prefer_active=True: (
            str(source_dir) if runid == "source-run" else str(target_dir)
        ),
    )
    monkeypatch.setattr(fork_archive_routes, "_exists", os.path.exists)
    monkeypatch.setattr(fork_archive_routes, "get_run_owners_lazy", lambda _runid: [])
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda _runid: {})
    monkeypatch.setattr(
        fork_archive_routes.Ron,
        "getInstance",
        lambda _wd: SimpleNamespace(config_stem="cfg"),
    )
    monkeypatch.setattr(fork_archive_routes, "new_rq_job_id", lambda: "replacement-fork")
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *_args: None)

    class Lease:
        def checkpoint(self): return None

    class Boundary:
        def __enter__(self): return Lease()
        def __exit__(self, *_args): return False

    monkeypatch.setattr(fork_archive_routes, "rq_submission_lock", lambda *_args, **_kwargs: Boundary())
    monkeypatch.setattr(fork_archive_routes, "run_replacement_guard", lambda *_args, **_kwargs: Boundary())

    class Redis:
        def __init__(self):
            self.values = {receipt_key: "old-fork"}
            self.hashes: dict[str, dict[str, str]] = {}
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def get(self, key): return self.values.get(key)
        def set(self, key, value, **_kwargs):
            self.values[key] = value
            if key == receipt_key and value == "replacement-fork": events.append("receipt")
            return True
        def hgetall(self, key): return self.hashes.get(key, {})
        def hset(self, key, mapping):
            self.hashes[key] = dict(mapping)
            events.append("planned")
            return len(mapping)

    redis_conn = Redis()
    monkeypatch.setattr(fork_archive_routes.redis, "Redis", lambda **_kwargs: redis_conn)
    old_root = SimpleNamespace(
        func_name=f"{fork_archive_routes.fork_rq.__module__}.{fork_archive_routes.fork_rq.__qualname__}",
        origin=fork_archive_routes.FORK_ARCHIVE_QUEUE,
        args=("source-run", "target-run"),
    )
    monkeypatch.setattr(fork_archive_routes.Job, "fetch", lambda *_args, **_kwargs: old_root)
    monkeypatch.setattr(
        fork_archive_routes,
        "reconcile_deferred_workflow",
        lambda *_args, **_kwargs: (events.append("reconcile") or SimpleNamespace(state="canceled", job_ids=("old-fork",))),
    )
    monkeypatch.setattr(
        fork_archive_routes,
        "reconcile_deferred_wepp_jobs",
        lambda *_args, **_kwargs: events.append("target-wepp-reconcile"),
    )
    monkeypatch.setattr(fork_archive_routes, "ensure_no_active_wepp_job", lambda *_args: None)
    monkeypatch.setattr(
        fork_archive_routes,
        "_reconcile_target_deferred_jobs",
        lambda *_args, **_kwargs: (events.append("target-reconcile") or ()),
    )

    class Prep:
        def get_rq_job_id(self, _key): return None
        def get_rq_job_ids(self): return {}
        def set_rq_job_id(self, _key, _job_id): events.append("source-hint")

    monkeypatch.setattr(fork_archive_routes.RedisPrep, "getInstance", lambda _wd: Prep())
    real_replace = os.replace

    def replace(source, destination):
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(fork_archive_routes.os, "replace", replace)

    class Queue:
        def __init__(self, *_args, **_kwargs): pass
        def enqueue_call(self, *_args, **kwargs):
            events.append("enqueue")
            return SimpleNamespace(id=kwargs["job_id"])

    monkeypatch.setattr(fork_archive_routes, "Queue", Queue)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/source-run/cfg/fork",
            headers={"Authorization": "Bearer token"},
            json={"target_runid": "target-run", "undisturbify": False},
        )

    assert response.status_code == 200
    assert response.json()["job_id"] == "replacement-fork"
    assert events.index("reconcile") < events.index("planned")
    assert events.index("planned") < events.index("replace")
    assert events.index("replace") < events.index("enqueue")
    assert not (target_dir / "old.txt").exists()
