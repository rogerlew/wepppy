from __future__ import annotations

import errno
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.batch_runner as batch_runner_mod
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import TaskEnum

pytestmark = pytest.mark.unit


class _StopBeforeControllers(RuntimeError):
    """Sentinel raised to stop run_batch_project after workspace prep."""


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return

    def error(self, *_args: object, **_kwargs: object) -> None:
        return


class _FeatureStub:
    def __init__(self, runid: str) -> None:
        self.runid = runid

    def save_geojson(self, _path: str) -> None:
        # Keep target_watershed.geojson absent so Ron.getInstance is never needed.
        return


def _runner_stub(tmp_path: Path, *, rmtree_enabled: bool) -> BatchRunner:
    runner = BatchRunner.__new__(BatchRunner)
    runner.wd = str(tmp_path / "batch-demo")
    Path(runner.wd).mkdir(parents=True, exist_ok=True)
    (Path(runner.wd) / "logs").mkdir(parents=True, exist_ok=True)

    directives = {task: False for task in BatchRunner.DEFAULT_TASKS}
    directives[TaskEnum.fetch_dem] = True
    directives[TaskEnum.if_exists_rmtree] = rmtree_enabled
    runner._run_directives = directives
    return runner


def test_run_batch_project_does_not_delete_workspace_when_rmtree_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner_stub(tmp_path, rmtree_enabled=False)
    runid_wd = Path(runner.wd) / "runs" / "leaf-run"
    runid_wd.mkdir(parents=True, exist_ok=True)
    marker = runid_wd / "preserve.me"
    marker.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(batch_runner_mod, "get_wd", lambda _runid: str(runid_wd))
    monkeypatch.setattr(BatchRunner, "_get_run_logger", lambda _self, _runid: _NoopLogger())
    monkeypatch.setattr(
        batch_runner_mod.RedisPrep,
        "getInstance",
        staticmethod(lambda _wd: (_ for _ in ()).throw(_StopBeforeControllers())),
    )
    monkeypatch.setattr(
        batch_runner_mod.shutil,
        "rmtree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rmtree should not be called")),
    )

    with pytest.raises(_StopBeforeControllers):
        runner.run_batch_project(_FeatureStub("leaf-run"))

    assert runid_wd.is_dir()
    assert marker.read_text(encoding="utf-8") == "keep"


def test_run_batch_project_survives_enotempty_during_workspace_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner_stub(tmp_path, rmtree_enabled=True)
    runid_wd = Path(runner.wd) / "runs" / "leaf-run"
    runid_wd.mkdir(parents=True, exist_ok=True)
    (runid_wd / "old.txt").write_text("old", encoding="utf-8")

    base_wd = Path(runner.wd) / "_base"
    base_wd.mkdir(parents=True, exist_ok=True)
    (base_wd / "base.txt").write_text("base", encoding="utf-8")

    monkeypatch.setattr(batch_runner_mod, "get_wd", lambda _runid: str(runid_wd))
    monkeypatch.setattr(BatchRunner, "_get_run_logger", lambda _self, _runid: _NoopLogger())
    monkeypatch.setattr(batch_runner_mod, "clear_nodb_file_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(batch_runner_mod, "clear_locks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        batch_runner_mod.RedisPrep,
        "getInstance",
        staticmethod(lambda _wd: (_ for _ in ()).throw(_StopBeforeControllers())),
    )

    real_rmtree = batch_runner_mod.shutil.rmtree
    calls = {"enotempty_raised": 0}

    def _flaky_rmtree(path: str | Path, *args: object, **kwargs: object) -> None:
        name = Path(path).name
        if name.startswith("leaf-run") and calls["enotempty_raised"] == 0:
            calls["enotempty_raised"] += 1
            raise OSError(errno.ENOTEMPTY, "Directory not empty", str(path))
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(batch_runner_mod.shutil, "rmtree", _flaky_rmtree)

    with pytest.raises(_StopBeforeControllers):
        runner.run_batch_project(_FeatureStub("leaf-run"))

    assert calls["enotempty_raised"] == 1
    assert runid_wd.is_dir()
    assert (runid_wd / "base.txt").read_text(encoding="utf-8") == "base"
    assert not list((runid_wd.parent).glob("leaf-run.stale.*"))


def test_run_batch_project_fails_fast_when_workspace_rename_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner_stub(tmp_path, rmtree_enabled=True)
    runid_wd = Path(runner.wd) / "runs" / "leaf-run"
    runid_wd.mkdir(parents=True, exist_ok=True)
    marker = runid_wd / "preserve.me"
    marker.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(batch_runner_mod, "get_wd", lambda _runid: str(runid_wd))
    monkeypatch.setattr(BatchRunner, "_get_run_logger", lambda _self, _runid: _NoopLogger())
    monkeypatch.setattr(
        batch_runner_mod.os,
        "replace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(errno.EBUSY, "busy")),
    )
    monkeypatch.setattr(
        batch_runner_mod.shutil,
        "rmtree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rmtree should not be called")),
    )

    with pytest.raises(RuntimeError, match="workspace reset rename failed"):
        runner.run_batch_project(_FeatureStub("leaf-run"))

    assert runid_wd.is_dir()
    assert marker.read_text(encoding="utf-8") == "keep"


def test_require_directory_root_rejects_archive_form(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_runner_mod,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="archive"),
    )

    with pytest.raises(batch_runner_mod.NoDirError) as exc_info:
        batch_runner_mod._require_directory_root("/tmp/run", "watershed")

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"
