from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.project_bp as project_module

RUN_ID = "team-run"
CONFIG = "cfg"

pytestmark = pytest.mark.unit


class ComparableAttribute:
    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.name)

    def __eq__(self, other):  # pragma: no cover - simple data holder
        return ("eq", self.name, other)


class Query:
    def __init__(self, accessor):
        self._accessor = accessor
        self._filtered = list(accessor())

    def filter(self, expr):
        items = list(self._accessor())
        if isinstance(expr, tuple) and len(expr) == 3 and expr[0] == "eq":
            _, attr, value = expr
            items = [item for item in items if getattr(item, attr) == value]
        elif callable(expr):
            items = [item for item in items if expr(item)]
        elif expr is True:
            items = list(items)
        elif expr is False:
            items = []
        else:
            items = [item for item in items if getattr(item, "runid", None) == expr]
        self._filtered = items
        return self

    def first(self):
        return self._filtered[0] if self._filtered else None


class QueryDescriptor:
    def __init__(self, accessor):
        self._accessor = accessor

    def __get__(self, instance, owner):
        return Query(self._accessor)


class DummyRun:
    def __init__(self, runid: str, config: str) -> None:
        self.runid = runid
        self.config = config
        self.members = []


class DummyUser:
    def __init__(self, user_id: int, email: str, first_name: str = "User", last_name: str = "Example") -> None:
        self.id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.runs = []


@pytest.fixture()
def team_client(monkeypatch: pytest.MonkeyPatch, tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(project_module.project_bp)

    monkeypatch.setattr("flask_login.utils._get_user", lambda: SimpleNamespace(is_authenticated=True), raising=False)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()

    monkeypatch.setattr(project_module, "authorize", lambda runid, config: None)

    class DummyContext:
        def __init__(self, root_path: str) -> None:
            self.active_root = root_path

    monkeypatch.setattr(project_module, "load_run_context", lambda runid, config: DummyContext(str(run_dir)))

    owners = []
    user_store = []
    run_store = []

    class DummyRunModel:
        runid = ComparableAttribute("runid")
        query = QueryDescriptor(lambda: run_store)

    class DummyUserModel:
        id = ComparableAttribute("id")
        email = ComparableAttribute("email")
        query = QueryDescriptor(lambda: user_store)

    class UserDatastoreStub:
        def __init__(self) -> None:
            self.added = []
            self.removed = []

        def find_user(self, email: str):
            email_lower = email.lower()
            for user in user_store:
                if user.email.lower() == email_lower:
                    return user
            return None

        def create_run(self, runid: str, config: str, user: DummyUser):
            run = DummyRun(runid, config)
            run_store.append(run)
            if user not in owners:
                owners.append(user)
            if run not in user.runs:
                user.runs.append(run)
            if user not in run.members:
                run.members.append(user)
            return run

        def add_run_to_user(self, user: DummyUser, run: DummyRun) -> None:
            if run not in run_store:
                run_store.append(run)
            if user not in run.members:
                run.members.append(user)
            if run not in user.runs:
                user.runs.append(run)
            self.added.append((user, run))

        def remove_run_to_user(self, user: DummyUser, run: DummyRun) -> None:
            if run in user.runs:
                user.runs.remove(run)
            if user in run.members:
                run.members.remove(user)
            self.removed.append((user, run))

    user_datastore = UserDatastoreStub()

    monkeypatch.setattr(project_module, "get_user_models", lambda: (DummyRunModel, DummyUserModel, user_datastore))
    monkeypatch.setattr(project_module, "get_run_owners_lazy", lambda runid: owners)

    run = DummyRun(RUN_ID, CONFIG)
    run_store.append(run)

    owner_user = DummyUser(1, "owner@example.com", "Owner", "One")
    owner_user.runs.append(run)
    run.members.append(owner_user)
    user_store.append(owner_user)
    owners.append(owner_user)

    with app.test_client() as client:
        def create_user(user_id: int, email: str, first_name: str = "User", last_name: str = "Example") -> DummyUser:
            user = DummyUser(user_id, email, first_name, last_name)
            user_store.append(user)
            return user

        yield {
            "client": client,
            "owners": owners,
            "user_store": user_store,
            "run_store": run_store,
            "user_datastore": user_datastore,
            "run": run,
            "create_user": create_user,
        }


def test_adduser_accepts_json_payload(team_client):
    client = team_client["client"]
    create_user = team_client["create_user"]
    run = team_client["run"]
    datastore = team_client["user_datastore"]

    collaborator = create_user(2, "collab@example.com", "Collab", "Example")

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/adduser/",
        json={"email": "collab@example.com"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"user_id": 2, "email": "collab@example.com"}}
    assert datastore.added == [(collaborator, run)]
    assert run in collaborator.runs
    assert collaborator in run.members


def test_adduser_returns_already_member_flag_for_existing_owner(team_client):
    client = team_client["client"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/adduser/",
        json={"email": "owner@example.com"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "Success": True,
        "Content": {"already_member": True, "user_id": 1, "email": "owner@example.com"},
    }


def test_adduser_requires_email(team_client):
    client = team_client["client"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/adduser/",
        json={"email": "   "},
    )

    payload = response.get_json()
    assert payload["Success"] is False
    assert payload["Error"] == "Email address is required."


def test_adduser_errors_when_user_unknown(team_client):
    client = team_client["client"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/adduser/",
        json={"email": "missing@example.com"},
    )

    payload = response.get_json()
    assert payload["Success"] is False
    assert payload["Error"] == "missing@example.com does not have a WeppCloud account."


def test_removeuser_accepts_json_payload(team_client):
    client = team_client["client"]
    create_user = team_client["create_user"]
    owners = team_client["owners"]
    run = team_client["run"]
    datastore = team_client["user_datastore"]

    collaborator = create_user(3, "collab2@example.com")
    owners.append(collaborator)
    datastore.add_run_to_user(collaborator, run)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/removeuser/",
        json={"user_id": 3},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"user_id": 3}}
    assert datastore.removed == [(collaborator, run)]
    assert run not in collaborator.runs
    assert collaborator not in run.members


def test_removeuser_reports_already_removed_when_not_member(team_client):
    client = team_client["client"]
    create_user = team_client["create_user"]
    owners = team_client["owners"]

    collaborator = create_user(4, "absent@example.com")
    owners.append(collaborator)

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/removeuser/",
        json={"user_id": 4},
    )

    payload = response.get_json()
    assert payload == {"Success": True, "Content": {"already_removed": True, "user_id": 4}}


def test_removeuser_validates_user_id_type(team_client):
    client = team_client["client"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/removeuser/",
        json={"user_id": "abc"},
    )

    payload = response.get_json()
    assert payload["Success"] is False
    assert payload["Error"] == "user_id must be an integer."


def test_removeuser_rejects_unknown_user(team_client):
    client = team_client["client"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/removeuser/",
        json={"user_id": 999},
    )

    payload = response.get_json()
    assert payload["Success"] is False
    assert payload["Error"] == "User 999 not found."


def test_removeuser_rejects_non_collaborator(team_client):
    client = team_client["client"]
    create_user = team_client["create_user"]

    outsider = create_user(5, "outsider@example.com")

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/removeuser/",
        json={"user_id": 5},
    )

    payload = response.get_json()
    assert payload["Success"] is False
    assert payload["Error"] == "User is not a collaborator on this project."
