from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

import pytest

import wepppy.rq.run_sync_rq as run_sync

pytestmark = pytest.mark.unit


def test_run_sync_rq_records_provenance(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(run_sync.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))

    job = SimpleNamespace(id="job-42", meta={})

    def _save() -> None:
        job.meta["_saved"] = True

    job.save = _save  # type: ignore[attr-defined]
    monkeypatch.setattr(run_sync, "get_current_job", lambda: job)
    monkeypatch.setattr(run_sync, "lock_statuses", lambda runid: {})

    spec_file = tmp_path / "spec.aria2"

    def fake_download_spec(url: str, headers: dict[str, str] | None, target_dir: Path | None = None) -> Path:
        assert headers == {}
        if target_dir is not None:
            target_dir.mkdir(parents=True, exist_ok=True)
            spec_path = target_dir / ".aria2c.spec"
            spec_path.write_text("url", encoding="utf-8")
            return spec_path
        spec_file.write_text("url", encoding="utf-8")
        return spec_file

    monkeypatch.setattr(run_sync, "_download_spec", fake_download_spec)

    def fake_aria2(
        input_file: Path,
        target_dir: Path,
        headers: dict[str, str] | None,
        status_callback=None,
    ) -> None:
        assert headers == {}
        target_dir.mkdir(parents=True, exist_ok=True)
        if status_callback:
            status_callback("aria2-progress")
        (target_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    monkeypatch.setattr(run_sync, "_run_aria2c", fake_aria2)
    monkeypatch.setattr(run_sync, "_verify_download", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_sync, "read_version", lambda path: 999)

    upserts: list[tuple] = []
    monkeypatch.setattr(
        run_sync,
        "_upsert_migration_row",
        lambda *args, **kwargs: upserts.append((args, kwargs)),
    )

    target_root = tmp_path / "runs"
    result = run_sync.run_sync_rq(
        "demo-run",
        "wepp.cloud",
        "owner@example.com",
        str(target_root),
        None,
    )

    # Runs are stored under {target_root}/{first_two_chars}/{runid}/
    run_root = target_root / "de" / "demo-run"
    provenance_path = run_root / ".provenance.json"
    assert provenance_path.exists()

    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert payload["runid"] == "demo-run"
    assert payload["config"] == "cfg"
    assert payload["source_host"] == "wepp.cloud"
    assert payload["owner_email"] == "owner@example.com"
    assert payload["version_at_pull"] == 999

    assert job.meta["runid"] == "demo-run"
    assert any("DOWNLOADING" in message for _, message in published)
    assert any("aria2-progress" in message for _, message in published)
    assert any("REGISTERED" in message for _, message in published)
    assert result["local_path"] == str(run_root)
    statuses = [args[7] for args, _ in upserts]
    assert "DOWNLOADING" in statuses
    assert "REGISTERED" in statuses


def test_run_sync_rq_uses_source_run_token_header(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    published: list[tuple[str, str]] = []
    monkeypatch.setattr(run_sync.StatusMessenger, "publish", lambda channel, message: published.append((channel, message)))

    class FakeRedisConn:
        def __init__(self) -> None:
            self.values = {"rq:run-sync:source-token:key-1": b"source-token-xyz"}
            self.getdel_calls: list[str] = []

        def getdel(self, key: str):
            self.getdel_calls.append(key)
            return self.values.pop(key, None)

    redis_conn = FakeRedisConn()
    job = SimpleNamespace(id="job-43", meta={"source_run_token_key": "rq:run-sync:source-token:key-1"}, connection=redis_conn)

    def _save() -> None:
        job.meta["_saved"] = True

    job.save = _save  # type: ignore[attr-defined]
    monkeypatch.setattr(run_sync, "get_current_job", lambda: job)
    monkeypatch.setattr(run_sync, "lock_statuses", lambda runid: {})

    header_calls: list[dict[str, str] | None] = []

    def fake_download_spec(url: str, headers: dict[str, str] | None, target_dir: Path | None = None) -> Path:
        header_calls.append(headers)
        assert target_dir is not None
        target_dir.mkdir(parents=True, exist_ok=True)
        spec_path = target_dir / ".aria2c.spec"
        spec_path.write_text("url", encoding="utf-8")
        return spec_path

    monkeypatch.setattr(run_sync, "_download_spec", fake_download_spec)

    def fake_aria2(
        input_file: Path,
        target_dir: Path,
        headers: dict[str, str] | None,
        status_callback=None,
    ) -> None:
        header_calls.append(headers)
        target_dir.mkdir(parents=True, exist_ok=True)
        if status_callback:
            status_callback("aria2-progress")
        (target_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    monkeypatch.setattr(run_sync, "_run_aria2c", fake_aria2)
    monkeypatch.setattr(run_sync, "_verify_download", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_sync, "read_version", lambda path: 999)
    monkeypatch.setattr(run_sync, "_upsert_migration_row", lambda *args, **kwargs: None)

    target_root = tmp_path / "runs"
    run_sync.run_sync_rq(
        "demo-run",
        "wepp.cloud",
        "owner@example.com",
        str(target_root),
        None,
    )

    assert header_calls == [
        {"Authorization": "Bearer source-token-xyz"},
        {"Authorization": "Bearer source-token-xyz"},
    ]
    assert redis_conn.getdel_calls == ["rq:run-sync:source-token:key-1"]


@pytest.mark.parametrize("exit_code", [0, 1])
def test_aria2_retains_early_errors_with_real_subprocess(monkeypatch, tmp_path, exit_code):
    executable = tmp_path / "aria2c"
    executable.write_text(
        "#!/bin/sh\n"
        "echo '[ERROR] Download aborted: climate.log'\n"
        "echo '  -> errorCode=8 Cannot resume download'\n"
        "i=0; while [ $i -lt 80 ]; do echo 'abc|OK | completed'; i=$((i+1)); done\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    (tmp_path / "spec").write_text("")
    messages = []
    if exit_code:
        with pytest.raises(RuntimeError) as error:
            run_sync._run_aria2c(tmp_path / "spec", tmp_path, None, messages.append)
        assert "Download aborted: climate.log" in str(error.value)
        assert "Cannot resume download" in str(error.value)
        assert "abc|OK" in str(error.value)
    else:
        run_sync._run_aria2c(tmp_path / "spec", tmp_path, None, messages.append)
    assert len(messages) == 82


@pytest.mark.parametrize("state", ["absent", "empty", "same", "changed", "partial", "orphan", "empty_source", "empty_manifest"])
def test_sync_replaces_with_real_aria2(tmp_path, state):
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    source = tmp_path / "source"
    source.mkdir()
    source_bytes = b"" if state == "empty_source" else b"current source"
    (source / "climate.log").write_bytes(source_bytes)
    target = tmp_path / "target"
    target.mkdir()
    payload = target / "climate.log"
    if state in {"empty", "same", "changed", "partial"}:
        payload.write_bytes({"empty": b"", "same": b"current source", "changed": b"outdated bytes", "partial": b"partial"}[state])
    control = target / "climate.log.aria2"
    if state in {"partial", "orphan"}:
        control.write_bytes(b"incompatible resume metadata")
    untouched = target / "unlisted"
    untouched.write_bytes(b"keep")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(source)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    spec = tmp_path / "manifest"
    spec.write_text(f"http://127.0.0.1:{server.server_port}/climate.log\n out=climate.log")
    if state == "empty_manifest":
        spec.write_text("")
    try:
        run_sync._run_aria2c(spec, target, None)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    if state == "empty_manifest":
        assert not payload.exists()
    else:
        assert payload.read_bytes() == source_bytes
    assert not control.exists()
    assert untouched.read_bytes() == b"keep"


@pytest.mark.parametrize("bad", ["../escape", "/absolute", "a", "a/b", "a.aria2", "a.aria2/b", ".aria2c.spec", "bad\x00name"])
def test_sync_invalid_manifest_preserves_files(tmp_path, bad):
    (tmp_path / "a").write_bytes(b"keep")
    spec = tmp_path / "manifest"
    spec.write_text(f"https://example.test/a\n out=a\nhttps://example.test/b\n out={bad}")
    with pytest.raises(ValueError):
        run_sync._prepare_sync_files(spec, tmp_path)
    assert (tmp_path / "a").read_bytes() == b"keep"


@pytest.mark.parametrize("name", ["b", "b.aria2", "parent"])
@pytest.mark.parametrize("kind", ["symlink", "directory"])
def test_sync_unsafe_targets_preserve_files(tmp_path, name, kind):
    root = tmp_path / "run"
    root.mkdir()
    (root / "a").write_bytes(b"keep")
    outside = tmp_path / "outside"
    outside.mkdir()
    path = root / name
    if kind == "symlink":
        path.symlink_to(outside)
    else:
        path.mkdir()
    destination = "parent/b" if name == "parent" else "b"
    spec = tmp_path / "manifest"
    spec.write_text(f"https://example.test/a\n out=a\nhttps://example.test/b\n out={destination}")
    if name == "parent" and kind == "directory":
        run_sync._prepare_sync_files(spec, root)
        assert not (root / "a").exists()
    else:
        with pytest.raises(ValueError):
            run_sync._prepare_sync_files(spec, root)
        assert (root / "a").read_bytes() == b"keep"


def test_sync_manifest_staging_does_not_follow_symlink(monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.write_bytes(b"keep")
    root = tmp_path / "run"
    root.mkdir()
    (root / ".aria2c.spec").symlink_to(outside)
    monkeypatch.setattr(run_sync.requests, "get", lambda *a, **k: SimpleNamespace(status_code=200, content=b""))
    spec = run_sync._download_spec("https://example.test/spec", None, root)
    run_sync._prepare_sync_files(spec, root)
    assert outside.read_bytes() == b"keep"
    assert spec.read_bytes() == b""


def test_sync_failure_does_not_register(monkeypatch, tmp_path):
    events = []
    statuses = []
    monkeypatch.setattr(run_sync, "get_current_job", lambda: None)
    monkeypatch.setattr(run_sync.StatusMessenger, "publish", lambda c, m: events.append(m))
    monkeypatch.setattr(run_sync, "_upsert_migration_row", lambda *a: statuses.append(a[7]))
    spec = tmp_path / "manifest"
    spec.write_text("https://example.test/a\n out=a\n dir=/unsafe")
    monkeypatch.setattr(run_sync, "_download_spec", lambda *a, **k: spec)
    with pytest.raises(ValueError, match="Unsupported"):
        run_sync.run_sync_rq("demo-run", "example.test", target_root=str(tmp_path))
    assert statuses == ["DOWNLOADING", "EXCEPTION"]
    assert not any("REGISTERED" in e or "COMPLETE" in e for e in events)


@pytest.mark.parametrize("record", [" out=b\n dir=/unsafe", " out=parent/b"])
def test_sync_invalid_directive_or_ancestor_preserves_files(tmp_path, record):
    (tmp_path / "a").write_bytes(b"keep")
    (tmp_path / "parent").write_bytes(b"not a directory")
    spec = tmp_path / "manifest"
    spec.write_text(f"https://example.test/a\n out=a\nhttps://example.test/b\n{record}")
    with pytest.raises(ValueError):
        run_sync._prepare_sync_files(spec, tmp_path)
    assert (tmp_path / "a").read_bytes() == b"keep"
