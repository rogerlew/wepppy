from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.batch_runner as batch_runner_mod
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import TaskEnum
from wepppy.runtime_paths.errors import NoDirError


pytestmark = pytest.mark.unit


class _Prep:
    def __init__(self, timestamps: dict[TaskEnum, int] | None = None) -> None:
        self.timestamps = timestamps or {}

    def __getitem__(self, key: TaskEnum | str) -> int | None:
        task = key if isinstance(key, TaskEnum) else TaskEnum(key)
        return self.timestamps.get(task)


class _RedisPrepFactory:
    timestamps_by_wd: dict[str, dict[TaskEnum, int]] = {}

    @classmethod
    def getInstance(cls, wd: str):
        return _Prep(cls.timestamps_by_wd.get(str(wd), {}))


class _Logger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return


def _runner(tmp_path: Path) -> BatchRunner:
    runner = BatchRunner.__new__(BatchRunner)
    runner.wd = str(tmp_path / "batch")
    Path(runner.wd).mkdir(parents=True)
    runner._rq_job_ids = {}
    runner._run_directives = {task: False for task in BatchRunner.DEFAULT_TASKS}
    return runner


def test_watar_is_registered_as_optional_batch_task() -> None:
    assert TaskEnum.run_watar in BatchRunner.DEFAULT_TASKS
    assert BatchRunner.OPTIONAL_TASK_NODB_FILENAMES[TaskEnum.run_watar] == "ash.nodb"


def test_watar_completion_is_required_only_when_ash_controller_exists(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    runner._run_directives[TaskEnum.run_watar] = True
    leaf = Path(runner.batch_runs_dir) / "leaf"
    leaf.mkdir(parents=True)

    assert TaskEnum.run_watar not in runner._completion_tasks(str(leaf))

    (leaf / "ash.nodb").write_text("{}", encoding="utf-8")

    assert TaskEnum.run_watar in runner._completion_tasks(str(leaf))


def test_watar_timestamp_controls_retry_for_ash_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path)
    runner._run_directives[TaskEnum.run_watar] = True
    leaf = Path(runner.batch_runs_dir) / "leaf"
    leaf.mkdir(parents=True)
    (leaf / "ash.nodb").write_text("{}", encoding="utf-8")
    feature = SimpleNamespace(runid="leaf")

    monkeypatch.setattr(batch_runner_mod, "RedisPrep", _RedisPrepFactory)
    _RedisPrepFactory.timestamps_by_wd[str(leaf)] = {}

    pending = runner.classify_batch_run_state(feature)

    assert pending["status"] == "incomplete"
    assert pending["missing_tasks"] == [TaskEnum.run_watar.value]
    assert pending["retry_eligible"] is True

    _RedisPrepFactory.timestamps_by_wd[str(leaf)] = {TaskEnum.run_watar: 3}

    complete = runner.classify_batch_run_state(feature)

    assert complete["status"] == "complete"
    assert complete["missing_tasks"] == []
    assert complete["retry_eligible"] is False


def test_post_load_normalizes_old_directive_map_for_watar(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    runner._run_directives = {TaskEnum.fetch_dem.value: False}

    loaded = BatchRunner._post_instance_loaded(runner)

    assert loaded._run_directives[TaskEnum.fetch_dem] is False
    assert loaded._run_directives[TaskEnum.run_watar] is True
    assert set(loaded._run_directives) == set(BatchRunner.DEFAULT_TASKS)


def test_directory_roots_lock_sorts_preflights_and_rechecks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight_calls: list[str] = []
    lock_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(batch_runner_mod, "_BATCH_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(
        batch_runner_mod,
        "_require_directory_root",
        lambda _wd, root: preflight_calls.append(root),
    )

    @contextmanager
    def _lock(
        _wd: str,
        root: str,
        *,
        purpose: str,
        scope: str,
        scope_token: str,
    ):
        assert scope == "effective_root_path"
        assert scope_token == f"scope:{root}"
        lock_calls.append((root, purpose))
        yield

    monkeypatch.setattr(
        batch_runner_mod,
        "nodir_maintenance_lock_scope_token",
        lambda _wd, root, *, scope: f"scope:{root}",
    )
    monkeypatch.setattr(batch_runner_mod, "nodir_maintenance_lock", _lock)

    result = batch_runner_mod._run_with_directory_roots_lock(
        "/wc1/batch/demo/runs/leaf",
        ("watershed", "climate", "landuse", "climate"),
        lambda: "ok",
        purpose="batch-run-watar",
    )

    assert result == "ok"
    assert lock_calls == [
        ("climate", "batch-run-watar/climate"),
        ("landuse", "batch-run-watar/landuse"),
        ("watershed", "batch-run-watar/watershed"),
    ]
    assert preflight_calls == [
        "climate",
        "landuse",
        "watershed",
        "climate",
        "landuse",
        "watershed",
    ]


def test_directory_roots_lock_retries_nodir_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    monkeypatch.setattr(batch_runner_mod, "_BATCH_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(batch_runner_mod, "_require_directory_root", lambda *_args: None)
    monkeypatch.setattr(
        batch_runner_mod,
        "nodir_maintenance_lock_scope_token",
        lambda _wd, root, *, scope: f"scope:{root}",
    )

    @contextmanager
    def _lock(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise NoDirError(http_status=409, code="NODIR_LOCKED", message="busy")
        yield

    monkeypatch.setattr(batch_runner_mod, "nodir_maintenance_lock", _lock)

    assert batch_runner_mod._run_with_directory_roots_lock(
        "/wc1/batch/demo/runs/leaf",
        ("climate",),
        lambda: "ok",
        purpose="batch-run-watar",
    ) == "ok"
    assert attempts == 2


def test_directory_roots_lock_rejects_archive_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        batch_runner_mod,
        "nodir_resolve",
        lambda *_args, **_kwargs: SimpleNamespace(form="tar"),
    )

    with pytest.raises(NoDirError) as exc_info:
        batch_runner_mod._run_with_directory_roots_lock(
            "/wc1/batch/demo/runs/leaf",
            ("climate", "landuse", "watershed"),
            lambda: None,
            purpose="batch-run-watar",
        )

    assert exc_info.value.code == "NODIR_ARCHIVE_ACTIVE"


def test_run_watar_stage_requires_wepp_timestamps(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    prep = _Prep({TaskEnum.run_wepp_hillslopes: 1})

    with pytest.raises(RuntimeError, match="run_wepp_watershed"):
        runner._run_watar_stage(
            str(tmp_path),
            prep,
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(is_single_storm=False),
            _Logger(),
        )


def test_run_watar_stage_repairs_interchange_and_uses_persisted_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path)
    interchange = tmp_path / "wepp" / "output" / "interchange"
    wepp = SimpleNamespace(wepp_interchange_dir=str(interchange))
    climate = SimpleNamespace(is_single_storm=False)
    prep = _Prep(
        {
            TaskEnum.run_wepp_hillslopes: 1,
            TaskEnum.run_wepp_watershed: 2,
        }
    )
    calls: list[object] = []

    def _ensure(name: str):
        def _call(*_args: object, **_kwargs: object) -> None:
            calls.append(name)
            interchange.mkdir(parents=True, exist_ok=True)
            if name == "hillslope":
                (interchange / "H.pass.parquet").touch()
                (interchange / "H.wat.parquet").touch()
            elif name == "totalwatsed3":
                (interchange / "totalwatsed3.parquet").touch()

        return _call

    monkeypatch.setattr(batch_runner_mod, "ensure_hillslope_interchange", _ensure("hillslope"))
    monkeypatch.setattr(batch_runner_mod, "ensure_totalwatsed3", _ensure("totalwatsed3"))
    monkeypatch.setattr(batch_runner_mod, "ensure_watershed_interchange", _ensure("watershed"))

    def _locked(_wd: str, roots, callback, *, purpose: str):
        calls.append((tuple(roots), purpose))
        return callback()

    monkeypatch.setattr(batch_runner_mod, "_run_with_directory_roots_lock", _locked)

    ash = SimpleNamespace(
        fire_date="9/12",
        ini_white_ash_depth_mm=2.5,
        ini_black_ash_depth_mm=4.5,
        run_ash=lambda *args: calls.append(("run_ash", args)),
    )

    runner._run_watar_stage(str(tmp_path), prep, ash, wepp, climate, _Logger())

    assert calls == [
        (("climate", "landuse", "watershed"), "batch-run-watar"),
        "hillslope",
        "totalwatsed3",
        "watershed",
        ("run_ash", ("9/12", 2.5, 4.5)),
    ]


def test_run_watar_stage_rejects_missing_interchange_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path)
    interchange = tmp_path / "wepp" / "output" / "interchange"
    interchange.mkdir(parents=True)
    (interchange / "H.pass.parquet").touch()
    (interchange / "H.wat.parquet").touch()
    prep = _Prep(
        {
            TaskEnum.run_wepp_hillslopes: 1,
            TaskEnum.run_wepp_watershed: 2,
        }
    )
    monkeypatch.setattr(batch_runner_mod, "ensure_hillslope_interchange", lambda *_args: None)
    monkeypatch.setattr(batch_runner_mod, "ensure_totalwatsed3", lambda *_args: None)
    monkeypatch.setattr(batch_runner_mod, "ensure_watershed_interchange", lambda *_args: None)
    monkeypatch.setattr(
        batch_runner_mod,
        "_run_with_directory_roots_lock",
        lambda _wd, _roots, callback, *, purpose: callback(),
    )
    ash_calls: list[object] = []
    ash = SimpleNamespace(
        fire_date="9/12",
        ini_white_ash_depth_mm=2.5,
        ini_black_ash_depth_mm=4.5,
        run_ash=lambda *args: ash_calls.append(args),
    )

    with pytest.raises(RuntimeError, match="totalwatsed3.parquet"):
        runner._run_watar_stage(
            str(tmp_path),
            prep,
            ash,
            SimpleNamespace(wepp_interchange_dir=str(interchange)),
            SimpleNamespace(is_single_storm=False),
            _Logger(),
        )

    assert ash_calls == []


def test_run_watar_stage_rejects_single_storm(tmp_path: Path) -> None:
    runner = _runner(tmp_path)
    prep = _Prep(
        {
            TaskEnum.run_wepp_hillslopes: 1,
            TaskEnum.run_wepp_watershed: 2,
        }
    )

    with pytest.raises(RuntimeError, match="single-storm"):
        runner._run_watar_stage(
            str(tmp_path),
            prep,
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(is_single_storm=True),
            _Logger(),
        )
