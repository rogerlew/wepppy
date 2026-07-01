from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.rq.batch_rq as batch_rq
from wepppy.nodb import batch_runner as batch_runner_module
from wepppy.nodb.batch_runner import BatchRunner
from wepppy.nodb.redis_prep import TaskEnum


pytestmark = pytest.mark.unit


class _FakeRedisPrep:
    timestamps_by_wd: dict[str, dict[str, int]] = {}

    def __init__(self, wd: str) -> None:
        self.wd = str(wd)

    @classmethod
    def getInstance(cls, wd: str, allow_nonexistent: bool = False, ignore_lock: bool = False):
        if not Path(wd).exists():
            raise FileNotFoundError(wd)
        return cls(str(wd))

    def __getitem__(self, key) -> int | None:
        task = key.value if isinstance(key, TaskEnum) else str(key)
        return self.timestamps_by_wd.get(self.wd, {}).get(task)

    def timestamps_report(self) -> str:
        return f"RedisPrep Timestamps ({Path(self.wd).name})"

    def remove_all_timestamp(self) -> None:
        self.timestamps_by_wd[self.wd] = {}

    def timestamp(self, key: TaskEnum) -> None:
        self.timestamps_by_wd.setdefault(self.wd, {})[key.value] = 1

    def remove_timestamp(self, key: TaskEnum) -> None:
        self.timestamps_by_wd.setdefault(self.wd, {}).pop(key.value, None)


def _runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> BatchRunner:
    monkeypatch.setattr(BatchRunner, "_init_base_project", lambda self: None)
    monkeypatch.setattr(batch_runner_module, "RedisPrep", _FakeRedisPrep)
    batch_dir = tmp_path / "demo"
    batch_dir.mkdir(parents=True, exist_ok=True)
    runner = BatchRunner(str(batch_dir), "batch/default_batch.cfg", "dummy_base.cfg")
    for task in runner.DEFAULT_TASKS:
        runner._run_directives[task] = False
    for task in (
        TaskEnum.fetch_dem,
        TaskEnum.build_climate,
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
    ):
        runner._run_directives[task] = True
    return runner


def _feature(runid: str):
    return SimpleNamespace(runid=runid)


def _set_timestamps(runner: BatchRunner, leaf: str, tasks: tuple[TaskEnum, ...]) -> None:
    run_dir = Path(runner.batch_runs_dir) / leaf
    run_dir.mkdir(parents=True, exist_ok=True)
    _FakeRedisPrep.timestamps_by_wd[str(run_dir)] = {
        task.value: index + 1 for index, task in enumerate(tasks)
    }


def test_batch_directory_root_lock_uses_effective_path_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        batch_runner_module,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="dir"),
    )
    scope_calls: list[tuple[str, str, str]] = []
    lock_calls: list[tuple[str, str, str, str, str]] = []

    def _scope_token(wd: str, root: str, *, scope: str) -> str:
        scope_calls.append((wd, root, scope))
        return f"scope:{wd}:{root}"

    @contextmanager
    def _lock(wd: str, root: str, *, purpose: str, scope: str, scope_token: str):
        lock_calls.append((wd, root, purpose, scope, scope_token))
        yield

    monkeypatch.setattr(batch_runner_module, "nodir_maintenance_lock_scope_token", _scope_token)
    monkeypatch.setattr(batch_runner_module, "nodir_maintenance_lock", _lock)

    result = batch_runner_module._run_with_directory_root_lock(
        "/wc1/batch/demo/runs/OR-154",
        "climate",
        lambda: "ok",
        purpose="unit",
    )

    assert result == "ok"
    assert scope_calls == [("/wc1/batch/demo/runs/OR-154", "climate", "effective_root_path")]
    assert lock_calls == [
        (
            "/wc1/batch/demo/runs/OR-154",
            "climate",
            "unit",
            "effective_root_path",
            "scope:/wc1/batch/demo/runs/OR-154:climate",
        )
    ]


def test_batch_directory_root_lock_retries_nodir_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(batch_runner_module, "_BATCH_LOCK_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(batch_runner_module, "_BATCH_LOCK_RETRY_SECONDS", 0.0)
    monkeypatch.setattr(
        batch_runner_module,
        "nodir_resolve",
        lambda _wd, _root, view="effective": SimpleNamespace(form="dir"),
    )
    monkeypatch.setattr(
        batch_runner_module,
        "nodir_maintenance_lock_scope_token",
        lambda wd, root, *, scope: f"scope:{wd}:{root}",
    )
    attempts = {"count": 0}

    @contextmanager
    def _lock(_wd: str, _root: str, *, purpose: str, scope: str, scope_token: str):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise batch_runner_module.NoDirError(
                http_status=503,
                code="NODIR_LOCKED",
                message="busy",
            )
        yield

    monkeypatch.setattr(batch_runner_module, "nodir_maintenance_lock", _lock)

    result = batch_runner_module._run_with_directory_root_lock(
        "/wc1/batch/demo/runs/OR-154",
        "climate",
        lambda: "ok",
        purpose="unit",
    )

    assert result == "ok"
    assert attempts["count"] == 2


def test_clear_batch_leaf_nodb_state_clears_cache_and_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runid = "batch;;demo;;OR-154"
    events: list[tuple[str, str]] = []

    monkeypatch.setattr(
        batch_runner_module,
        "clear_nodb_file_cache",
        lambda value: events.append(("cache", value)),
    )
    monkeypatch.setattr(
        batch_runner_module,
        "clear_locks",
        lambda value: events.append(("locks", value)) or ["climate.nodb"],
    )

    locks_cleared = batch_runner_module._clear_batch_leaf_nodb_state(
        runid,
        batch_runner_module.logging.getLogger("test.batch.cleanup"),
    )

    assert locks_cleared == ("climate.nodb",)
    assert events == [("cache", runid), ("locks", runid)]


def test_run_batch_project_clears_existing_leaf_locks_before_redisprep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    run_dir = Path(runner.batch_runs_dir) / "retry-leaf"
    run_dir.mkdir(parents=True)
    events: list[tuple[str, str]] = []

    def _cleanup(runid: str, logger) -> tuple[str, ...]:
        events.append(("cleanup", runid))
        return ("climate.nodb",)

    class _StopRedisPrep:
        @classmethod
        def getInstance(cls, wd: str):
            events.append(("redisprep", str(wd)))
            raise RuntimeError("stop after cleanup")

    monkeypatch.setattr(
        batch_runner_module,
        "get_wd",
        lambda runid: str(Path(runner.batch_runs_dir) / runid.split(";;")[-1]),
    )
    monkeypatch.setattr(batch_runner_module, "_clear_batch_leaf_nodb_state", _cleanup)
    monkeypatch.setattr(batch_runner_module, "RedisPrep", _StopRedisPrep)

    with pytest.raises(RuntimeError, match="stop after cleanup"):
        runner.run_batch_project(_feature("retry-leaf"))

    assert events == [
        ("cleanup", "batch;;demo;;retry-leaf"),
        ("redisprep", str(run_dir)),
    ]


def test_run_batch_project_repairs_hillslope_interchange_before_watershed_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    run_dir = Path(runner.batch_runs_dir) / "retry-leaf"
    run_dir.mkdir(parents=True)
    _FakeRedisPrep.timestamps_by_wd[str(run_dir)] = {
        TaskEnum.fetch_dem.value: 1,
        TaskEnum.build_climate.value: 2,
        TaskEnum.run_wepp_hillslopes.value: 3,
    }

    events: list[str] = []

    class _FakeWepp:
        def _check_and_set_baseflow_map(self) -> None:
            events.append("baseflow")

        def _check_and_set_phosphorus_map(self) -> None:
            events.append("phosphorus")

        def prep_watershed(self) -> None:
            events.append("prep_watershed")

        def run_watershed(self) -> None:
            events.append("run_watershed")

    monkeypatch.setattr(
        batch_runner_module,
        "get_wd",
        lambda runid: str(Path(runner.batch_runs_dir) / runid.split(";;")[-1]),
    )
    monkeypatch.setattr(batch_runner_module, "_clear_batch_leaf_nodb_state", lambda *_args: ())
    monkeypatch.setattr(batch_runner_module.Ron, "getInstance", lambda _wd: SimpleNamespace())
    monkeypatch.setattr(batch_runner_module.Watershed, "getInstance", lambda _wd: SimpleNamespace())
    monkeypatch.setattr(batch_runner_module.Landuse, "getInstance", lambda _wd: SimpleNamespace())
    monkeypatch.setattr(batch_runner_module.Soils, "getInstance", lambda _wd: SimpleNamespace())
    monkeypatch.setattr(
        batch_runner_module.Climate,
        "getInstance",
        lambda _wd: SimpleNamespace(observed_start_year=2000, observed_end_year=2001),
    )
    monkeypatch.setattr(batch_runner_module.Wepp, "getInstance", lambda _wd: _FakeWepp())
    monkeypatch.setattr(batch_runner_module.RAP_TS, "tryGetInstance", lambda _wd: None)
    monkeypatch.setattr(batch_runner_module.OpenET_TS, "tryGetInstance", lambda _wd: None)
    monkeypatch.setattr(
        batch_runner_module,
        "ensure_hillslope_interchange",
        lambda *_args, **_kwargs: events.append("ensure_hillslope_interchange"),
    )
    monkeypatch.setattr(
        batch_runner_module,
        "ensure_totalwatsed3",
        lambda *_args, **_kwargs: events.append("ensure_totalwatsed3"),
    )
    monkeypatch.setattr(
        batch_runner_module,
        "ensure_watershed_interchange",
        lambda *_args, **_kwargs: events.append("ensure_watershed_interchange"),
    )
    monkeypatch.setattr(
        batch_runner_module,
        "activate_query_engine_for_run",
        lambda *_args, **_kwargs: events.append("activate_query_engine"),
    )

    runner.run_batch_project(_feature("retry-leaf"))

    assert "clean" not in events
    assert events.index("ensure_hillslope_interchange") < events.index("run_watershed")
    assert events == [
        "baseflow",
        "phosphorus",
        "ensure_hillslope_interchange",
        "prep_watershed",
        "run_watershed",
        "ensure_totalwatsed3",
        "ensure_watershed_interchange",
        "activate_query_engine",
    ]


def test_clear_retry_runtime_locks_uses_child_path_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    calls: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        batch_runner_module,
        "get_wd",
        lambda runid: str(Path(runner.batch_runs_dir) / runid.split(";;")[-1]),
    )
    monkeypatch.setattr(
        batch_runner_module,
        "nodir_maintenance_lock_scope_token",
        lambda wd, root, *, scope: f"{scope}:{wd}:{root}",
    )

    def _clear(wd: str, root: str, *, scope: str, scope_token: str):
        calls.append((wd, root, scope, scope_token))
        if root == "climate":
            return [{"key": "nodb-lock:path-scope:abc:runtime-paths/climate"}]
        return []

    monkeypatch.setattr(batch_runner_module, "nodir_clear_runtime_locks_for_scope", _clear)

    cleared = runner.clear_retry_runtime_locks([_feature("WA-174")])

    run_wd = str(Path(runner.batch_runs_dir) / "WA-174")
    assert [call[1] for call in calls] == ["landuse", "soils", "climate", "watershed"]
    assert all(call[0] == run_wd for call in calls)
    assert all(call[2] == "effective_root_path" for call in calls)
    assert ("nodb-lock:path-scope:abc:runtime-paths/climate", "WA-174") == (
        cleared[0]["key"],
        cleared[0]["batch_leaf_runid"],
    )


def test_classify_batch_run_states_uses_timestamps_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    all_tasks = (
        TaskEnum.fetch_dem,
        TaskEnum.build_climate,
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
    )
    _set_timestamps(runner, "complete-old", all_tasks)
    _set_timestamps(runner, "incomplete", (TaskEnum.fetch_dem,))
    _set_timestamps(
        runner,
        "failed",
        (TaskEnum.fetch_dem, TaskEnum.build_climate),
    )
    _set_timestamps(runner, "stale-failed", all_tasks)

    failed_dir = Path(runner.batch_runs_dir) / "failed"
    (failed_dir / "run_metadata.json").write_text(
        json.dumps({"status": "failed", "error": {"message": "boom"}}),
        encoding="utf-8",
    )
    stale_dir = Path(runner.batch_runs_dir) / "stale-failed"
    (stale_dir / "run_metadata.json").write_text(
        json.dumps({"status": "failed", "error": {"message": "old boom"}}),
        encoding="utf-8",
    )

    features = [
        _feature("complete-old"),
        _feature("incomplete"),
        _feature("failed"),
        _feature("missing"),
        _feature("stale-failed"),
    ]

    states = runner.classify_batch_run_states(features)

    assert states["complete-old"]["status"] == "complete"
    assert states["complete-old"]["retry_eligible"] is False
    assert states["complete-old"]["metadata_status"] is None

    assert states["incomplete"]["status"] == "incomplete"
    assert states["incomplete"]["retry_eligible"] is True
    assert states["incomplete"]["missing_tasks"] == [
        "build_climate",
        "run_wepp_hillslopes",
        "run_wepp_watershed",
    ]

    assert states["failed"]["status"] == "failed"
    assert states["failed"]["retry_eligible"] is True
    assert states["failed"]["metadata_status"] == "failed"

    assert states["missing"]["status"] == "missing"
    assert states["missing"]["retry_eligible"] is True

    assert states["stale-failed"]["status"] == "complete"
    assert states["stale-failed"]["retry_eligible"] is False
    assert states["stale-failed"]["metadata_stale"] is True


def test_retry_eligible_watershed_features_skips_completed_old_style_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    all_tasks = (
        TaskEnum.fetch_dem,
        TaskEnum.build_climate,
        TaskEnum.run_wepp_hillslopes,
        TaskEnum.run_wepp_watershed,
    )
    _set_timestamps(runner, "complete-old", all_tasks)
    _set_timestamps(runner, "failed", (TaskEnum.fetch_dem,))
    (Path(runner.batch_runs_dir) / "failed" / "run_metadata.json").write_text(
        json.dumps({"status": "failed"}),
        encoding="utf-8",
    )
    features = [_feature("complete-old"), _feature("failed"), _feature("missing")]

    selected = runner.retry_eligible_watershed_features(features)

    assert [feature.runid for feature in selected] == ["failed", "missing"]


def test_classify_batch_run_states_skips_absent_optional_timeseries_tasks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    runner._run_directives[TaskEnum.fetch_rap_ts] = True
    runner._run_directives[TaskEnum.fetch_openet_ts] = True
    _set_timestamps(
        runner,
        "complete-without-optional-mods",
        (
            TaskEnum.fetch_dem,
            TaskEnum.build_climate,
            TaskEnum.run_wepp_hillslopes,
            TaskEnum.run_wepp_watershed,
        ),
    )

    state = runner.classify_batch_run_state(_feature("complete-without-optional-mods"))

    assert state["status"] == "complete"
    assert state["retry_eligible"] is False
    assert TaskEnum.fetch_rap_ts.value not in state["enabled_tasks"]
    assert TaskEnum.fetch_openet_ts.value not in state["enabled_tasks"]


def test_classify_batch_run_state_rejects_invalid_leaf_runid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)

    state = runner.classify_batch_run_state(_feature("../_base"))

    assert state["status"] == "invalid"
    assert state["retry_eligible"] is False
    assert state["retry_reason"] == "invalid_runid"
    assert state["run_wd"] is None


def test_generate_runstate_cli_report_omits_retry_status_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner(tmp_path, monkeypatch)
    _set_timestamps(runner, "WA-174", (TaskEnum.fetch_dem,))
    monkeypatch.setattr(runner, "get_watershed_features_lpt", lambda: [_feature("WA-174")])

    report = runner.generate_runstate_cli_report()

    assert report.startswith("WA-174 ")
    assert "incomplete" not in report
    assert "retry" not in report
    assert TaskEnum.fetch_dem.emoji() in report


class _DummyJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id
        self.meta: dict[str, object] = {}
        self.saves = 0

    def save(self) -> None:
        self.saves += 1


class _DummyRedis:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_run_batch_rq_enqueues_only_retry_eligible_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_job = _DummyJob("parent")
    monkeypatch.setattr(batch_rq, "get_current_job", lambda: parent_job)
    monkeypatch.setattr(batch_rq.redis, "Redis", lambda **kwargs: _DummyRedis())
    monkeypatch.setattr(batch_rq, "_active_batch_job_summaries", lambda *args, **kwargs: [])

    features = [_feature("complete"), _feature("failed"), _feature("missing")]
    cleared_runids: list[str] = []

    class _Runner:
        wd = "/tmp/batch/demo"
        rq_job_ids: dict[str, str] = {}

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            self.rq_job_ids[key] = job_id

        def get_watershed_collection(self):
            return SimpleNamespace(runid_template="{id}", runid_template_is_valid=True)

        def get_watershed_features_lpt(self):
            return features

        def is_task_enabled(self, task: TaskEnum) -> bool:
            return task is not TaskEnum.if_exists_rmtree

        def classify_batch_run_states(self, watershed_features=None):
            return {
                "complete": {"status": "complete", "retry_eligible": False},
                "failed": {"status": "failed", "retry_eligible": True},
                "missing": {"status": "missing", "retry_eligible": True},
            }

        def summarize_batch_run_states(self, states):
            return {"total": len(states), "complete": 1, "failed": 1, "missing": 1}

        def clear_retry_runtime_locks(self, watershed_features):
            cleared_runids.extend(str(wf.runid) for wf in watershed_features)
            return []

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )

    enqueue_calls: list[dict[str, object]] = []

    class _Queue:
        def __init__(self, name: str, connection=None) -> None:
            assert name == "batch"

        def enqueue_call(self, func, args=(), timeout=None, depends_on=None):
            job = _DummyJob(f"job-{len(enqueue_calls) + 1}")
            enqueue_calls.append(
                {
                    "func": func,
                    "args": args,
                    "timeout": timeout,
                    "depends_on": depends_on,
                    "job": job,
                }
            )
            return job

    monkeypatch.setattr(batch_rq, "Queue", _Queue)
    published: list[str] = []
    monkeypatch.setattr(
        batch_rq.StatusMessenger,
        "publish",
        lambda _channel, message: published.append(message),
    )

    result = batch_rq.run_batch_rq("demo")

    watershed_calls = [
        call for call in enqueue_calls if call["func"] is batch_rq.run_batch_watershed_rq
    ]
    assert [call["args"][1].runid for call in watershed_calls] == ["failed", "missing"]
    assert result["final_job_id"] == enqueue_calls[-1]["job"].id
    assert result["enqueued"] == 2
    assert result["selection"]["enqueued"] == 2
    json.dumps(result)
    assert enqueue_calls[-1]["depends_on"] == [call["job"] for call in watershed_calls]
    assert parent_job.meta["batch_run_selection"]["enqueued"] == 2
    assert parent_job.meta["batch_run_selection"]["skipped"] == 1
    assert cleared_runids == ["failed", "missing"]
    assert any("STATUS run selection total=3 enqueued=2 skipped=1" in msg for msg in published)


def test_run_batch_rq_full_rerun_enqueues_all_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(batch_rq, "get_current_job", lambda: _DummyJob("parent"))
    monkeypatch.setattr(batch_rq.redis, "Redis", lambda **kwargs: _DummyRedis())
    monkeypatch.setattr(batch_rq, "_active_batch_job_summaries", lambda *args, **kwargs: [])
    features = [_feature("complete"), _feature("failed"), _feature("missing")]
    cleared_runids: list[str] = []

    class _Runner:
        rq_job_ids: dict[str, str] = {}

        def set_rq_job_id(self, key: str, job_id: str) -> None:
            self.rq_job_ids[key] = job_id

        def get_watershed_collection(self):
            return SimpleNamespace(runid_template="{id}", runid_template_is_valid=True)

        def get_watershed_features_lpt(self):
            return features

        def is_task_enabled(self, task: TaskEnum) -> bool:
            return task is TaskEnum.if_exists_rmtree

        def classify_batch_run_states(self, watershed_features=None):
            raise AssertionError("full rerun should not classify existing run state")

        def summarize_batch_run_states(self, states):
            raise AssertionError("full rerun should not summarize existing run state")

        def clear_retry_runtime_locks(self, watershed_features):
            cleared_runids.extend(str(wf.runid) for wf in watershed_features)
            return []

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )

    enqueue_calls: list[dict[str, object]] = []

    class _Queue:
        def __init__(self, name: str, connection=None) -> None:
            assert name == "batch"

        def enqueue_call(self, func, args=(), timeout=None, depends_on=None):
            job = _DummyJob(f"job-{len(enqueue_calls) + 1}")
            enqueue_calls.append({"func": func, "args": args, "job": job})
            return job

    monkeypatch.setattr(batch_rq, "Queue", _Queue)
    monkeypatch.setattr(batch_rq.StatusMessenger, "publish", lambda *_args: None)

    batch_rq.run_batch_rq("demo")

    watershed_calls = [
        call for call in enqueue_calls if call["func"] is batch_rq.run_batch_watershed_rq
    ]
    assert [call["args"][1].runid for call in watershed_calls] == [
        "complete",
        "failed",
        "missing",
    ]
    assert cleared_runids == ["complete", "failed", "missing"]


def test_run_batch_rq_raises_when_batch_jobs_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(batch_rq, "get_current_job", lambda: _DummyJob("parent"))
    monkeypatch.setattr(
        batch_rq,
        "_active_batch_job_summaries",
        lambda *args, **kwargs: ["job-2:started:run_batch_watershed_rq"],
    )

    class _Runner:
        def get_watershed_collection(self):
            raise AssertionError("run selection should not be reached")

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )
    published: list[str] = []
    monkeypatch.setattr(
        batch_rq.StatusMessenger,
        "publish",
        lambda _channel, message: published.append(message),
    )

    with pytest.raises(RuntimeError, match="jobs are active"):
        batch_rq.run_batch_rq("demo")

    assert any("EXCEPTION run_batch_rq(demo)" in message for message in published)


def test_delete_batch_rq_checks_active_jobs_before_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_job = _DummyJob("delete-parent")
    batch_dir = tmp_path / "demo"
    (batch_dir / "runs" / "WA-38").mkdir(parents=True)
    monkeypatch.setattr(batch_rq, "get_current_job", lambda: parent_job)
    monkeypatch.setattr(
        batch_rq,
        "_active_batch_job_summaries",
        lambda *args, **kwargs: ["job-2:started:run_batch_watershed_rq"],
    )
    cleanup_calls: list[str] = []
    monkeypatch.setattr(
        batch_rq,
        "_cleanup_batch_run_cache_and_locks",
        lambda runid: cleanup_calls.append(runid),
    )
    monkeypatch.setattr(batch_rq.StatusMessenger, "publish", lambda *_args: None)

    class _Runner:
        wd = str(batch_dir)

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )

    with pytest.raises(RuntimeError, match="jobs are active"):
        batch_rq.delete_batch_rq("demo")

    assert cleanup_calls == []


def test_run_batch_watershed_rq_writes_success_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "WA-38"
    run_dir.mkdir(parents=True)
    (run_dir / "run_metadata.json").write_text(
        json.dumps({"status": "failed", "error": {"message": "old failure"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(batch_rq, "get_current_job", lambda: _DummyJob("job-leaf"))
    monkeypatch.setattr(batch_rq, "get_wd", lambda _runid: str(run_dir))
    monkeypatch.setattr(batch_rq.StatusMessenger, "publish", lambda *_args: None)

    class _Runner:
        base_wd = str(tmp_path / "_base")
        rq_job_ids: dict[str, str] = {}

        def run_batch_project(self, watershed_feature, job_id=None):
            return ()

        def is_task_enabled(self, task: TaskEnum) -> bool:
            return False

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )
    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", _FakeRedisPrep.getInstance)
    _FakeRedisPrep.timestamps_by_wd[str(run_dir)] = {
        TaskEnum.fetch_dem.value: 1,
        TaskEnum.run_wepp_hillslopes.value: 2,
    }

    status, elapsed = batch_rq.run_batch_watershed_rq("demo", _feature("WA-38"))

    assert status is True
    assert elapsed >= 0
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "success"
    assert metadata["runid"] == "batch;;demo;;WA-38"
    assert metadata["batch_name"] == "demo"
    assert metadata["rq_job_id"] == "job-leaf"
    assert "error" not in metadata
    assert metadata["task_status"][TaskEnum.fetch_dem.value] == 1


def test_run_batch_watershed_rq_task_status_failure_is_metadata_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = tmp_path / "WA-39"
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(batch_rq, "get_current_job", lambda: _DummyJob("job-leaf"))
    monkeypatch.setattr(batch_rq, "get_wd", lambda _runid: str(run_dir))
    monkeypatch.setattr(batch_rq.StatusMessenger, "publish", lambda *_args: None)

    class _Runner:
        base_wd = str(tmp_path / "_base")
        rq_job_ids: dict[str, str] = {}

        def run_batch_project(self, watershed_feature, job_id=None):
            return ()

        def is_task_enabled(self, task: TaskEnum) -> bool:
            return False

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )
    calls = 0

    def _get_prep(_wd: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _FakeRedisPrep(str(run_dir))
        raise json.JSONDecodeError("bad", "{}", 0)

    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", _get_prep)

    status, elapsed = batch_rq.run_batch_watershed_rq("demo", _feature("WA-39"))

    assert status is True
    assert elapsed >= 0
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "success"
    assert metadata["task_status"] == {}
    assert metadata["metadata_warnings"]


def test_final_batch_complete_publishes_failure_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(batch_rq, "get_current_job", lambda: _DummyJob("final"))
    monkeypatch.setattr(batch_rq, "send_discord_message", None)
    published: list[str] = []
    monkeypatch.setattr(
        batch_rq.StatusMessenger,
        "publish",
        lambda _channel, message: published.append(message),
    )

    class _Runner:
        def classify_batch_run_states(self):
            return {
                "complete": {"status": "complete", "retry_eligible": False},
                "failed": {"status": "failed", "retry_eligible": True},
            }

        def summarize_batch_run_states(self, states):
            return {
                "total": 2,
                "complete": 1,
                "failed": 1,
                "incomplete": 0,
                "missing": 0,
                "invalid": 0,
                "retry_eligible": 1,
                "metadata_stale": 0,
                "metadata_error": 0,
                "prep_error": 0,
            }

    monkeypatch.setattr(
        batch_rq.BatchRunner,
        "getInstanceFromBatchName",
        lambda _batch_name: _Runner(),
    )

    batch_rq._final_batch_complete_rq("demo")

    assert any("STATUS run summary total=2 complete=1 failed=1" in message for message in published)
    assert any("TRIGGER batch BATCH_RUN_COMPLETED_WITH_FAILURES" in message for message in published)
    assert any("TRIGGER batch BATCH_RUN_COMPLETED" in message for message in published)
