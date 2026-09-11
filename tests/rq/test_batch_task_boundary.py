"""Real RQ transitions on a disposable Redis server; never use the live queue."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest
import redis
from rq import Queue, SimpleWorker
from rq.job import Job, JobStatus
from rq.registry import DeferredJobRegistry, StartedJobRegistry

from wepppy.rq import batch_rq
from wepppy.rq.cancel_job import _cancel_job_recursive
from wepppy.rq.job_id import new_rq_job_id
from wepppy.nodb.redis_prep import TaskEnum

pytestmark = pytest.mark.integration


@pytest.fixture
def isolated_rq(tmp_path, monkeypatch):
    monkeypatch.setattr(redis, "Redis", redis.StrictRedis)
    external_socket = os.environ.get("BATCH_BOUNDARY_TEST_REDIS_SOCKET")
    if external_socket:
        connection = redis.Redis(unix_socket_path=external_socket)
        assert connection.get("batch-boundary-test-server") == b"disposable"
        before = set(connection.scan_iter("rq:job:*"))
        try:
            yield connection
        finally:
            # Cancel only jobs created by this test; retain all job evidence.
            for key in set(connection.scan_iter("rq:job:*")) - before:
                job_id = key.decode().removeprefix("rq:job:")
                if ":" not in job_id:
                    job = Job.fetch(job_id, connection=connection)
                    if job.get_status() in {JobStatus.QUEUED, JobStatus.DEFERRED, JobStatus.STARTED}:
                        job.cancel()
            connection.close()
        return
    executable = shutil.which("redis-server")
    if executable is None:
        pytest.skip("redis-server executable required for isolated RQ integration")
    socket_path = tmp_path / "redis.sock"
    # No TCP listener, persistence or access to the Compose Redis database.
    process = subprocess.Popen(
        [executable, "--port", "0", "--unixsocket", str(socket_path),
         "--save", "", "--appendonly", "no"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    connection = redis.Redis(unix_socket_path=str(socket_path))
    try:
        for _ in range(100):
            try:
                connection.ping()
                break
            except redis.ConnectionError:
                time.sleep(0.01)
        else:
            pytest.fail("isolated Redis did not start")
        yield connection
    finally:
        connection.close()
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture
def workflow(isolated_rq, tmp_path, monkeypatch):
    connection = isolated_rq
    queue = Queue("batch", connection=connection)
    published = []
    events = []
    features = [SimpleNamespace(runid="leaf")]
    run_dir = tmp_path / "runs" / "leaf"
    class Runner:
        batch_runs_dir = str(tmp_path / "runs")
        base_wd = str(tmp_path / "_base")
        rq_job_ids = {}
        hillslope_error = False
        watershed_error = False
        selected = True

        def set_rq_job_id_fresh(self, key, value):
            self.rq_job_ids[key] = value

        def get_watershed_collection(self):
            return SimpleNamespace(runid_template="{id}", runid_template_is_valid=True)

        def get_watershed_features_lpt(self):
            return features

        def is_task_enabled(self, task):
            return False

        def classify_batch_run_states(self, *_args):
            return {f.runid: {"retry_eligible": self.selected} for f in features}

        def summarize_batch_run_states(self, *_args):
            return dict(total=len(features), complete=0, failed=0, incomplete=0,
                        missing=0, invalid=0, retry_eligible=int(self.selected))

        def clear_retry_runtime_locks(self, *_args):
            return []

        def run_batch_hillslopes(self, feature, job_id=None):
            events.append(("hillslopes", job_id))
            leaf_dir = run_dir.parent / feature.runid
            leaf_dir.mkdir(parents=True, exist_ok=True)
            (leaf_dir / "scientific-output.txt").write_text("retained hillslope output")
            if self.hillslope_error is True or self.hillslope_error == feature.runid:
                raise RuntimeError("injected hillslope failure")
            return ()

        def run_batch_watershed(self, feature, job_id=None):
            events.append(("watershed", job_id))
            assert (run_dir.parent / feature.runid / "scientific-output.txt").read_text() == "retained hillslope output"
            if self.watershed_error:
                raise RuntimeError("injected watershed failure")

    runner = Runner()
    monkeypatch.setattr(batch_rq.BatchRunner, "getInstanceFromBatchName", lambda _: runner)
    monkeypatch.setattr(batch_rq, "get_wd", lambda runid: str(run_dir.parent / runid.split(";;")[-1]))
    monkeypatch.setattr(batch_rq, "redis_connection_kwargs", lambda _: {"unix_socket_path": connection.connection_pool.connection_kwargs["path"]})
    monkeypatch.setattr(batch_rq.StatusMessenger, "publish", lambda _, msg: published.append(msg))
    monkeypatch.setattr(batch_rq, "send_discord_message", None)
    monkeypatch.setattr(batch_rq, "_collect_run_task_status", lambda _: ({}, []))
    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", lambda _: {})

    def dispatch():
        root = queue.enqueue(batch_rq.run_batch_rq, "demo")
        SimpleWorker([queue], connection=connection).work(burst=True, max_jobs=1)
        root.refresh()
        assert root.get_status() == JobStatus.FINISHED
        hills_id = root.meta.get("jobs:0,hillslopes,runid:leaf")
        water_id = root.meta.get("jobs:0,runid:leaf")
        return root, (Job.fetch(hills_id, connection=connection) if hills_id else None), (
            Job.fetch(water_id, connection=connection) if water_id else None)

    def drain(max_jobs=None):
        SimpleWorker([queue], connection=connection).work(burst=True, max_jobs=max_jobs)

    return SimpleNamespace(connection=connection, queue=queue, runner=runner, events=events,
                           published=published, run_dir=run_dir, features=features, dispatch=dispatch, drain=drain)


@pytest.mark.parametrize("failure", [None, "hillslope", "watershed"])
def test_real_two_stage_completion_and_retry(workflow, failure):
    w = workflow
    w.runner.hillslope_error = failure == "hillslope"
    w.runner.watershed_error = failure == "watershed"
    root, hills, water = w.dispatch()
    assert root.result_ttl == hills.result_ttl == -1
    assert w.connection.ttl(root.key) == -1
    assert hills.id != water.id
    assert hills.origin == water.origin == "batch"
    assert water._dependency_ids == [hills.id]
    assert water.get_status() == JobStatus.DEFERRED
    w.drain()
    hills.refresh(); water.refresh()
    if failure != "hillslope":
        assert w.connection.ttl(hills.key) == -1
    final = Job.fetch(root.meta["jobs:1,func:_final_batch_complete_rq"], connection=w.connection)
    assert final.get_status() == JobStatus.FINISHED
    assert water.return_value()[0] is (failure is None)
    assert hills.get_status() == (JobStatus.FAILED if failure == "hillslope" else JobStatus.FINISHED)
    assert [name for name, _ in w.events] == (["hillslopes"] if failure == "hillslope" else ["hillslopes", "watershed"])
    metadata = json.loads((w.run_dir / "run_metadata.json").read_text())
    assert metadata["status"] == ("success" if failure is None else "failed")
    assert sum("BATCH_WATERSHED_TASK_COMPLETED" in msg for msg in w.published) == 1
    assert not w.queue.get_job_ids()
    assert not DeferredJobRegistry("batch", connection=w.connection).get_job_ids()
    assert not StartedJobRegistry("batch", connection=w.connection).get_job_ids()
    if failure:
        w.runner.hillslope_error = w.runner.watershed_error = False
        _, retry_hills, retry_water = w.dispatch()
        assert retry_hills.id != hills.id and retry_water.id != water.id
        w.drain()
        assert retry_water.return_value()[0] is True


@pytest.mark.parametrize("corruption", ["missing", "json", "old_attempt", "symlink", "rq_mismatch"])
def test_invalid_handoff_never_runs_watershed(workflow, corruption, tmp_path):
    w = workflow
    _, hills, water = w.dispatch()
    w.drain(max_jobs=1)
    path = w.run_dir / "batch_handoff" / f"{hills.id}.json"
    if corruption == "missing":
        path.unlink()
    elif corruption == "json":
        path.write_text("{")
    elif corruption == "old_attempt":
        receipt = json.loads(path.read_text()); receipt["watershed_job_id"] = new_rq_job_id()
        path.write_text(json.dumps(receipt))
    elif corruption == "symlink":
        outside = tmp_path / "outside.json"; outside.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(outside)
    else:
        hills.refresh(); hills.meta["batch_handoff"] = {}; hills.save_meta()
    w.drain()
    assert water.return_value()[0] is False
    assert [name for name, _ in w.events] == ["hillslopes"]
    assert not DeferredJobRegistry("batch", connection=w.connection).get_job_ids()


def test_tree_cancel_between_stages_and_retry(workflow):
    w = workflow
    root, hills, water = w.dispatch()
    w.drain(max_jobs=1)
    _cancel_job_recursive(root, w.connection)
    w.drain()
    assert [name for name, _ in w.events] == ["hillslopes"]
    assert not (w.run_dir / "run_metadata.json").exists()
    assert not DeferredJobRegistry("batch", connection=w.connection).get_job_ids()
    _, _, replacement = w.dispatch()
    w.drain()
    assert replacement.return_value()[0] is True


def test_duplicate_live_submission_is_rejected(workflow):
    w = workflow
    _, hills, water = w.dispatch()
    duplicate = w.queue.enqueue(batch_rq.run_batch_rq, "demo")
    # Execute duplicate directly while the original chain remains active.
    SimpleWorker([w.queue], connection=w.connection).execute_job(duplicate, w.queue)
    assert duplicate.get_status(refresh=True) == JobStatus.FAILED
    assert "jobs are active" in duplicate.exc_info
    w.drain()
    assert water.return_value()[0] is True


def test_zero_selected_leaves_only_finalizes(workflow):
    w = workflow; w.runner.selected = False
    root, hills, water = w.dispatch()
    assert hills is water is None
    w.drain()
    assert not w.events
    assert Job.fetch(root.meta["jobs:1,func:_final_batch_complete_rq"], connection=w.connection).get_status() == JobStatus.FINISHED


@pytest.mark.parametrize("attack", ["foreign_leaf", "foreign_root", "path"])
def test_invalid_identity_failure_handler_cannot_write(workflow, attack, monkeypatch):
    w = workflow
    root, hills, water = w.dispatch()
    if attack == "foreign_leaf":
        water.meta["runid"] = "batch;;demo;;victim"
    elif attack == "foreign_root":
        root.meta["jobs:0,runid:leaf"] = new_rq_job_id(); root.save_meta()
    else:
        assert water.args[0] == "demo"  # Hydrate RQ's lazy serialized data before replacing args.
        water.args = ("demo", SimpleNamespace(runid="../victim"), hills.id)
    water.save()
    w.drain()
    assert not (w.run_dir / "run_metadata.json").exists()
    assert not (w.run_dir.parent / "victim").exists()
    assert not any(name == "watershed" for name, _ in w.events)


def test_stopped_hillslope_releases_failure_observer(workflow):
    w = workflow
    root, hills, water = w.dispatch()
    w.queue.remove(hills)
    worker = SimpleWorker([w.queue], connection=w.connection)
    worker._stopped_job_id = hills.id
    worker.handle_job_failure(hills, w.queue, exc_string="injected worker stop")
    assert hills.get_status(refresh=True) == JobStatus.STOPPED
    w.drain()
    assert water.return_value()[0] is False
    assert not w.events
    final = Job.fetch(root.meta["jobs:1,func:_final_batch_complete_rq"], connection=w.connection)
    assert final.get_status() == JobStatus.FINISHED
    assert not DeferredJobRegistry("batch", connection=w.connection).get_job_ids()


def test_receipt_publication_failure_retains_outputs_and_blocks_science(workflow, monkeypatch):
    w = workflow
    _, hills, water = w.dispatch()
    def fail_replace(*_args):
        raise OSError("injected receipt publication failure")
    monkeypatch.setattr(batch_rq.os, "replace", fail_replace)
    w.drain()
    assert hills.get_status(refresh=True) == JobStatus.FAILED
    assert water.return_value()[0] is False
    assert (w.run_dir / "scientific-output.txt").read_text() == "retained hillslope output"
    assert not list((w.run_dir / "batch_handoff").iterdir())
    assert [name for name, _ in w.events] == ["hillslopes"]


def test_omni_finalizer_is_linked_before_leaf_completion(workflow, monkeypatch):
    w = workflow
    monkeypatch.setattr(w.runner, "is_task_enabled", lambda task: task == TaskEnum.run_omni_scenarios)
    monkeypatch.setattr(batch_rq, "_reset_omni_nodb_from_base", lambda *_: None)
    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", lambda _: {str(TaskEnum.run_omni_scenarios): None})
    omni_jobs = []
    def enqueue_omni(_):
        job = w.queue.enqueue(sum, [1, 2])
        omni_jobs.append(job)
        return job
    monkeypatch.setattr(batch_rq, "run_omni_scenarios_rq", enqueue_omni)
    root, _, water = w.dispatch()
    w.drain(max_jobs=2)
    final = Job.fetch(root.meta["jobs:1,func:_final_batch_complete_rq"], connection=w.connection)
    assert set(final._dependency_ids) == {water.id, omni_jobs[0].id}
    assert final.get_status() == JobStatus.DEFERRED
    w.drain()
    assert final.get_status(refresh=True) == JobStatus.FINISHED


def test_production_worker_preserves_identity_and_forks_each_stage(workflow):
    from wepppy.rq.rq_worker import WepppyRqWorker
    w = workflow
    _, hills, water = w.dispatch()
    WepppyRqWorker([w.queue], connection=w.connection).work(burst=True, max_jobs=2)
    hills.refresh(); water.refresh()
    assert hills.get_status() == water.get_status() == JobStatus.FINISHED
    assert water.return_value()[0] is True
    assert hills.meta["runid"] == water.meta["runid"] == "batch;;demo;;leaf"
    assert hills.meta["batch_handoff"]["pid"] != water.meta["watershed_stage_started"]["pid"]
    assert hills.meta["batch_handoff"]["pid"] != os.getpid()
    w.drain()


def test_leaf_metadata_includes_hillslope_elapsed_time(workflow):
    from datetime import timedelta
    w = workflow
    _, hills, water = w.dispatch()
    w.drain(max_jobs=1)
    hills.refresh()
    hills.started_at -= timedelta(seconds=120)
    hills.save()
    w.drain()
    metadata = json.loads((w.run_dir / "run_metadata.json").read_text())
    assert metadata["duration_seconds"] >= 120
    assert metadata["started_at"].startswith(hills.started_at.isoformat()[:19])


def test_root_dispatch_failure_reconciles_before_retry(workflow, monkeypatch):
    w = workflow
    original = w.runner.set_rq_job_id_fresh
    def fail_receipt(key, value):
        if key == "final_batch_complete_rq":
            raise RuntimeError("injected dispatch failure")
        original(key, value)
    monkeypatch.setattr(w.runner, "set_rq_job_id_fresh", fail_receipt)
    root = w.queue.enqueue(batch_rq.run_batch_rq, "demo")
    w.drain()
    assert root.get_status(refresh=True) == JobStatus.FAILED
    assert not w.events
    assert batch_rq.reconcile_deferred_batch_jobs("demo", redis_conn=w.connection) == []
    assert not DeferredJobRegistry("batch", connection=w.connection).get_job_ids()
    monkeypatch.setattr(w.runner, "set_rq_job_id_fresh", original)
    _, _, water = w.dispatch()
    w.drain()
    assert water.return_value()[0] is True


@pytest.mark.parametrize("escape", [False, True])
def test_real_nodb_phase_reload_clears_only_scoped_cache(isolated_rq, tmp_path, monkeypatch, escape):
    import wepppy.nodb.base as base
    import wepppy.nodb.batch_runner as module
    import wepppy.weppcloud.utils.helpers as helpers
    from wepppy.nodb.core import Ron, Wepp
    cache = redis.StrictRedis(connection_pool=isolated_rq.connection_pool)
    monkeypatch.setattr(base, "redis_nodb_cache_client", cache)
    monkeypatch.setattr(base, "redis_lock_client", cache)
    run_dir = tmp_path / "leaf"
    run_dir.mkdir()
    monkeypatch.setattr(helpers, "get_wd", lambda _: str(run_dir))
    monkeypatch.setattr(module, "get_wd", lambda _: str(run_dir))
    Ron(str(run_dir), "0.cfg", run_group="batch", group_name="demo")
    stale = Wepp.getInstance(str(run_dir))
    with stale.locked():
        stale._boundary_test_marker = "stale"
    path = run_dir / "wepp.nodb"
    original = path.read_text()
    signature = path.stat()
    assert "stale" in original
    path.write_text(original.replace('"stale"', '"fresh"'))
    os.utime(path, ns=(signature.st_atime_ns, signature.st_mtime_ns))
    assert path.stat().st_size == signature.st_size
    assert Wepp.getInstance(str(run_dir)) is stale
    assert stale._boundary_test_marker == "stale"
    unrelated = str(tmp_path / "other" / "wepp.nodb")
    cache.set(unrelated, "preserve-other-cache")
    lock_key = stale._distributed_lock_key
    cache.set(lock_key, "foreign-owner-token")
    runner = module.BatchRunner.__new__(module.BatchRunner)
    runner.wd = str(tmp_path / "demo")
    runner._run_directives = {task: False for task in module.BatchRunner.DEFAULT_TASKS}
    monkeypatch.setattr(runner, "_get_run_logger", lambda _: batch_rq.logger)
    try:
        if escape:
            outside = tmp_path / "outside.nodb"
            path.rename(outside)
            before = outside.read_bytes()
            path.symlink_to(outside)
            with pytest.raises(ValueError, match="outside the run root"):
                runner.run_batch_watershed(SimpleNamespace(runid="leaf"))
            assert outside.read_bytes() == before
            assert cache.get(lock_key) == b"foreign-owner-token"
            return
        runner.run_batch_watershed(SimpleNamespace(runid="leaf"))
        fresh = Wepp.getInstance(str(run_dir))
        assert fresh is not stale
        assert fresh._boundary_test_marker == "fresh"
        assert cache.get(unrelated) == b"preserve-other-cache"
        assert cache.get(lock_key) == b"foreign-owner-token"
        assert not (run_dir / "ash.nodb").exists()
    finally:
        cache.delete(lock_key, unrelated)
        base.NoDbBase.cleanup_run_instances(str(run_dir))


def test_mixed_leaves_finalize_after_both_terminal_stages(workflow):
    w = workflow
    w.features.append(SimpleNamespace(runid="second"))
    w.runner.hillslope_error = "second"
    root, _, water = w.dispatch()
    other = Job.fetch(root.meta["jobs:0,runid:second"], connection=w.connection)
    w.drain()
    assert water.return_value()[0] is True
    assert other.return_value()[0] is False
    final = Job.fetch(root.meta["jobs:1,func:_final_batch_complete_rq"], connection=w.connection)
    assert final.get_status() == JobStatus.FINISHED
    assert set(final._dependency_ids) == {water.id, other.id}
    assert sum("BATCH_WATERSHED_TASK_COMPLETED" in msg for msg in w.published) == 2


def test_concurrent_omni_attachments_preserve_both_dependencies(workflow, monkeypatch):
    import multiprocessing
    from wepppy.rq.rq_worker import WepppyRqWorker
    w = workflow
    w.features.append(SimpleNamespace(runid="second"))
    monkeypatch.setattr(w.runner, "is_task_enabled", lambda task: task == TaskEnum.run_omni_scenarios)
    monkeypatch.setattr(batch_rq, "_reset_omni_nodb_from_base", lambda *_: None)
    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", lambda _: {str(TaskEnum.run_omni_scenarios): None})
    context = multiprocessing.get_context("fork")
    dispatch_barrier = context.Barrier(2, timeout=15)
    def enqueue_omni(_):
        dispatch_barrier.wait()
        return w.queue.enqueue(sum, [1, 2])
    monkeypatch.setattr(batch_rq, "run_omni_scenarios_rq", enqueue_omni)
    root, _, water = w.dispatch()
    other = Job.fetch(root.meta["jobs:0,runid:second"], connection=w.connection)
    def work():
        WepppyRqWorker([w.queue], connection=w.connection).work(burst=True)
    processes = [context.Process(target=work) for _ in range(2)]
    try:
        for process in processes: process.start()
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        w.drain()
        water.refresh(); other.refresh()
        assert water.return_value()[0] is other.return_value()[0] is True
        final = Job.fetch(root.meta["jobs:1,func:_final_batch_complete_rq"], connection=w.connection)
        assert set(final._dependency_ids) == {
            water.id, other.id, water.meta["omni_final_job_id"], other.meta["omni_final_job_id"],
        }
        assert final.get_status() == JobStatus.FINISHED
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate(); process.join(timeout=5)


def test_omni_link_failure_does_not_announce_batch_completion(workflow, monkeypatch):
    w = workflow
    monkeypatch.setattr(w.runner, "is_task_enabled", lambda task: task == TaskEnum.run_omni_scenarios)
    monkeypatch.setattr(batch_rq, "_reset_omni_nodb_from_base", lambda *_: None)
    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", lambda _: {str(TaskEnum.run_omni_scenarios): None})
    monkeypatch.setattr(batch_rq, "run_omni_scenarios_rq", lambda _: w.queue.enqueue(sum, [1, 2]))
    root, _, water = w.dispatch()
    final_id = root.meta["jobs:1,func:_final_batch_complete_rq"]
    original = Job.register_dependency
    def fail_attach(job, *args, **kwargs):
        if job.id == final_id:
            raise redis.ConnectionError("injected attachment failure")
        return original(job, *args, **kwargs)
    monkeypatch.setattr(Job, "register_dependency", fail_attach)
    w.drain()
    assert water.return_value()[0] is False
    final = Job.fetch(final_id, connection=w.connection)
    assert final.get_status() == JobStatus.FAILED
    assert not any("TRIGGER batch BATCH_RUN_COMPLETED" in msg for msg in w.published)
    root.refresh()
    assert root.meta["batch_pending_omni_links"] == [water.id]


def test_omni_lock_timeout_happens_before_submission(workflow, monkeypatch):
    w = workflow
    monkeypatch.setattr(w.runner, "is_task_enabled", lambda task: task == TaskEnum.run_omni_scenarios)
    monkeypatch.setattr(batch_rq.RedisPrep, "getInstance", lambda _: {str(TaskEnum.run_omni_scenarios): None})
    submitted = []
    monkeypatch.setattr(batch_rq, "run_omni_scenarios_rq", lambda _: submitted.append(True))
    root, _, water = w.dispatch()
    final_id = root.meta["jobs:1,func:_final_batch_complete_rq"]
    lock_key = f"batch-finalizer-link:{final_id}"
    held = w.connection.lock(lock_key, timeout=60)
    assert held.acquire(blocking=False)
    original = redis.StrictRedis.lock
    def immediate_lock(client, name, *args, **kwargs):
        if name == lock_key:
            kwargs["blocking_timeout"] = 0
        return original(client, name, *args, **kwargs)
    monkeypatch.setattr(redis.StrictRedis, "lock", immediate_lock)
    try:
        w.drain()
        assert water.return_value()[0] is False
        assert submitted == []
        assert Job.fetch(final_id, connection=w.connection).get_status() == JobStatus.FINISHED
    finally:
        held.release()
