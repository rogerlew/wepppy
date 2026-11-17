from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

import wepppy.rq.project_rq as project_rq

pytestmark = pytest.mark.unit


def _stub_user_models(monkeypatch: pytest.MonkeyPatch, runid: str):
    class DummyRun:
        runid = "runid"

        def __init__(self, runid_value: str) -> None:
            self.runid = runid_value

    dummy_run = DummyRun(runid)

    class DummyQuery:
        def __init__(self, run: DummyRun) -> None:
            self._run = run

        def filter(self, *args, **kwargs) -> "DummyQuery":
            return self

        def first(self) -> DummyRun:
            return self._run

    DummyRun.query = DummyQuery(dummy_run)

    class DummyUserDatastore:
        def __init__(self) -> None:
            self.deleted: list[DummyRun] = []

        def delete_run(self, run: DummyRun) -> None:
            self.deleted.append(run)

    user_datastore = DummyUserDatastore()

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["get_user_models"])
    monkeypatch.setattr(helpers, "get_user_models", lambda: (DummyRun, None, user_datastore))

    return user_datastore, dummy_run


def _stub_delete_environment(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runid: str,
    job_id: str,
    errno_value: int,
) -> tuple[list[str], list[dict[str, object]], object]:
    job = SimpleNamespace(id=job_id)
    monkeypatch.setattr(project_rq, "get_current_job", lambda: job)

    published: list[str] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append(message),
    )

    def fake_rmtree(_path: Path) -> None:
        raise OSError(errno_value, "busy")

    monkeypatch.setattr(project_rq.shutil, "rmtree", fake_rmtree)
    monkeypatch.setattr(project_rq.time, "sleep", lambda _seconds: None)

    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda _runid: [])
    monkeypatch.setattr(project_rq, "clear_locks", lambda _runid: None)
    import flask

    monkeypatch.setattr(flask, "has_app_context", lambda: True)

    mark_calls: list[dict[str, object]] = []

    def fake_mark_delete_state(
        wd: str,
        state: str,
        *,
        db_cleared: bool | None = None,
        touched_by: str = "delete",
    ) -> None:
        mark_calls.append({
            "wd": wd,
            "state": state,
            "db_cleared": db_cleared,
            "touched_by": touched_by,
        })

    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["mark_delete_state"])
    monkeypatch.setattr(ttl_module, "mark_delete_state", fake_mark_delete_state)

    user_datastore, _dummy_run = _stub_user_models(monkeypatch, runid)
    return published, mark_calls, user_datastore


def test_delete_run_rq_marks_ttl_when_rmtree_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runid = "test-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True)
    (run_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    published, mark_calls, user_datastore = _stub_delete_environment(
        monkeypatch,
        runid=runid,
        job_id="job-1",
        errno_value=project_rq.errno.EBUSY,
    )

    project_rq.delete_run_rq(runid, wd=str(run_dir), delete_files=True)

    assert len(user_datastore.deleted) == 1
    assert run_dir.exists()
    assert any(call["state"] == "queued" for call in mark_calls)
    assert any(call["db_cleared"] is True for call in mark_calls)
    assert not any("delete deferred" in message for message in published)
    assert not any("delete retry" in message for message in published)
    assert not any("delete failed" in message for message in published)


def test_delete_run_rq_reports_non_retryable_delete_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runid = "test-run-hard-fail"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True)
    (run_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    published, mark_calls, user_datastore = _stub_delete_environment(
        monkeypatch,
        runid=runid,
        job_id="job-1b",
        errno_value=project_rq.errno.EPERM,
    )

    project_rq.delete_run_rq(runid, wd=str(run_dir), delete_files=True)

    assert len(user_datastore.deleted) == 1
    assert run_dir.exists()
    assert any(call["touched_by"] == "delete_failed" for call in mark_calls)
    assert any("delete failed" in message for message in published)
    assert any("delete deferred" in message for message in published)


def test_delete_run_holds_vector_scope_and_rebuilds_ledger_after_durable_removal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from wepppy.rq import project_rq_delete as delete_module

    runid = "retained-run"
    run_dir = tmp_path / runid
    (run_dir / "roads" / "vector_upload_attempts" / "attempt").mkdir(parents=True)
    (run_dir / "roads" / "vector_upload_attempts" / "attempt" / "normalization.json").write_text("{}")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "delete-test")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    monkeypatch.setattr(project_rq, "get_current_job", lambda: SimpleNamespace(id="delete-job"))
    monkeypatch.setattr(project_rq.StatusMessenger, "publish", lambda *_args: None)
    monkeypatch.setattr(project_rq, "clear_nodb_file_cache", lambda _runid: [])
    monkeypatch.setattr(project_rq, "clear_locks", lambda _runid: None)
    monkeypatch.setattr("wepppy.weppcloud.utils.run_ttl.mark_delete_state", lambda *_args, **_kwargs: None)
    import flask
    monkeypatch.setattr(flask, "has_app_context", lambda: True)
    _stub_user_models(monkeypatch, runid)
    events: list[str] = []

    class Lease:
        def assert_owned(self) -> None:
            events.append("assert")

        def release(self) -> None:
            events.append("release")

    monkeypatch.setattr(delete_module, "RedisScopeLeaseFactory", lambda: lambda scope: events.append(scope) or Lease())
    monkeypatch.setattr(
        delete_module,
        "acquire_retention_maintenance_lease",
        lambda: Lease(),
    )
    obligation = tmp_path / ".vector-upload-rebuild-pending" / "test.json"
    monkeypatch.setattr(
        delete_module,
        "begin_retention_rebuild_obligation",
        lambda *_args, **_kwargs: events.append("obligation:begin") or obligation,
    )
    monkeypatch.setattr(
        delete_module,
        "complete_retention_rebuild_obligation",
        lambda path: events.append(f"obligation:complete:{path.name}"),
    )
    monkeypatch.setattr(
        delete_module,
        "reconcile_retention",
        lambda root, **kwargs: events.append(f"rebuild:{root}") or {},
    )

    project_rq.delete_run_rq(runid, wd=str(run_dir), delete_files=True)

    assert not run_dir.exists()
    assert events[0] == f"run:{runid}"
    assert f"rebuild:{tmp_path}" in events
    assert "obligation:complete:test.json" in events


def test_delete_run_releases_global_maintenance_when_project_scope_acquisition_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from wepppy.rq import project_rq_delete as delete_module

    runid = "scope-acquisition-failure"
    run_dir = tmp_path / runid
    (run_dir / "roads" / "vector_upload_attempts").mkdir(parents=True)
    _stub_delete_environment(
        monkeypatch,
        runid=runid,
        job_id="delete-scope-failure",
        errno_value=project_rq.errno.EBUSY,
    )
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ID", "delete-scope-failure")
    monkeypatch.setenv("VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT", str(tmp_path))
    released: list[str] = []

    class MaintenanceLease:
        def release(self) -> None:
            released.append("maintenance")

    monkeypatch.setattr(
        delete_module,
        "acquire_retention_maintenance_lease",
        lambda: MaintenanceLease(),
    )
    monkeypatch.setattr(
        delete_module,
        "RedisScopeLeaseFactory",
        lambda: lambda _scope: (_ for _ in ()).throw(RuntimeError("project scope unavailable")),
    )

    with pytest.raises(RuntimeError, match="project scope unavailable"):
        project_rq.delete_run_rq(runid, wd=str(run_dir), delete_files=True)

    assert released == ["maintenance"]


def test_gc_runs_rq_deferred_delete_suppresses_messages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runid = "gc-run"
    run_dir = tmp_path / runid
    run_dir.mkdir(parents=True)
    (run_dir / "ron.nodb").write_text("nodb", encoding="utf-8")

    published, mark_calls, user_datastore = _stub_delete_environment(
        monkeypatch,
        runid=runid,
        job_id="job-2",
        errno_value=project_rq.errno.EBUSY,
    )
    ttl_module = __import__("wepppy.weppcloud.utils.run_ttl", fromlist=["collect_gc_candidates"])
    monkeypatch.setattr(
        ttl_module,
        "collect_gc_candidates",
        lambda *args, **kwargs: [
            {
                "runid": runid,
                "wd": str(run_dir),
                "reason": "queued",
            }
        ],
    )

    result = project_rq.gc_runs_rq(root=str(tmp_path), limit=10, dry_run=False)

    assert result["deleted"] == 0
    assert result["deferred"] == 1
    assert result["errors"] == []
    assert len(user_datastore.deleted) == 1
    assert run_dir.exists()
    assert any(call["state"] == "queued" for call in mark_calls)
    assert any(call["db_cleared"] is True for call in mark_calls)
    assert not any("delete deferred" in message for message in published)
    assert not any("delete retry" in message for message in published)
    assert not any("delete failed" in message for message in published)


def test_index_usersum_docs_rq_builds_index_without_postgres(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"
    usersum_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = usersum_dir / "weppcloud" / "example.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# Example\n\nSearchable content.\n", encoding="utf-8")

    (usersum_dir / "docs_manifest.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "docs:",
                "  - doc_id: usersum.weppcloud.example",
                "    source: local",
                "    rel_path: wepppy/weppcloud/routes/usersum/weppcloud/example.md",
                "    title: Example Doc",
                "    min_role: user",
                "    category: weppcloud",
                "    audience_tags: []",
                "    status: active",
                "    nav_key: usersum.weppcloud.example",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "nav_tree.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "roots:",
                "  - key: usersum.weppcloud.section",
                "    title: WEPPcloud",
                "    collapsible: true",
                "    children:",
                "      - key: usersum.weppcloud.example",
                "        doc_id: usersum.weppcloud.example",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "vendors.yaml").write_text("version: 1\nvendors: []\n", encoding="utf-8")

    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    result = project_rq.index_usersum_docs_rq(
        usersum_base_dir=str(usersum_dir),
        repo_root=str(repo_root),
        sync_postgres=False,
    )

    assert result["documents"] == 1
    assert result["index_written"] is True
    assert result["postgres_synced"] is False
    assert (usersum_dir / "generated" / "docs_index.json").is_file()
    assert any("STARTED index_usersum_docs_rq" in message for _, message in published)
    assert any("COMPLETED index_usersum_docs_rq" in message for _, message in published)


def test_index_usersum_docs_rq_syncs_vendor_docs_before_require_vendor_validation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"
    usersum_dir.mkdir(parents=True, exist_ok=True)

    forest_repo = tmp_path / "wepp-forest"
    forest_repo.mkdir(parents=True, exist_ok=True)
    (forest_repo / "change-log.md").write_text(
        "# Change Log\n\n| Date | Commit Hash | Compiler | Version | Notes |\n",
        encoding="utf-8",
    )

    (usersum_dir / "docs_manifest.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "docs:",
                "  - doc_id: usersum.weppcloud.wepp_forest_change_log",
                "    source: vendor",
                "    vendor_id: wepp-forest",
                "    rel_path: wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md",
                "    title: WEPP-Forest Change Log",
                "    min_role: user",
                "    category: weppcloud",
                "    audience_tags: [user]",
                "    status: active",
                "    nav_key: usersum.weppcloud.wepp_forest_change_log",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "nav_tree.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "roots:",
                "  - key: usersum.technical_reference",
                "    title: Technical Reference",
                "    collapsible: true",
                "    children:",
                "      - key: usersum.weppcloud.wepp_forest_change_log",
                "        doc_id: usersum.weppcloud.wepp_forest_change_log",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "vendors.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "vendors:",
                "  - vendor_id: wepp-forest",
                f"    source_repo_path: {forest_repo}",
                "    source_ref: main",
                "    include_globs: [\"change-log.md\"]",
                "    exclude_globs: [\"**/.git/**\"]",
                "    target_root: wepppy/weppcloud/routes/usersum/vendor/wepp-forest",
                "    route_prefix: /usersum/vendor/wepp-forest",
                "",
            ]
        ),
        encoding="utf-8",
    )

    vendored_copy = usersum_dir / "vendor" / "wepp-forest" / "change-log.md"
    assert not vendored_copy.exists()

    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    result = project_rq.index_usersum_docs_rq(
        usersum_base_dir=str(usersum_dir),
        repo_root=str(repo_root),
        require_vendor_files=True,
        sync_postgres=False,
    )

    assert vendored_copy.is_file()
    assert result["documents"] == 1
    assert result["vendors_synced"] == 1
    assert result["vendors_skipped"] == 0
    assert any("COMPLETED index_usersum_docs_rq" in message for _, message in published)


def test_index_usersum_docs_rq_syncs_vendor_docs_when_write_index_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"
    usersum_dir.mkdir(parents=True, exist_ok=True)

    forest_repo = tmp_path / "wepp-forest"
    forest_repo.mkdir(parents=True, exist_ok=True)
    (forest_repo / "change-log.md").write_text(
        "# Change Log\n\n| Date | Commit Hash | Compiler | Version | Notes |\n",
        encoding="utf-8",
    )

    (usersum_dir / "docs_manifest.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "docs:",
                "  - doc_id: usersum.weppcloud.wepp_forest_change_log",
                "    source: vendor",
                "    vendor_id: wepp-forest",
                "    rel_path: wepppy/weppcloud/routes/usersum/vendor/wepp-forest/change-log.md",
                "    title: WEPP-Forest Change Log",
                "    min_role: user",
                "    category: weppcloud",
                "    audience_tags: [user]",
                "    status: active",
                "    nav_key: usersum.weppcloud.wepp_forest_change_log",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "nav_tree.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "roots:",
                "  - key: usersum.technical_reference",
                "    title: Technical Reference",
                "    collapsible: true",
                "    children:",
                "      - key: usersum.weppcloud.wepp_forest_change_log",
                "        doc_id: usersum.weppcloud.wepp_forest_change_log",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "vendors.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "vendors:",
                "  - vendor_id: wepp-forest",
                f"    source_repo_path: {forest_repo}",
                "    source_ref: main",
                "    include_globs: [\"change-log.md\"]",
                "    exclude_globs: [\"**/.git/**\"]",
                "    target_root: wepppy/weppcloud/routes/usersum/vendor/wepp-forest",
                "    route_prefix: /usersum/vendor/wepp-forest",
                "",
            ]
        ),
        encoding="utf-8",
    )

    vendored_copy = usersum_dir / "vendor" / "wepp-forest" / "change-log.md"
    index_path = usersum_dir / "generated" / "docs_index.json"
    assert not vendored_copy.exists()
    assert not index_path.exists()

    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    result = project_rq.index_usersum_docs_rq(
        usersum_base_dir=str(usersum_dir),
        repo_root=str(repo_root),
        write_index=False,
        require_vendor_files=True,
        sync_postgres=False,
    )

    assert vendored_copy.is_file()
    assert not index_path.exists()
    assert result["documents"] == 1
    assert result["index_written"] is False
    assert result["vendors_synced"] == 1
    assert result["vendors_skipped"] == 0
    assert any("COMPLETED index_usersum_docs_rq" in message for _, message in published)


def test_index_usersum_docs_rq_postgres_sync_is_readonly_on_repo_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"
    usersum_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = usersum_dir / "weppcloud" / "example.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("# Example\n\nSearchable content.\n", encoding="utf-8")

    (usersum_dir / "docs_manifest.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "docs:",
                "  - doc_id: usersum.weppcloud.example",
                "    source: local",
                "    rel_path: wepppy/weppcloud/routes/usersum/weppcloud/example.md",
                "    title: Example Doc",
                "    min_role: user",
                "    category: weppcloud",
                "    audience_tags: []",
                "    status: active",
                "    nav_key: usersum.weppcloud.example",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "nav_tree.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "roots:",
                "  - key: usersum.weppcloud.section",
                "    title: WEPPcloud",
                "    collapsible: true",
                "    children:",
                "      - key: usersum.weppcloud.example",
                "        doc_id: usersum.weppcloud.example",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (usersum_dir / "vendors.yaml").write_text(
        "\n".join(
            [
                "version: 1",
                "vendors:",
                "  - vendor_id: wepp-forest",
                f"    source_repo_path: {tmp_path / 'wepp-forest'}",
                "    source_ref: main",
                "    include_globs: [\"change-log.md\"]",
                "    exclude_globs: [\"**/.git/**\"]",
                "    target_root: wepppy/weppcloud/routes/usersum/vendor/wepp-forest",
                "    route_prefix: /usersum/vendor/wepp-forest",
                "",
            ]
        ),
        encoding="utf-8",
    )

    vendor_sync_module = __import__(
        "wepppy.weppcloud.usersum_docs.vendor_sync",
        fromlist=["sync_vendor_docs"],
    )
    sync_called: list[bool] = []

    def _fake_sync_vendor_docs(*args, **kwargs):
        sync_called.append(True)
        return []

    monkeypatch.setattr(vendor_sync_module, "sync_vendor_docs", _fake_sync_vendor_docs)

    pg_search_module = __import__(
        "wepppy.weppcloud.usersum_docs.pg_search",
        fromlist=["PostgresUsersumSearchBackend"],
    )
    synced_docs: list[object] = []

    class _FakePostgresUsersumSearchBackend:
        def __init__(self, _db_url: str) -> None:
            pass

        def ensure_synced(self, docs) -> None:
            synced_docs.append(docs)

    monkeypatch.setattr(
        pg_search_module,
        "PostgresUsersumSearchBackend",
        _FakePostgresUsersumSearchBackend,
    )

    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        project_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )

    result = project_rq.index_usersum_docs_rq(
        usersum_base_dir=str(usersum_dir),
        repo_root=str(repo_root),
        write_index=False,
        require_vendor_files=False,
        sync_postgres=True,
        db_url="postgresql://example.invalid/usersum",
    )

    assert sync_called == []
    assert len(synced_docs) == 1
    assert len(synced_docs[0]) == 1
    assert not (usersum_dir / "generated" / "docs_index.json").exists()
    assert result["index_written"] is False
    assert result["postgres_synced"] is True
    assert any("COMPLETED index_usersum_docs_rq" in message for _, message in published)
