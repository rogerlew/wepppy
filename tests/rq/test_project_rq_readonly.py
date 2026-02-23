from __future__ import annotations

import contextlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
import redis

pytest.importorskip("flask")

import wepppy.rq.project_rq as project_rq

pytestmark = pytest.mark.unit


class _PrepStub:
    def __init__(
        self,
        *,
        set_exc: Exception | None = None,
        remove_exc: Exception | None = None,
        timestamp_exc: Exception | None = None,
    ) -> None:
        self.set_exc = set_exc
        self.remove_exc = remove_exc
        self.timestamp_exc = timestamp_exc

    def set_rq_job_id(self, _key: str, _job_id: str) -> None:
        if self.set_exc is not None:
            raise self.set_exc

    def remove_timestamp(self, _key: object) -> None:
        if self.remove_exc is not None:
            raise self.remove_exc

    def timestamp(self, _key: object) -> None:
        if self.timestamp_exc is not None:
            raise self.timestamp_exc


class _RonStub:
    def __init__(self) -> None:
        self.readonly = False
        self.is_child_run = True

    def timed(self, _label: str):
        return contextlib.nullcontext()


def _configure_readonly_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prep: _PrepStub,
):
    published: list[tuple[str, str]] = []
    published_commands: list[tuple[str, str]] = []

    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="job-readonly"))
    monkeypatch.setattr(project_rq, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish_command",
        lambda runid, message: published_commands.append((runid, message)),
    )
    monkeypatch.setattr(project_rq.RedisPrep, "tryGetInstance", lambda _wd: prep)

    ron_instance = _RonStub()
    monkeypatch.setattr(project_rq.Ron, "getInstance", lambda _wd: ron_instance)

    browse_module = types.ModuleType("wepppy.microservices.browse")
    browse_module.MANIFEST_FILENAME = "manifest.json"
    browse_module.create_manifest = lambda _wd: None
    browse_module.remove_manifest = lambda _wd: None
    monkeypatch.setitem(sys.modules, "wepppy.microservices.browse", browse_module)

    ttl_module = types.ModuleType("wepppy.weppcloud.utils.run_ttl")
    ttl_module.sync_ttl_policy = lambda _wd, touched_by=None: None
    monkeypatch.setitem(sys.modules, "wepppy.weppcloud.utils.run_ttl", ttl_module)

    return published, published_commands


def test_set_run_readonly_rq_swallow_expected_prep_bookkeeping_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prep = _PrepStub(
        remove_exc=redis.exceptions.ConnectionError("redis unavailable"),
        timestamp_exc=OSError("write failed"),
    )
    published, published_commands = _configure_readonly_env(monkeypatch, tmp_path, prep)

    project_rq.set_run_readonly_rq("demo", readonly=True)

    assert any("COMPLETED set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)
    assert any("manifest.json skipped (child run)" in message for _, message in published_commands)
    assert not any("EXCEPTION set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)


def test_set_run_readonly_rq_swallow_expected_prep_json_decode_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prep = _PrepStub(remove_exc=json.JSONDecodeError("bad json", "{}", 0))
    published, _published_commands = _configure_readonly_env(monkeypatch, tmp_path, prep)

    project_rq.set_run_readonly_rq("demo", readonly=True)

    assert any("COMPLETED set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)
    assert not any("EXCEPTION set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)


def test_set_run_readonly_rq_swallow_expected_prep_set_job_id_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prep = _PrepStub(set_exc=redis.exceptions.RedisError("prep redis error"))
    published, published_commands = _configure_readonly_env(monkeypatch, tmp_path, prep)

    project_rq.set_run_readonly_rq("demo", readonly=True)

    assert any("COMPLETED set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)
    assert any("manifest.json skipped (child run)" in message for _, message in published_commands)
    assert not any("EXCEPTION set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)


def test_set_run_readonly_rq_publishes_exception_for_unexpected_prep_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prep = _PrepStub(set_exc=RuntimeError("prep failure"))
    published, published_commands = _configure_readonly_env(monkeypatch, tmp_path, prep)

    with pytest.raises(RuntimeError, match="prep failure"):
        project_rq.set_run_readonly_rq("demo", readonly=True)

    assert any("EXCEPTION set_run_readonly_rq(demo, readonly=True)" in message for _, message in published)
    assert any("manifest.json creation failed" in message for _, message in published_commands)
