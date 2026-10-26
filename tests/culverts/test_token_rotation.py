"""Credential lifecycle tests; filesystem and HTTP boundaries are exercised directly."""
from importlib.util import module_from_spec, spec_from_file_location
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]


def load(path):
    spec = spec_from_file_location(path.stem, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rotation():
    return load(ROOT / "scripts/culvert_token_rotation.py")


@pytest.fixture
def client():
    return load(ROOT / "docs/culvert-at-risk-integration/dev-package/scripts/weppcloud_token.py")


def token(rotation, **changes):
    now = int(time.time())
    claims = {**rotation.IDENTITY, "iat": now, "exp": now + rotation.TTL, "jti": "first"}
    claims.update(changes)
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return "eyJhbGciOiJIUzI1NiJ9." + body + ".c2ln"


@pytest.fixture
def token_file(tmp_path, rotation):
    directory = tmp_path / "private"
    rotation.private_directory(directory)
    return directory / "token"


def test_receiver_initial_install_and_same_process_client_reload(rotation, client, token_file, monkeypatch):
    monkeypatch.setattr(rotation, "verify", lambda value: None)
    monkeypatch.setenv("WEPPCLOUD_TOKEN_FILE", str(token_file))
    assert rotation.receiver("status", token_file) == {"installed": None}
    first, second = token(rotation), token(rotation, jti="second")
    rotation.receiver("install", token_file, first)
    assert client.load_weppcloud_token() == first
    rotation.receiver("install", token_file, second)
    assert client.load_weppcloud_token() == second
    assert token_file.with_name("previous").read_text().strip() == first
    assert token_file.stat().st_mode & 0o777 == 0o600
    assert token_file.with_name("previous").stat().st_mode & 0o777 == 0o600


def test_failed_verification_preserves_current(rotation, token_file, monkeypatch):
    original = token(rotation)
    rotation.atomic_write(token_file, original)
    def reject(value):
        raise rotation.RotationError("API rejected verification")
    monkeypatch.setattr(rotation, "verify", reject)
    with pytest.raises(rotation.RotationError):
        rotation.receiver("install", token_file, token(rotation, jti="new"))
    assert token_file.read_text() == original
    assert not token_file.with_name("previous").exists()


def test_replace_failure_preserves_current_and_backup(rotation, token_file, monkeypatch):
    original = token(rotation)
    rotation.atomic_write(token_file, original)
    monkeypatch.setattr(rotation, "verify", lambda value: None)
    replace = rotation.os.replace
    def fail_active(src, dst):
        if dst == token_file:
            raise OSError("simulated replace failure")
        return replace(src, dst)
    monkeypatch.setattr(rotation.os, "replace", fail_active)
    with pytest.raises(OSError):
        rotation.receiver("install", token_file, token(rotation, jti="new"))
    assert token_file.read_text() == original
    assert token_file.with_name("previous").read_text().strip() == original
    assert not list(token_file.parent.glob(".renew-*"))


@pytest.mark.parametrize("changes", [{"scope": "rq:enqueue"}, {"sub": "another"}, {"runs": ["x"]},
                                      {"exp": "bad"}, {"jti": ""}, {"aud": "other"}])
def test_wrong_identity_rejected_before_network(rotation, token_file, monkeypatch, changes):
    def forbidden(value):
        pytest.fail("invalid candidate reached network")
    monkeypatch.setattr(rotation, "verify", forbidden)
    with pytest.raises(rotation.RotationError):
        rotation.receiver("install", token_file, token(rotation, **changes))
    assert not token_file.exists()


@pytest.mark.parametrize("value", ["", "garbage", "a.@@@.b"])
def test_corrupt_installed_token_explicit_failure(rotation, token_file, value):
    rotation.atomic_write(token_file, value)
    with pytest.raises(rotation.RotationError):
        rotation.receiver("status", token_file)
    assert token_file.read_text() == value


def test_symlink_and_nonregular_targets_rejected(rotation, token_file, tmp_path):
    other = tmp_path / "other"
    other.write_text("do not change")
    token_file.symlink_to(other)
    with pytest.raises(OSError):
        rotation.receiver("status", token_file)
    assert other.read_text() == "do not change"
    token_file.unlink()
    os.mkfifo(token_file, 0o600)
    with pytest.raises(rotation.RotationError):
        rotation.receiver("status", token_file)


def test_expired_installed_token_is_inspectable_but_not_installable(rotation, token_file):
    now = int(time.time())
    old = token(rotation, iat=now - rotation.TTL - 100, exp=now - 100)
    rotation.atomic_write(token_file, old)
    assert rotation.receiver("status", token_file)["installed"]["exp"] < now
    with pytest.raises(rotation.RotationError, match="not currently valid"):
        rotation.verify(old)


def test_client_legacy_and_configured_file_failure(client, monkeypatch, tmp_path):
    monkeypatch.delenv("WEPPCLOUD_TOKEN_FILE", raising=False)
    monkeypatch.setenv("WEPPCLOUD_TOKEN", "legacy")
    assert client.load_weppcloud_token() == "legacy"
    monkeypatch.setenv("WEPPCLOUD_TOKEN_FILE", str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="cannot be read"):
        client.load_weppcloud_token()
    for value in ("", "a.b", "a..b", "a.@@@.b", " ", "x" * 16385):
        path = tmp_path / "bad"
        path.write_text(value)
        monkeypatch.setenv("WEPPCLOUD_TOKEN_FILE", str(path))
        with pytest.raises(ValueError):
            client.load_weppcloud_token()


def test_noop_force_and_expired_renewal(rotation, monkeypatch):
    active = token(rotation)
    state = {"value": rotation.metadata(active)}
    minted = []
    def remote(action, candidate=None):
        if action == "install":
            state["value"] = rotation.metadata(candidate)
        return {"installed": state["value"]}
    def issue(command):
        minted.append(command)
        return json.dumps({"token": token(rotation, jti=f"new-{len(minted)}")})
    monkeypatch.setattr(rotation, "remote", remote)
    monkeypatch.setattr(rotation, "run_private", issue)
    monkeypatch.setattr(rotation, "verify", lambda value: None)
    assert rotation.renew()["status"] == "not_due"
    assert not minted
    assert rotation.renew(True)["status"] == "renewed"
    state["value"]["exp"] = int(time.time()) - 1
    assert rotation.renew()["status"] == "renewed"
    assert len(minted) == 2


def test_unauthorized_command_and_secret_subprocess_error(rotation, tmp_path):
    env = {**os.environ, "SSH_ORIGINAL_COMMAND": "install; cat /etc/passwd"}
    result = subprocess.run([sys.executable, rotation.__file__, "receive"], env=env,
                            input="secret-marker", text=True, capture_output=True)
    assert result.returncode == 1 and "command denied" in result.stderr
    assert "secret-marker" not in result.stdout + result.stderr
    with pytest.raises(rotation.RotationError) as error:
        rotation.run_private([sys.executable, "-c", "import sys; print(sys.stdin.read()); sys.exit(1)"],
                             input_text="secret-marker")
    assert "secret-marker" not in str(error.value)


def test_real_http_validation_and_no_redirect(rotation, monkeypatch):
    observed = []
    class Handler(BaseHTTPRequestHandler):
        status = 400
        def do_POST(self):
            observed.append(self.path)
            self.send_response(self.status)
            if self.status == 302:
                self.send_header("Location", "/leaked")
            self.end_headers()
            self.wfile.write(json.dumps({"error": {"code": "validation_error"},
                "errors": [{"code": "missing_file", "path": "payload.zip"}]}).encode())
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(rotation, "ENDPOINT", f"http://127.0.0.1:{server.server_port}/verify")
    try:
        rotation.verify(token(rotation))
        Handler.status = 401
        with pytest.raises(rotation.RotationError, match="HTTP 401"):
            rotation.verify(token(rotation))
        Handler.status = 302
        with pytest.raises(rotation.RotationError, match="HTTP 302"):
            rotation.verify(token(rotation))
        assert observed == ["/verify", "/verify", "/verify"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_client_invalid_utf8(client, monkeypatch, tmp_path):
    path = tmp_path / "bad"
    path.write_bytes(b"\xff")
    monkeypatch.setenv("WEPPCLOUD_TOKEN_FILE", str(path))
    with pytest.raises(ValueError, match="cannot be read"):
        client.load_weppcloud_token()


def test_exact_renewal_boundary(rotation, monkeypatch):
    now = 1800000000
    monkeypatch.setattr(rotation.time, "time", lambda: now)
    current = rotation.metadata(token(rotation, exp=now + rotation.RENEW_BEFORE))
    monkeypatch.setattr(rotation, "remote", lambda action, candidate=None: {"installed": current})
    def attempted(command):
        raise rotation.RotationError("issuance attempted")
    monkeypatch.setattr(rotation, "run_private", attempted)
    with pytest.raises(rotation.RotationError, match="issuance attempted"):
        rotation.renew()
