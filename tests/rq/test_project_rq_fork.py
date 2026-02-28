from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


def _extract_excludes(cmd: list[str]) -> list[str]:
    return [cmd[index + 1] for index, token in enumerate(cmd[:-1]) if token == "--exclude"]


def test_build_fork_rsync_cmd_directory_mode_has_no_nodir_cache_exclude() -> None:
    import wepppy.rq.project_rq as project

    cmd = project._build_fork_rsync_cmd("/tmp/target/", undisturbify=False)
    excludes = _extract_excludes(cmd)

    assert ".nodir/cache/***" not in excludes
    assert "wepp/runs" not in excludes
    assert "wepp/output" not in excludes
    assert cmd[-2:] == [".", "/tmp/target/"]


def test_build_fork_rsync_cmd_adds_undisturbify_excludes() -> None:
    import wepppy.rq.project_rq as project

    cmd = project._build_fork_rsync_cmd("/tmp/target/", undisturbify=True)
    excludes = _extract_excludes(cmd)

    assert ".nodir/cache/***" not in excludes
    assert "wepp/runs" in excludes
    assert "wepp/output" in excludes
    assert cmd[-2:] == [".", "/tmp/target/"]


def test_clean_env_for_system_tools_uses_sanitized_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("PATH", "/custom/bin")

    env = project._clean_env_for_system_tools()

    assert env["PATH"] == "/usr/sbin:/usr/bin:/bin"
    assert env["LANG"] == "en_US.UTF-8"
    assert env["LC_ALL"] == "C"
    assert "/custom/bin" not in env["PATH"]


def test_fork_rq_undisturbify_enqueues_finish_job(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, _message: None)
    monkeypatch.setattr(
        project._fork_helpers,
        "prepare_fork_run",
        lambda *args, **kwargs: "/tmp/forked-run",
    )

    final_wepp_job = object()
    monkeypatch.setattr(project, "run_wepp_rq", lambda _runid: final_wepp_job)
    monkeypatch.setattr(project, "redis_connection_kwargs", lambda _db: {})

    class _RedisStub:
        def __init__(self, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

    monkeypatch.setattr(project.redis, "Redis", _RedisStub)

    enqueue_calls: list[tuple[object, list[str] | None, object]] = []

    class _QueueStub:
        def __init__(self, connection=None) -> None:
            self.connection = connection

        def enqueue(self, func, args=None, depends_on=None):
            enqueue_calls.append((func, args, depends_on))
            return SimpleNamespace(id="queued")

    monkeypatch.setattr(project, "Queue", _QueueStub)

    project.fork_rq("source-run", "new-run", undisturbify=True)

    assert len(enqueue_calls) == 1
    func, args, depends_on = enqueue_calls[0]
    assert func is project._finish_fork_rq
    assert args == ["source-run"]
    assert depends_on is final_wepp_job


def test_fork_rq_reports_ttl_import_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import wepppy.rq.project_rq as project

    published: list[str] = []
    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork-ttl"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, message: published.append(message))

    source_wd = tmp_path / "source"
    source_wd.mkdir(parents=True)
    target_wd = tmp_path / "target"

    monkeypatch.setattr(project, "get_wd", lambda _runid: str(source_wd))
    monkeypatch.setattr(project, "get_primary_wd", lambda _runid: str(target_wd))
    monkeypatch.setattr(project._fork_helpers.shutil, "which", lambda _name: "/usr/bin/rsync")
    monkeypatch.setattr(
        project._fork_helpers,
        "_run_rsync_with_live_output",
        lambda **_kwargs: None,
    )

    # Simulate missing initialize_ttl symbol at import time.
    monkeypatch.setitem(
        sys.modules,
        "wepppy.weppcloud.utils.run_ttl",
        types.ModuleType("wepppy.weppcloud.utils.run_ttl"),
    )

    project.fork_rq("source-run", "new-run", undisturbify=False)

    assert any("STATUS TTL initialization failed" in message for message in published)


def test_fork_rq_uses_wrapper_helper_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    import wepppy.rq.project_rq as project

    monkeypatch.setattr(project, "get_current_job", lambda: SimpleNamespace(id="job-fork-aliases"))
    monkeypatch.setattr(project.StatusMessenger, "publish", lambda _channel, _message: None)

    monkeypatch.setattr(
        project,
        "_build_fork_rsync_cmd",
        lambda run_right, undisturbify=False: ["patched-rsync", run_right, undisturbify],
    )
    monkeypatch.setattr(project, "_clean_env_for_system_tools", lambda: {"PATH": "patched"})

    captured: dict[str, object] = {}

    def _prepare(*_args, **kwargs):
        captured["cmd"] = kwargs["build_rsync_cmd"]("/tmp/target/", False)
        captured["env"] = kwargs["clean_env_for_system_tools"]()
        return "/tmp/forked-run"

    monkeypatch.setattr(project._fork_helpers, "prepare_fork_run", _prepare)

    project.fork_rq("source-run", "new-run", undisturbify=False)

    assert captured["cmd"] == ["patched-rsync", "/tmp/target/", False]
    assert captured["env"] == {"PATH": "patched"}
