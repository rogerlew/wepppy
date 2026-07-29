from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import wepppy.rq.migrations_rq as migrations
from wepppy.tools.migrations import runner

pytestmark = pytest.mark.unit


def _install_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, str]], SimpleNamespace]:
    published: list[tuple[str, str]] = []
    job = SimpleNamespace(id="migration-job-1")
    monkeypatch.setattr(migrations, "get_current_job", lambda: job)
    monkeypatch.setattr(
        migrations.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    monkeypatch.setattr(
        migrations,
        "_setup_file_logger",
        lambda wd: logging.getLogger("test-migrations-rq"),
    )
    return published, job


def test_migrations_rq_returns_result_updates_version_and_publishes_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    published, _job = _install_runtime(monkeypatch)
    result = runner.MigrationResult(
        wd=str(tmp_path),
        success=True,
        applied=["nodb_version"],
        skipped=["query_catalog"],
    )
    monkeypatch.setattr(runner, "run_all_migrations", lambda *args, **kwargs: result)
    version_updates: list[tuple[str, int]] = []
    monkeypatch.setattr(
        migrations,
        "write_version",
        lambda wd, version: version_updates.append((wd, version)),
    )

    payload = migrations.migrations_rq(str(tmp_path), "run-1")

    assert payload["success"] is True
    assert payload["applied"] == ["nodb_version"]
    assert version_updates == [(str(tmp_path), migrations.CURRENT_VERSION)]
    messages = [message for _channel, message in published]
    assert any("STARTED" in message for message in messages)
    assert any("COMPLETED" in message for message in messages)
    assert any("MIGRATION_COMPLETE" in message for message in messages)
    assert {channel for channel, _message in published} == {
        "run-1:migrations",
        "run-1:run_sync",
    }


def test_migrations_rq_honors_archive_and_restores_readonly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _install_runtime(monkeypatch)
    archive_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        migrations,
        "_run_archive_inline",
        lambda wd, runid, job_id, *args: archive_calls.append((runid, job_id)),
    )
    monkeypatch.setattr(
        runner,
        "run_all_migrations",
        lambda *args, **kwargs: runner.MigrationResult(wd=str(tmp_path), success=True),
    )
    monkeypatch.setattr(migrations, "write_version", lambda *args: None)

    readonly = SimpleNamespace(readonly=False)
    from wepppy.nodb.core.ron import Ron

    monkeypatch.setattr(Ron, "getInstance", lambda wd: readonly)

    migrations.migrations_rq(
        str(tmp_path),
        "run-1",
        archive_before=True,
        restore_readonly=True,
    )

    assert archive_calls == [("run-1", "migration-job-1")]
    assert readonly.readonly is True


def test_migrations_rq_stops_when_requested_archive_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _install_runtime(monkeypatch)
    monkeypatch.setattr(
        migrations,
        "_run_archive_inline",
        lambda *args: (_ for _ in ()).throw(OSError("archive unavailable")),
    )
    migration_calls: list[str] = []
    monkeypatch.setattr(
        runner,
        "run_all_migrations",
        lambda *args, **kwargs: migration_calls.append("called"),
    )

    with pytest.raises(OSError, match="archive unavailable"):
        migrations.migrations_rq(
            str(tmp_path),
            "run-1",
            archive_before=True,
        )

    assert migration_calls == []
