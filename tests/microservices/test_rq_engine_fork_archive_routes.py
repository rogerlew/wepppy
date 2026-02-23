import contextlib

import pytest
from rq.exceptions import NoSuchJobError

TestClient = pytest.importorskip("fastapi.testclient").TestClient

import wepppy.microservices.rq_engine as rq_engine
from wepppy.microservices.rq_engine import fork_archive_routes
from wepppy.weppcloud.utils import helpers as helpers_utils
from wepppy.weppcloud.utils import runid as runid_utils


pytestmark = pytest.mark.microservice


def _stub_queue(monkeypatch: pytest.MonkeyPatch, *, job_id: str = "job-123") -> None:
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

        def close(self) -> None:
            return None

    monkeypatch.setattr(fork_archive_routes, "Queue", DummyQueue)
    monkeypatch.setattr(fork_archive_routes.redis, "Redis", lambda **kwargs: DummyRedis())


def _stub_prep(
    monkeypatch: pytest.MonkeyPatch,
    *,
    archive_job_id: str | None = None,
):
    class DummyPrep:
        def __init__(self) -> None:
            self.archive_job_id = archive_job_id
            self.clear_calls = 0

        def set_rq_job_id(self, *args, **kwargs) -> None:
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

    monkeypatch.setattr(
        helpers_utils,
        "get_user_models",
        lambda: (object(), DummyUserModel, user_datastore),
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
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
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
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
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
    assert response.json() == {
        "error": {
            "message": "Invalid target_runid",
            "code": "validation_error",
            "details": "Invalid target_runid",
        }
    }


def test_fork_enqueues_job(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
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

    _stub_queue(monkeypatch, job_id="job-42")
    _stub_prep(monkeypatch)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/fork",
            headers={"Authorization": "Bearer token"},
            data={"undisturbify": "true"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-42"
    assert payload["new_runid"] == "new-run"
    assert payload["undisturbify"] is True


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
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
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
        lambda: (object(), DummyUserModel, user_datastore),
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
        lambda request: {"token_class": "user", "email": "mdobre@example.com"},
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
        lambda request: {"token_class": "user", "email": "mdobre@example.com"},
    )
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
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


def test_archive_enqueues_job(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(fork_archive_routes, "require_jwt", lambda request, required_scopes=None: {})
    monkeypatch.setattr(fork_archive_routes, "authorize_run_access", lambda claims, runid: None)
    monkeypatch.setattr(fork_archive_routes, "get_wd", lambda runid: str(run_dir))
    monkeypatch.setattr(fork_archive_routes, "_exists", lambda path: True)
    monkeypatch.setattr(fork_archive_routes, "lock_statuses", lambda runid: {})

    _stub_queue(monkeypatch, job_id="job-99")
    _stub_prep(monkeypatch)
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            headers={"Authorization": "Bearer token"},
            json={"comment": "demo"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-99"


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

    _stub_queue(monkeypatch, job_id="job-100")
    prep = _stub_prep(monkeypatch, archive_job_id="stale-job")
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/archive",
            headers={"Authorization": "Bearer token"},
            json={"comment": "demo"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-100"
    assert prep.clear_calls == 1
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
            headers={"Authorization": "Bearer token"},
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
            headers={"Authorization": "Bearer token"},
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

    _stub_queue(monkeypatch, job_id="job-restore")
    prep = _stub_prep(monkeypatch, archive_job_id="stale-restore")
    monkeypatch.setattr(fork_archive_routes.StatusMessenger, "publish", lambda *args, **kwargs: None)

    with TestClient(rq_engine.app) as client:
        response = client.post(
            "/api/runs/run-1/cfg/restore-archive",
            headers={"Authorization": "Bearer token"},
            json={"archive_name": "snapshot.zip"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "job-restore"
    assert prep.clear_calls == 1
    assert prep.archive_job_id == "job-restore"
