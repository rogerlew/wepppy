import contextlib

import pytest

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


def _stub_prep(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPrep:
        def set_rq_job_id(self, *args, **kwargs) -> None:
            return None

        def get_archive_job_id(self) -> str | None:
            return None

        def set_archive_job_id(self, *args, **kwargs) -> None:
            return None

        def clear_archive_job_id(self) -> None:
            return None

    monkeypatch.setattr(fork_archive_routes.RedisPrep, "getInstance", lambda wd: DummyPrep())


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
        email = "mdobre@example.com"

    monkeypatch.setattr(
        fork_archive_routes,
        "_resolve_user_from_claims",
        lambda claims: (DummyUser(), None, None),
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
