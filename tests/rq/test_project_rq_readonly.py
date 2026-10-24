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
    (tmp_path / "demo").mkdir(exist_ok=True)
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


def test_readonly_drains_parent_and_nested_receipts_before_manifest(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from wepppy.query_engine.catalog_refresh import record_catalog_refresh, pending_catalog_requests
    from wepppy.query_engine.context import RunContext, refresh_run_context
    from wepppy.query_engine.catalog import load_catalog

    _configure_readonly_env(monkeypatch, tmp_path, _PrepStub())
    monkeypatch.setenv("QUERY_CATALOG_ROOTS_JSON", json.dumps([{
        "path": str(tmp_path), "namespace": "readonly-test", "layout": "flat",
        "coordination": str(tmp_path.parent / (tmp_path.name + "-coordination")),
    }]))
    root = tmp_path / "demo"
    child = root / "_pups/omni/scenarios/burned"
    for scope in (root, child):
        (scope / "soils").mkdir(parents=True)
        pq.write_table(pa.table({"value": [3]}), scope / "soils/soils.parquet")
        record_catalog_refresh(scope, "soils/soils.parquet")

    class Ron:
        is_child_run = False
        timed = staticmethod(lambda _label: contextlib.nullcontext())

        @property
        def readonly(self):
            return (root / "READONLY").exists()

        @readonly.setter
        def readonly(self, value):
            if value:
                assert all(not pending_catalog_requests(scope) for scope in (root, child))
                (root / "READONLY").touch()
            else:
                (root / "READONLY").unlink(missing_ok=True)

    monkeypatch.setattr(project_rq.Ron, "getInstance", lambda _wd: Ron())
    manifest = root / "manifest.json"
    def create_manifest(_wd):
        assert (root / "READONLY").exists()
        manifest.write_text("complete")
    monkeypatch.setattr(sys.modules["wepppy.microservices.browse"], "create_manifest", create_manifest)
    project_rq.set_run_readonly_rq("demo", readonly=True)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    for scope in (root, child):
        context = RunContext("demo", scope, None, load_catalog(scope))
        refresh_run_context(context, ["soils/soils.parquet"])
        assert context.catalog
    assert before == {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert manifest.read_text() == "complete"


def test_readonly_catalog_failure_preserves_writable_state_and_pending_intent(tmp_path, monkeypatch):
    import pyarrow as pa
    from wepppy.query_engine.catalog_refresh import record_catalog_refresh, pending_catalog_requests

    _configure_readonly_env(monkeypatch, tmp_path, _PrepStub())
    root = tmp_path / 'demo'
    (root / 'soils').mkdir()
    (root / 'soils/soils.parquet').write_bytes(b'not parquet')
    record_catalog_refresh(root, 'soils/soils.parquet')
    ron = project_rq.Ron.getInstance(str(root))
    with pytest.raises((pa.ArrowInvalid, ValueError)):
        project_rq.set_run_readonly_rq('demo', readonly=True)
    assert not ron.readonly
    assert not (root / 'READONLY').exists()
    assert not (root / 'manifest.json').exists()
    assert pending_catalog_requests(root)
