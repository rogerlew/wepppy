from __future__ import annotations

import json
from types import SimpleNamespace
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
    assert ping_targets == ["http://localhost:9999/weppcloud"]
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
