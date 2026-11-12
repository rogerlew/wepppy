from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from wepppy.weppcloud.utils import auth_tokens
import time

test_bp_module = import_module("wepppy.weppcloud.routes.test_bp")

pytestmark = pytest.mark.routes


def _configure_create_run_test_app(
    monkeypatch: pytest.MonkeyPatch,
    run_dir: Path,
) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["TEST_SUPPORT_ENABLED"] = True
    app.config["WEPPCLOUD_DEPLOYMENT_PROFILE"] = "test"
    app.register_blueprint(test_bp_module.test_bp)

    monkeypatch.setattr(
        test_bp_module,
        "current_user",
        SimpleNamespace(is_authenticated=True),
        raising=False,
    )
    monkeypatch.setattr(test_bp_module, "create_run_dir", lambda user: ("ab-run", str(run_dir)))
    captured_cfg: list[str] = []

    class DummyRon:
        def __init__(self, wd: str, cfg: str) -> None:
            self.wd = wd
            self.cfg = cfg
            captured_cfg.append(cfg)

        def config_get_bool(self, section: str, option: str, default: bool | None = None) -> bool:
            if section != "nodb" or option != "apply_nodir":
                return False if default is None else bool(default)
            if "?" not in self.cfg:
                return False if default is None else bool(default)
            _, query = self.cfg.split("?", 1)
            for pair in query.split("&"):
                if "=" not in pair:
                    continue
                key, value = pair.split("=", 1)
                if key != "nodb:apply_nodir":
                    continue
                return value.strip().lower().startswith("true")
            return False if default is None else bool(default)

    monkeypatch.setattr(test_bp_module, "Ron", DummyRon)
    monkeypatch.setattr(test_bp_module, "ensure_readme_on_create", lambda runid, config: None)
    monkeypatch.setattr(
        test_bp_module,
        "url_for_run",
        lambda endpoint, runid, config: f"/weppcloud/runs/{runid}/{config}",
    )
    app.config["_support_headers"] = _headers()
    app.config["_captured_ron_cfg"] = captured_cfg
    return app


def test_create_run_endpoint_does_not_seed_default_nodir_marker_without_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

    monkeypatch.delenv("WEPP_NODIR_DEFAULT_NEW_RUNS", raising=False)
    app = _configure_create_run_test_app(monkeypatch, run_dir)

    with app.test_client() as client:
        response = client.post(
            "/tests/api/create-run",
            headers=app.config["_support_headers"],
            json={"config": "dev_unit_1"},
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["run"]["runid"] == "ab-run"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_create_run_endpoint_does_not_seed_default_nodir_marker_with_opt_in_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

    monkeypatch.delenv("WEPP_NODIR_DEFAULT_NEW_RUNS", raising=False)
    app = _configure_create_run_test_app(monkeypatch, run_dir)

    with app.test_client() as client:
        response = client.post(
            "/tests/api/create-run",
            headers=app.config["_support_headers"],
            json={"config": "dev_unit_1", "overrides": {"nodb:apply_nodir": "true"}},
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["run"]["runid"] == "ab-run"
    assert app.config["_captured_ron_cfg"][-1] == "dev_unit_1.cfg?nodb:apply_nodir=true"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_create_run_endpoint_opt_in_respects_global_nodir_env_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "ab-run"
    run_dir.mkdir(parents=True, exist_ok=False)

    monkeypatch.setenv("WEPP_NODIR_DEFAULT_NEW_RUNS", "0")
    app = _configure_create_run_test_app(monkeypatch, run_dir)

    with app.test_client() as client:
        response = client.post(
            "/tests/api/create-run",
            headers=app.config["_support_headers"],
            json={"config": "dev_unit_1", "overrides": {"nodb:apply_nodir": "true"}},
        )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload is not None
    assert payload["run"]["runid"] == "ab-run"
    assert app.config["_captured_ron_cfg"][-1] == "dev_unit_1.cfg?nodb:apply_nodir=true"

    marker_path = run_dir / ".nodir" / "default_archive_roots.json"
    assert not marker_path.exists()


def test_malformed_body_before_project_creation(monkeypatch, tmp_path):
    run_dir = tmp_path / 'absent'
    app = _configure_create_run_test_app(monkeypatch, run_dir)
    def unexpected(*args, **kwargs):
        pytest.fail('malformed request reached project creation')
    monkeypatch.setattr(test_bp_module, 'create_run_dir', unexpected)
    response = app.test_client().post('/tests/api/create-run', data='{', headers=app.config['_support_headers'],
                                      content_type='application/json')
    assert response.status_code == 400
    assert response.json['error']['code'] == 'invalid_request'
    assert not run_dir.exists()


@pytest.fixture(autouse=True)
def support_signing_config(monkeypatch):
    for key in ("WEPP_AUTH_JWT_SECRETS_FILE", "WEPP_AUTH_JWT_SECRET_FILE", "WEPP_AUTH_JWT_DEFAULT_AUDIENCE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("WEPP_AUTH_JWT_SECRETS", "support-test-key")
    monkeypatch.setenv("WEPP_AUTH_JWT_SCOPE_SEPARATOR", ",")
    auth_tokens.get_jwt_config.cache_clear()
    yield
    auth_tokens.get_jwt_config.cache_clear()


def _headers(**kwargs):
    options = dict(audience="weppcloud-test-support", scopes=["other", "test:support"], expires_in=3600)
    options.update(kwargs)
    return {"Authorization": "Bearer " + auth_tokens.issue_token("test", **options)["token"]}


@pytest.mark.parametrize("credential,status", [
    ("missing", 401), ("malformed", 401), ("forged", 401), ("expired", 401),
    ("audience", 401), ("scope", 403), ("long", 401), ("no_exp", 401), ("nan", 401), ("huge", 401),
])
def test_denials_have_no_filesystem_effect(monkeypatch, tmp_path, credential, status):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="csrf-test", TEST_SUPPORT_ENABLED=True,
                      WEPPCLOUD_DEPLOYMENT_PROFILE="test")
    csrf = CSRFProtect(app)
    test_bp_module.register_csrf_exemptions(csrf)
    app.register_blueprint(test_bp_module.test_bp)
    victim = tmp_path / "retained"
    victim.mkdir()
    (victim / "sentinel").write_text("unchanged")
    monkeypatch.setenv("SMOKE_RUN_ROOT", str(tmp_path))
    def unexpected(*args, **kwargs):
        pytest.fail("denied request reached filesystem/payload boundary")
    monkeypatch.setattr(test_bp_module, "get_wd", unexpected)
    monkeypatch.setattr(test_bp_module, "_spawn_run", unexpected)
    headers = {
        "missing": {}, "malformed": {"Authorization": "Bearer a b"},
        "forged": {"Authorization": "Bearer forged.token.value"},
        "expired": _headers(issued_at=int(time.time())-4000),
        "audience": _headers(audience="wrong"), "scope": _headers(scopes=["other"]),
        "long": _headers(expires_in=3601),
    }
    claims = auth_tokens.issue_token("test", audience="weppcloud-test-support", scopes=["test:support"])["claims"]
    claims.pop("exp")
    headers["no_exp"] = {"Authorization": "Bearer " + auth_tokens.encode_jwt(claims, "support-test-key")}
    claims["exp"] = float('nan')
    headers["nan"] = {"Authorization": "Bearer " + auth_tokens.encode_jwt(claims, "support-test-key")}
    claims["iat"] = time.time() - 1
    claims["exp"] = 10**400
    headers["huge"] = {"Authorization": "Bearer " + auth_tokens.encode_jwt(claims, "support-test-key")}
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = "cookie-does-not-authorize"
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))
    for method, path in [('post', '/tests/api/create-run'), ('delete', '/tests/api/run/retained'), ('get', '/tests/api/ping')]:
        response = getattr(client, method)(path, headers=headers[credential], data='{', content_type='application/json')
        assert response.status_code == status
        assert response.json == {"error": "Forbidden" if status == 403 else "Unauthorized"}
        assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*')) == before
        assert (victim / "sentinel").read_text() == "unchanged"


def test_valid_bearer_without_csrf_deletes_actual_directory(monkeypatch, tmp_path):
    app = _configure_create_run_test_app(monkeypatch, tmp_path / "created")
    app.config['SECRET_KEY'] = 'csrf-test'
    csrf = CSRFProtect(app)
    test_bp_module.register_csrf_exemptions(csrf)
    victim = tmp_path / 'victim'
    victim.mkdir()
    (victim / 'sentinel').write_text('delete-me')
    monkeypatch.setattr(test_bp_module, 'get_wd', lambda *a, **kw: str(victim))
    client = app.test_client()
    assert client.post('/tests/api/create-run', json={'config': 'dev_unit_1'}, headers=_headers()).status_code == 201
    assert client.get('/tests/api/ping', headers=_headers()).status_code == 200
    assert client.delete('/tests/api/run/victim', headers=_headers()).status_code == 200
    assert not victim.exists()


@pytest.mark.parametrize("failure", ["busy", "permission", "retained"])
def test_cleanup_failure_is_explicit(monkeypatch, tmp_path, failure):
    import errno
    app = _configure_create_run_test_app(monkeypatch, tmp_path / "created")
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "sentinel").write_text("retained")
    monkeypatch.setattr(test_bp_module, "get_wd", lambda *a, **kw: str(victim))

    def fail_removal(path):
        if failure != "retained":
            raise OSError(errno.EBUSY if failure == "busy" else errno.EACCES, "blocked")

    monkeypatch.setattr(test_bp_module.shutil, "rmtree", fail_removal)
    response = app.test_client().delete("/tests/api/run/victim", headers=_headers())
    assert response.status_code == 500
    assert response.json == {"error": "Run cleanup failed"}
    assert (victim / "sentinel").read_text() == "retained"


def test_failed_creation_reports_incomplete_cleanup(monkeypatch, tmp_path):
    run = tmp_path / "created"
    run.mkdir()
    app = _configure_create_run_test_app(monkeypatch, run)

    def fail_creation(*args):
        raise ValueError("failed initialization")

    monkeypatch.setattr(test_bp_module, "Ron", fail_creation)
    monkeypatch.setattr(test_bp_module.shutil, "rmtree", lambda path: None)
    response = app.test_client().post("/tests/api/create-run", json={}, headers=_headers())
    assert response.status_code == 500
    assert response.json == {"error": "Run cleanup failed"}
    assert run.exists()


@pytest.mark.parametrize("error_number", [13, 116])
def test_cleanup_readback_error_cannot_prove_absence(monkeypatch, tmp_path, error_number):
    app = _configure_create_run_test_app(monkeypatch, tmp_path / "created")
    victim = tmp_path / "victim"
    victim.mkdir()
    original_lstat = Path.lstat

    def unavailable(self, *args, **kwargs):
        if self == victim:
            raise OSError(error_number, "readback unavailable")
        return original_lstat(self, *args, **kwargs)

    monkeypatch.setattr(test_bp_module.shutil, "rmtree", lambda path: None)
    monkeypatch.setattr(Path, "lstat", unavailable)
    with app.app_context(), pytest.raises(test_bp_module.RunCleanupError):
        test_bp_module._cleanup_run_directory(victim)
