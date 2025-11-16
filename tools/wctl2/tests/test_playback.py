from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from typer.testing import CliRunner

from tools.wctl2.__main__ import app


class _StreamResponse:
    def __init__(self, lines: Optional[list[str]] = None, status: int = 200, text: str = "") -> None:
        self._lines = lines or []
        self.status_code = status
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def iter_lines(self):
        for line in self._lines:
            yield line.encode("utf-8")

    def __enter__(self) -> "_StreamResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _JSONResponse:
    def __init__(self, payload: Dict[str, Any], status: int = 200, text: str = "") -> None:
        self._payload = payload
        self.status_code = status
        self.text = text or ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_run_test_profile_streams_output(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: Dict[str, Any] = {}

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["stream"] = stream
        return _StreamResponse(lines=["line-1", "line-2"])

    monkeypatch.setattr("tools.wctl2.commands.playback.requests.post", fake_post)

    result = runner.invoke(
        app,
        ["--project-dir", str(temp_project), "run-test-profile", "backed-globule", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "line-1" in result.stdout
    assert "line-2" in result.stdout
    assert "[wctl] POST http://127.0.0.1:8070/run/backed-globule" in result.output
    assert calls["url"] == "http://127.0.0.1:8070/run/backed-globule"
    assert calls["stream"] is True
    assert calls["json"]["dry_run"] is True
    assert calls["json"]["verbose"] is True
    assert calls["json"]["base_url"] == "http://weppcloud:8000/weppcloud"
    assert calls["headers"]["Content-Type"] == "application/json"


def test_run_test_profile_with_trace(monkeypatch: pytest.MonkeyPatch, temp_project: Path) -> None:
    coverage_file = temp_project / "wepppy" / "weppcloud" / "coverage.profile-playback.ini"
    coverage_file.parent.mkdir(parents=True, exist_ok=True)
    coverage_file.write_text("[run]\n")

    runner = CliRunner()
    calls: Dict[str, Any] = {}

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        calls["json"] = json
        return _StreamResponse(lines=["done"], status=200)

    monkeypatch.setattr("tools.wctl2.commands.playback.requests.post", fake_post)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-test-profile",
            "backed-globule",
            "--trace-code",
            "--coverage-dir",
            "/tmp/profile-coverage",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls["json"]["trace_code"] is True
    assert calls["json"]["coverage_dir"] == "/tmp/profile-coverage"
    assert calls["json"]["coverage_config"] == str(coverage_file.resolve())


def test_run_archive_profile_prints_json(monkeypatch: pytest.MonkeyPatch, temp_project) -> None:
    runner = CliRunner()
    calls: Dict[str, Any] = {}

    def fake_post(url, json=None, headers=None, stream=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        return _JSONResponse({"status": "ok", "profile": json["comment"] if "comment" in json else None})

    monkeypatch.setattr("tools.wctl2.commands.playback.requests.post", fake_post)

    result = runner.invoke(
        app,
        [
            "--project-dir",
            str(temp_project),
            "run-archive-profile",
            "backed-globule",
            "--archive-comment",
            "smoke test",
            "--timeout",
            "120",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.stdout
    assert calls["url"] == "http://127.0.0.1:8070/archive/backed-globule"
    assert calls["json"]["timeout_seconds"] == 120
    assert calls["json"]["comment"] == "smoke test"
