from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path
from typing import Any, Dict, List

import pytest
import typer
import urllib.error
from typer.testing import CliRunner

from tools.wctl2.__main__ import app
from tools.wctl2.commands import playwright as playwright_cmd


class _DummyResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def _dummy_context(values: Dict[str, str]) -> Any:
    return SimpleNamespace(env_value=lambda key, default=None: values.get(key, default))


def test_build_overrides_json_parses_values() -> None:
    payload = playwright_cmd._build_overrides_json(["general:dem_db=ned1/2016", "climate:source=daymet"])
    assert payload is not None
    parsed = json.loads(payload)
    assert parsed["general:dem_db"] == "ned1/2016"
    assert parsed["climate:source"] == "daymet"


def test_build_overrides_json_invalid_format_exits() -> None:
    with pytest.raises(typer.Exit):
        playwright_cmd._build_overrides_json(["bad-format"])


def test_resolve_base_url_prefers_override(monkeypatch: pytest.MonkeyPatch) -> None:
    context = _dummy_context({"PLAYWRIGHT_LOCAL_URL": "https://override.local"})
    assert playwright_cmd._resolve_base_url(context, "local", None) == "https://override.local"


def test_resolve_base_url_requires_custom_base() -> None:
    context = _dummy_context({})
    with pytest.raises(typer.Exit):
        playwright_cmd._resolve_base_url(context, "custom", None)


def test_run_path_disables_provisioning(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []
    captured_env: Dict[str, str] = {}
    ping_targets: List[str] = []

    def fake_ping(url: str, token: str) -> None:
        ping_targets.append(url)

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        captured_env.update(env or {})
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--base-url",
            "http://localhost:9999/weppcloud",
            "--run-path",
            "http://localhost:9999/weppcloud/runs/demo",
            "--suite",
            "controllers",
            "--workers",
            "3",
            "--headed",
        ],
    )

    assert result.exit_code == 0, result.output
    assert ping_targets
    assert ping_targets[-1] == "http://localhost:9999/weppcloud"
    assert calls == [
        ["npm", "run", "test:playwright", "--", "--project", "runs0", "--workers", "1", "--grep", "controller regression"]
    ]
    assert captured_env["SMOKE_RUN_PATH"] == "http://localhost:9999/weppcloud/runs/demo"
    assert captured_env["SMOKE_CREATE_RUN"] == "false"
    assert captured_env["SMOKE_HEADLESS"] == "false"
    assert captured_env["SMOKE_BASE_URL"] == "http://localhost:9999/weppcloud"
    assert captured_env["GL_DASHBOARD_URL"] == "http://localhost:9999/weppcloud/runs/demo/gl-dashboard"
    assert captured_env["PLAYWRIGHT_BROWSERS_PATH"] == "./.playwright-browsers"


def test_gl_dashboard_url_and_browsers_path(monkeypatch: pytest.MonkeyPatch, temp_project: Path) -> None:
    runner = CliRunner()
    captured_env: Dict[str, str] = {}
    calls: List[List[str]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        captured_env.update(env or {})
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--base-url",
            "http://localhost:8080/weppcloud",
            "--gl-dashboard-url",
            "http://example.test/weppcloud/runs/demo/gl-dashboard",
            "--browsers-path",
            "/tmp/pw-browsers",
            "--no-create-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls
    assert captured_env["GL_DASHBOARD_URL"] == "http://example.test/weppcloud/runs/demo/gl-dashboard"
    assert captured_env["PLAYWRIGHT_BROWSERS_PATH"] == "/tmp/pw-browsers"
    assert captured_env["SMOKE_CREATE_RUN"] == "false"
    assert captured_env["SMOKE_BASE_URL"] == "http://localhost:8080/weppcloud"
    assert "GL_DASHBOARD_PATH" not in captured_env


def test_report_triggers_show_report_on_success(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--base-url",
            "http://localhost:9999",
            "--report",
            "--report-path",
            "custom-report",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls[0][:3] == ["npm", "run", "test:playwright"]
    assert calls[1] == ["npx", "playwright", "show-report", "custom-report"]


def test_report_skips_show_report_on_failure(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        return _DummyResult(returncode=1)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--base-url",
            "http://localhost:9999",
            "--report",
        ],
    )

    assert result.exit_code == 1
    assert len(calls) == 1


def test_project_env_override(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    docker_env = temp_project / "docker" / ".env"
    docker_env.write_text(docker_env.read_text().replace("PLAYWRIGHT_DEV_PROJECT=runs0", "PLAYWRIGHT_DEV_PROJECT=runs1"))

    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "--project" in calls[0]
    project_index = calls[0].index("--project")
    assert calls[0][project_index + 1] == "runs1"


def test_explicit_project_wins(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--project",
            "customProject",
        ],
    )

    assert result.exit_code == 0, result.output
    project_index = calls[0].index("--project")
    assert calls[0][project_index + 1] == "customProject"


def test_ping_support_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        playwright_cmd.urllib.request,
        "build_opener",
        lambda *args: SimpleNamespace(open=lambda request, timeout=0: _Response()),
    )

    # Should not raise
    playwright_cmd._ping_test_support("http://localhost:9999/weppcloud", "test.token.signature")


def test_ping_support_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        playwright_cmd.urllib.request,
        "build_opener",
        lambda *args: SimpleNamespace(open=lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("down"))),
    )

    with pytest.raises(typer.Exit):
        playwright_cmd._ping_test_support("http://localhost:9999/weppcloud", "test.token.signature")


def test_report_path_without_report_opens_no_viewer(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        calls.append(cmd)
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--report-path",
            "telemetry/playwright-report",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert "--reporter" in calls[0]
    idx = calls[0].index("--output")
    assert calls[0][idx + 1] == "telemetry/playwright-report"


def _create_profile(tmp_path: Path, slug: str = "legacy-palouse") -> Path:
    profile_root = tmp_path / "profiles" / slug
    run_dir = profile_root / "run"
    capture_dir = profile_root / "capture"
    run_dir.mkdir(parents=True, exist_ok=True)
    capture_dir.mkdir(parents=True, exist_ok=True)
    payload = {"stage": "request", "endpoint": "/weppcloud/runs/skeletal-azalea/dev_cfg/view/overview"}
    (capture_dir / "events.jsonl").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    (run_dir / "active_config.txt").write_text("dev_cfg", encoding="utf-8")
    return profile_root


def test_profile_mode_sets_run_path(monkeypatch: pytest.MonkeyPatch, temp_project: Path) -> None:
    runner = CliRunner()
    subprocess_calls: List[Dict[str, Any]] = []
    ping_targets: List[str] = []

    def fake_ping(url: str, token: str) -> None:
        ping_targets.append(url)

    def fake_run(cmd, cwd=None, env=None):
        subprocess_calls.append({"cmd": cmd, "env": env})
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    profile_root = _create_profile(temp_project)
    playback_root = temp_project / "playback"
    run_root = playback_root / "runs"
    monkeypatch.setenv("PROFILE_PLAYBACK_ROOT", str(profile_root.parent))
    monkeypatch.setenv("PROFILE_PLAYBACK_BASE", str(playback_root))
    monkeypatch.setenv("PROFILE_PLAYBACK_RUN_ROOT", str(run_root))
    monkeypatch.setattr(playwright_cmd, "uuid4", lambda: SimpleNamespace(hex="sandbox123"))

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--suite",
            "mods-menu",
            "--profile",
            "legacy-palouse",
            "--base-url",
            "http://localhost:8080/weppcloud",
        ],
    )

    assert result.exit_code == 0, result.output
    assert ping_targets
    assert ping_targets[-1] == "http://localhost:8080/weppcloud"
    env = subprocess_calls[0]["env"]
    expected_base = "http://localhost:8080/weppcloud"
    assert env["SMOKE_RUN_PATH"] == f"{expected_base}/runs/profile;;tmp;;sandbox123/dev_cfg/"
    assert env["SMOKE_CREATE_RUN"] == "false"
    assert env["SMOKE_BASE_URL"] == expected_base
    assert env["GL_DASHBOARD_URL"] == f"{expected_base}/runs/profile;;tmp;;sandbox123/dev_cfg/gl-dashboard"
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == "./.playwright-browsers"
    assert not (run_root / "sandbox123").exists()


def test_profile_missing_capture(monkeypatch: pytest.MonkeyPatch, temp_project: Path) -> None:
    runner = CliRunner()

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        raise AssertionError("subprocess.run should not be called when profile prep fails")

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    profile_root = temp_project / "profiles" / "legacy-palouse"
    (profile_root / "run").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PROFILE_PLAYBACK_ROOT", str(profile_root.parent))

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--suite",
            "mods-menu",
            "--profile",
            "legacy-palouse",
        ],
    )

    assert result.exit_code != 0
    assert "Capture log missing" in result.output


def test_profile_keep_run_skips_cleanup(monkeypatch: pytest.MonkeyPatch, temp_project: Path) -> None:
    runner = CliRunner()
    subprocess_calls: List[Dict[str, Any]] = []

    def fake_ping(url: str, token: str) -> None:
        return None

    def fake_run(cmd, cwd=None, env=None):
        subprocess_calls.append({"cmd": cmd, "env": env})
        return _DummyResult(returncode=0)

    monkeypatch.setattr(playwright_cmd, "_ping_test_support", fake_ping)
    monkeypatch.setattr(playwright_cmd.subprocess, "run", fake_run)

    profile_root = _create_profile(temp_project)
    playback_root = temp_project / "playback"
    run_root = playback_root / "runs"
    monkeypatch.setenv("PROFILE_PLAYBACK_ROOT", str(profile_root.parent))
    monkeypatch.setenv("PROFILE_PLAYBACK_BASE", str(playback_root))
    monkeypatch.setenv("PROFILE_PLAYBACK_RUN_ROOT", str(run_root))
    monkeypatch.setattr(playwright_cmd, "uuid4", lambda: SimpleNamespace(hex="sand45"))

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-playwright",
            "--suite",
            "mods-menu",
            "--profile",
            "legacy-palouse",
            "--keep-run",
            "--base-url",
            "http://localhost:8080/weppcloud",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (run_root / "sand45").exists()


@pytest.fixture(autouse=True)
def automatic_support_mint(monkeypatch):
    monkeypatch.setattr(playwright_cmd, "mint_test_support_token", lambda ctx: "test.token.signature")


@pytest.mark.parametrize("url", ["http://remote.example", "https://user:pass@example.com", "file:///tmp/x"])
def test_unsafe_support_url_rejected_before_mint(monkeypatch, temp_project, url):
    monkeypatch.setattr(playwright_cmd, "mint_test_support_token", lambda ctx: pytest.fail("mint before URL validation"))
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), 'run-playwright', '--base-url', url])
    assert result.exit_code == 1


def test_mint_failure_stops_ping_and_npm(monkeypatch, temp_project):
    def fail(ctx):
        raise typer.Exit(1)
    monkeypatch.setattr(playwright_cmd, 'mint_test_support_token', fail)
    monkeypatch.setattr(playwright_cmd, '_ping_test_support', lambda *a: pytest.fail('ping after mint failure'))
    monkeypatch.setattr(playwright_cmd.subprocess, 'run', lambda *a, **kw: pytest.fail('npm after mint failure'))
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), 'run-playwright', '--base-url', 'http://localhost:9999'])
    assert result.exit_code == 1


def test_support_mint_captures_output_and_bounds_claims(monkeypatch, capsys, tmp_path):
    from tools.wctl2.commands.auth import mint_test_support_token
    seen = {}
    def run(args, **kwargs):
        seen.update(args=args, **kwargs)
        return SimpleNamespace(returncode=0, stdout='private.jwt.signature\n')
    monkeypatch.setattr(playwright_cmd.subprocess, 'run', run)
    ctx = SimpleNamespace(compose_base_args=lambda: [], project_dir=tmp_path, environment={})
    assert mint_test_support_token(ctx) == 'private.jwt.signature'
    assert seen['capture_output'] and '-T' in seen['args']
    assert '--expires-in 3600' in seen['args'][-1]
    assert '--audience weppcloud-test-support' in seen['args'][-1]
    assert '--scope test:support' in seen['args'][-1]
    assert 'private.jwt.signature' not in repr(seen)
    assert 'private.jwt.signature' not in capsys.readouterr().out


def test_ping_does_not_forward_bearer_on_redirect(monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path, self.headers.get('Authorization')))
            self.send_response(302)
            self.send_header('Location', '/unrelated')
            self.end_headers()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(typer.Exit):
            playwright_cmd._ping_test_support(f'http://127.0.0.1:{server.server_port}', 'test.token.signature')
        assert seen == [('/tests/api/ping', 'Bearer test.token.signature')]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize('returncode,stdout', [(1, 'private.jwt.signature'), (0, 'private output')])
def test_real_mint_failure_suppresses_output(monkeypatch, capsys, tmp_path, returncode, stdout):
    from tools.wctl2.commands.auth import mint_test_support_token
    monkeypatch.setattr(playwright_cmd.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stdout))
    ctx = SimpleNamespace(compose_base_args=lambda: [], project_dir=tmp_path, environment={})
    with pytest.raises(typer.Exit):
        mint_test_support_token(ctx)
    output = capsys.readouterr()
    assert stdout not in output.out + output.err
    assert 'signing configuration' in output.err


def test_only_test_child_receives_token(monkeypatch, temp_project):
    seen = []
    monkeypatch.setattr(playwright_cmd, '_ping_test_support', lambda *a: None)
    def run(args, **kwargs):
        seen.append((list(args), dict(kwargs['env'])))
        return _DummyResult()
    monkeypatch.setattr(playwright_cmd.subprocess, 'run', run)
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), 'run-playwright', '--base-url', 'http://localhost:9999', '--report'])
    assert result.exit_code == 0, result.output
    assert seen[0][1]['SMOKE_TEST_SUPPORT_TOKEN'] == 'test.token.signature'
    assert 'SMOKE_TEST_SUPPORT_TOKEN' not in seen[1][1]
    assert 'test.token.signature' not in result.output
    assert all('test.token.signature' not in repr(args) for args, env in seen)


def test_npm_failure_is_token_free(monkeypatch, temp_project):
    monkeypatch.setattr(playwright_cmd, '_ping_test_support', lambda *a: None)
    def run(*args, **kwargs):
        raise FileNotFoundError('test.token.signature')
    monkeypatch.setattr(playwright_cmd.subprocess, 'run', run)
    result = CliRunner().invoke(app, ['--project-dir', str(temp_project), 'run-playwright', '--base-url', 'http://localhost:9999'])
    assert result.exit_code == 1
    assert 'test.token.signature' not in result.output
    assert 'Cannot launch Playwright' in result.output
    assert app.pretty_exceptions_show_locals is False


def test_ping_ignores_ambient_proxy(monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    seen = []
    class Proxy(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('http_proxy', f'http://127.0.0.1:{server.server_port}')
    monkeypatch.setenv('no_proxy', '')
    monkeypatch.setenv('NO_PROXY', '')
    try:
        with pytest.raises(typer.Exit):
            playwright_cmd._ping_test_support('http://127.0.0.1:1', 'private.jwt.signature')
        assert seen == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
