from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask
import flask_login
from werkzeug.exceptions import Forbidden

from wepppy.weppcloud.utils import helpers


pytestmark = pytest.mark.unit


class DummyUser:
    def __init__(self, roles: set[str] | None = None) -> None:
        self._roles = roles or set()

    def has_role(self, role: str) -> bool:
        return role in self._roles


def test_authorize_strips_omni_suffix_for_parent_ownership_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    # authorize() requires login_manager to be configured.
    app.login_manager = SimpleNamespace()

    monkeypatch.setattr(flask_login, "current_user", DummyUser())
    wd_calls: list[str] = []

    def fake_get_wd(runid: str, **_kwargs: object) -> str:
        wd_calls.append(runid)
        return f"/tmp/{runid}"

    monkeypatch.setattr(helpers, "get_wd", fake_get_wd)

    owners_calls: list[str] = []

    def fake_get_run_owners(runid: str):
        owners_calls.append(runid)
        return []

    import wepppy.weppcloud.app as app_module

    monkeypatch.setattr(app_module, "get_run_owners", fake_get_run_owners)

    with app.test_request_context("/"):
        helpers.authorize("decimal-pleasing;;omni;;burned", "cfg")

    assert owners_calls == ["decimal-pleasing"]
    assert wd_calls == ["decimal-pleasing"]


def test_authorize_rejects_batch_runids_for_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.login_manager = SimpleNamespace()

    monkeypatch.setattr(flask_login, "current_user", DummyUser())

    # Ensure we fail before any WD/DB lookups.
    monkeypatch.setattr(helpers, "get_wd", lambda *_args, **_kwargs: pytest.fail("get_wd should not be called"))
    import wepppy.weppcloud.app as app_module

    monkeypatch.setattr(
        app_module,
        "get_run_owners",
        lambda *_args, **_kwargs: pytest.fail("get_run_owners should not be called"),
    )

    with app.test_request_context("/"):
        with pytest.raises(Forbidden):
            helpers.authorize("batch;;spring-2025;;run-001", "cfg")


def test_authorize_allows_batch_runids_for_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.login_manager = SimpleNamespace()

    monkeypatch.setattr(flask_login, "current_user", DummyUser(roles={"Admin"}))
    monkeypatch.setattr(helpers, "get_wd", lambda *_args, **_kwargs: pytest.fail("get_wd should not be called"))
    import wepppy.weppcloud.app as app_module

    monkeypatch.setattr(
        app_module,
        "get_run_owners",
        lambda *_args, **_kwargs: pytest.fail("get_run_owners should not be called"),
    )

    with app.test_request_context("/"):
        helpers.authorize("batch;;spring-2025;;run-001;;omni;;treated", "cfg")


def test_authorize_rejects_when_login_manager_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)

    monkeypatch.setattr(flask_login, "current_user", DummyUser())
    monkeypatch.setattr(helpers, "get_wd", lambda *_args, **_kwargs: pytest.fail("get_wd should not be called"))
    import wepppy.weppcloud.app as app_module

    monkeypatch.setattr(
        app_module,
        "get_run_owners",
        lambda *_args, **_kwargs: pytest.fail("get_run_owners should not be called"),
    )

    with app.test_request_context("/"):
        with pytest.raises(Forbidden):
            helpers.authorize("decimal-pleasing", "cfg")


def test_authorize_rejects_when_role_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenUser:
        def has_role(self, _role: str) -> bool:
            raise RuntimeError("broken role backend")

    app = Flask(__name__)
    app.login_manager = SimpleNamespace()

    monkeypatch.setattr(flask_login, "current_user", BrokenUser())
    monkeypatch.setattr(helpers, "get_wd", lambda *_args, **_kwargs: pytest.fail("get_wd should not be called"))
    import wepppy.weppcloud.app as app_module

    monkeypatch.setattr(
        app_module,
        "get_run_owners",
        lambda *_args, **_kwargs: pytest.fail("get_run_owners should not be called"),
    )

    with app.test_request_context("/"):
        with pytest.raises(Forbidden):
            helpers.authorize("decimal-pleasing", "cfg")
