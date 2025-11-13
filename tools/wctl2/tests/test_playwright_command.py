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
    context = _dummy_context({"PLAYWRIGHT_LOCAL_URL": "http://override.local"})
    assert playwright_cmd._resolve_base_url(context, "local", None) == "http://override.local"


def test_resolve_base_url_requires_custom_base() -> None:
    context = _dummy_context({})
    with pytest.raises(typer.Exit):
        playwright_cmd._resolve_base_url(context, "custom", None)


def test_run_path_disables_provisioning(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []
    captured_env: Dict[str, str] = {}
    ping_targets: List[str] = []

    def fake_ping(url: str) -> None:
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


def test_report_triggers_show_report_on_success(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str) -> None:
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

    def fake_ping(url: str) -> None:
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

    def fake_ping(url: str) -> None:
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

    def fake_ping(url: str) -> None:
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
        "urlopen",
        lambda request, timeout=0: _Response(),
    )

    # Should not raise
    playwright_cmd._ping_test_support("http://localhost:9999/weppcloud")


def test_ping_support_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        playwright_cmd.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("down")),
    )

    with pytest.raises(typer.Exit):
        playwright_cmd._ping_test_support("http://localhost:9999/weppcloud")


def test_report_path_without_report_opens_no_viewer(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: List[List[str]] = []

    def fake_ping(url: str) -> None:
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

    def fake_ping(url: str) -> None:
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
    assert not (run_root / "sandbox123").exists()


def test_profile_missing_capture(monkeypatch: pytest.MonkeyPatch, temp_project: Path) -> None:
    runner = CliRunner()

    def fake_ping(url: str) -> None:
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

    def fake_ping(url: str) -> None:
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
