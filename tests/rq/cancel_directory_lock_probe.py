"""Fresh-interpreter probes, using only unique run/queue keys on real Redis."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import select
import subprocess
import sys
import tempfile
import threading
import time
import uuid


class InjectedProbeFailure(Exception):
    pass


def cleanup_probe_children():
    """Independent teardown: cold-stop and reap every probe-owned descendant."""
    import psutil

    deadline = time.monotonic() + 15
    parent = psutil.Process()
    while children := parent.children():
        if time.monotonic() >= deadline:
            raise AssertionError("probe child teardown exceeded deadline")
        for child in children:
            try:
                child.kill()  # psutil verifies identity against PID reuse.
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(children, timeout=1)


def wait_for(predicate, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := predicate():
            return value
        time.sleep(0.02)
    raise AssertionError("probe observation timed out")


def spawn_writer(path):
    return subprocess.Popen(
        [sys.executable, "-m", "tests.rq.cancel_directory_lock_probe", "writer", str(path)],
        start_new_session=True,
    )


def writer(path):
    Path(str(path) + ".pid").write_text(str(os.getpid()))
    while True:
        with open(path, "a") as stream:
            stream.write("write\n")
        time.sleep(0.01)


def locked_job(runid, wd):
    from wepppy.runtime_paths.thaw_freeze import maintenance_lock, acquire_maintenance_lock

    Path(wd, "supervisor.pid").write_text(str(os.getppid()))
    with maintenance_lock(wd, "climate", purpose="cancel-regression", scope="effective_root_path_compat"):
        thread = threading.Thread(target=lambda: acquire_maintenance_lock(wd, "watershed"))
        thread.start()
        thread.join()
        # One inherited-group process and a detached-session CLIGEN analogue.
        if os.fork() == 0:
            acquire_maintenance_lock(wd, "soils")
            writer(Path(wd) / "pool")
        spawn_writer(Path(wd) / "detached")
        Path(wd, "ready").touch()
        while True:
            time.sleep(1)


def crashing_job(runid, wd):
    Path(wd, "crashed-supervisor.pid").write_text(str(os.getppid()))
    spawn_writer(Path(wd) / "crashed-writer")
    wait_for(lambda: Path(wd, "crashed-writer.pid").exists())
    os.kill(os.getpid(), signal.SIGKILL)


def processes():
    from wepppy.rq.directory_locks import prepare_containment, terminate_adopted_writers, _child_pids

    with tempfile.TemporaryDirectory() as wd:
        prepare_containment()
        horse = os.fork()
        if horse == 0:
            os.setsid()
            spawn_writer(Path(wd) / "detached")
            os._exit(0)
        os.waitpid(horse, 0)
        pid = int(wait_for(lambda: Path(wd, "detached.pid").read_text()
                          if Path(wd, "detached.pid").exists() else None))
        terminate_adopted_writers(lambda: None, 1, {})
        assert not _child_pids()
        assert not Path(f"/proc/{pid}").exists()
        size = Path(wd, "detached").stat().st_size
        time.sleep(0.05)
        assert Path(wd, "detached").stat().st_size == size


def connection():
    import redis
    from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
    return redis.Redis(**redis_connection_kwargs(RedisDB.RQ))


def worker(queue_name):
    from rq import Queue
    from rq.worker_pool import WorkerPool
    from wepppy.rq.rq_worker import WepppyRqWorker
    conn = connection()
    failure = os.environ.get("RQ_CANCEL_TEST_DIAGNOSTIC_FAILURE")
    if failure:
        import redis
        from types import SimpleNamespace
        from wepppy.rq import directory_locks
        original = directory_locks.record_cleanup
        class Pipeline:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def watch(self, *_args):
                error = redis.WatchError if failure == "watch" else redis.ConnectionError
                raise error("injected diagnostic transport failure")
        def failed_diagnostics(job, execution_id, state, **details):
            proxy = SimpleNamespace(id=job.id, key=job.key,
                                    connection=SimpleNamespace(pipeline=Pipeline))
            original(proxy, execution_id, state, **details)
        directory_locks.record_cleanup = failed_diagnostics
    # Use the production worker-pool orchestration, including scheduler startup
    # and automatic supervisor replacement after retirement.
    WorkerPool([Queue(queue_name, connection=conn)], connection=conn,
               num_workers=1, worker_class=WepppyRqWorker).start(burst=False)


def ownership():
    from wepppy.runtime_paths import thaw_freeze as locks
    with tempfile.TemporaryDirectory(prefix="rq-cancel-locks-") as wd:
        client = locks._runtime_lock_redis_client()
        saved = []
        try:
            legacy = locks.acquire_maintenance_lock(wd, "landuse")
            saved.extend(legacy.lock_keys)
            with locks.maintenance_lock_execution("same-job") as execution_a:
                old = locks.acquire_maintenance_lock(wd, "climate", scope="effective_root_path_compat")
                saved.extend(old.lock_keys)
            assert locks.release_execution_locks("other-job", execution_a) == []
            locks.release_maintenance_lock(old)
            with locks.maintenance_lock_execution("same-job") as execution_b:
                new = locks.acquire_maintenance_lock(wd, "climate", scope="effective_root_path_compat")
            assert execution_a != execution_b
            assert locks.release_execution_locks("same-job", execution_a) == []
            assert all(client.get(key) for key in new.lock_keys)
            assert set(locks.release_execution_locks("same-job", execution_b)) == set(new.lock_keys)
            assert client.get(legacy.key)
            assert locks.release_execution_locks("same-job", execution_b) == []
            with locks.maintenance_lock_execution("same-job") as execution_c:
                raced = locks.acquire_maintenance_lock(wd, "climate")
                saved.extend(raced.lock_keys)
            original_delete = locks._delete_if_raw_matches
            replacement = json.loads(raced.payload)
            replacement["token"] = uuid.uuid4().hex
            replacement["rq_execution_id"] = uuid.uuid4().hex
            def replace_before_lua(key_client, key, raw):
                key_client.set(key, json.dumps(replacement), ex=30)
                return original_delete(key_client, key, raw)
            locks._delete_if_raw_matches = replace_before_lua
            try:
                assert locks.release_execution_locks("same-job", execution_c) == []
                assert json.loads(client.get(raced.key)) == replacement
            finally:
                locks._delete_if_raw_matches = original_delete
            replacement["rq_execution_id"] = execution_c
            replacement["token"] = ""
            client.set(raced.key, json.dumps(replacement), ex=30)
            try:
                locks.release_execution_locks("same-job", execution_c)
            except ValueError as exc:
                assert "missing token" in str(exc)
            else:
                raise AssertionError("malformed owned token was silently accepted")
            assert client.get(raced.key)
            replacement["token"] = uuid.uuid4().hex
            client.set(raced.key, json.dumps(replacement), ex=30)
            original_eval = client.eval
            def unavailable_eval(*_args):
                import redis
                raise redis.ConnectionError("injected lock-Redis release failure")
            client.eval = unavailable_eval
            try:
                try:
                    locks.release_execution_locks("same-job", execution_c)
                except RuntimeError as exc:
                    assert raced.key in str(exc)
                else:
                    raise AssertionError("lock-Redis release failure was hidden")
                assert client.get(raced.key)
            finally:
                client.eval = original_eval
        finally:
            for key in saved:
                client.delete(key)


def cancel(queued=False, diagnostic_failure=None, crash_first=False, early_failure=False):
    from rq import Queue
    from wepppy.rq.cancel_job import cancel_jobs
    from wepppy.runtime_paths import thaw_freeze as locks

    conn = connection()
    queue = Queue("cancel-probe-" + uuid.uuid4().hex, connection=conn)
    with tempfile.TemporaryDirectory(prefix="rq-cancel-locks-",
                                     dir=os.environ.get("RQ_CANCEL_TEST_RUN_PARENT")) as wd:
        runid = Path(wd).name
        from wepppy.rq.directory_locks import prepare_containment
        prepare_containment()  # Teardown also adopts escaped probe descendants.
        # Outside the dedicated worker: neither its process nor its lock belongs
        # to the canceled execution.
        crashed = None
        job = None
        runner = None
        writer_fds = []
        scheduler_fd = None
        orphan_fd = None
        try:
            unrelated = spawn_writer(Path(wd) / "unrelated")
            legacy = locks.acquire_maintenance_lock(wd, "landuse")
            if crash_first:
                crashed = queue.enqueue("tests.rq.cancel_directory_lock_probe.crashing_job", runid, wd)
            job = queue.enqueue("tests.rq.cancel_directory_lock_probe.locked_job", runid, wd)
            if not queued:
                env = os.environ.copy()
                if diagnostic_failure:
                    env["RQ_CANCEL_TEST_DIAGNOSTIC_FAILURE"] = diagnostic_failure
                runner = subprocess.Popen(
                    [sys.executable, "-m", "tests.rq.cancel_directory_lock_probe", "worker", queue.name],
                    env=env,
                )
                if crash_first:
                    wait_for(lambda: crashed.get_status(refresh=True) == "failed")
                    old_supervisor = int(Path(wd, "crashed-supervisor.pid").read_text())
                    wait_for(lambda: not Path(f"/proc/{old_supervisor}").exists())
                    assert runner.poll() is None
                    orphan_pid = int(Path(wd, "crashed-writer.pid").read_text())
                    orphan_fd = os.pidfd_open(orphan_pid)
                wait_for(lambda: all(Path(wd, name + ".pid").exists() for name in ("pool", "detached")))
                wait_for(lambda: Path(wd, "ready").exists())
                execution_id = job.get_meta(refresh=True)["directory_lock_execution_id"]
                owned_keys = [locks.maintenance_lock_key(wd, "climate", scope="effective_root_path_compat")]
                owned_keys.extend(locks.maintenance_lock_key(wd, root) for root in ("soils", "watershed"))
                for key in owned_keys:
                    payload = json.loads(locks._runtime_lock_redis_client().get(key))
                    assert (payload["rq_job_id"], payload["rq_execution_id"]) == (job.id, execution_id)
                if early_failure:
                    raise InjectedProbeFailure("injected before cancellation/pidfd capture")
                writer_fds = [os.pidfd_open(int(Path(wd, name + ".pid").read_text()))
                              for name in ("pool", "detached")]
                horse_pid = job.get_meta(refresh=True)["pid"]
                supervisor_pid = int(Path(wd, "supervisor.pid").read_text())
                if crash_first:
                    assert supervisor_pid != old_supervisor
                children = set(map(int, Path(f"/proc/{supervisor_pid}/task/{supervisor_pid}/children").read_text().split()))
                scheduler_pid, = children - {horse_pid}
                scheduler_fd = os.pidfd_open(scheduler_pid)
            assert cancel_jobs(job.id) == {"status": "ok"}
            if queued:
                assert job.get_status(refresh=True) == "canceled"
            else:
                if diagnostic_failure:
                    wait_for(lambda: not any(locks._runtime_lock_redis_client().get(key) for key in owned_keys))
                else:
                    wait_for(lambda: job.get_meta(refresh=True).get("directory_lock_cleanup", {}).get("state") == "complete")
                assert job.get_status(refresh=True) == "stopped"
                assert runner.poll() is None
                assert not select.select([scheduler_fd], [], [], 0)[0], "cleanup killed the RQ scheduler"
                for name in ("pool", "detached"):
                    pid = int(Path(wd, name + ".pid").read_text())
                    assert not Path(f"/proc/{pid}").exists()
                with locks.maintenance_lock(wd, "climate", purpose="immediate-rebuild", scope="effective_root_path_compat"):
                    pass
                for root in ("soils", "watershed"):
                    assert not locks._runtime_lock_redis_client().get(locks.maintenance_lock_key(wd, root))
            assert unrelated.poll() is None
            if orphan_fd is not None:
                assert not select.select([orphan_fd], [], [], 0)[0], "later cancel killed an earlier execution's writer"
            assert locks._runtime_lock_redis_client().get(legacy.key)
            assert cancel_jobs(job.id) == {"status": "ok"}
            print(json.dumps({"passed": True, "job_id": job.id, "uid": os.getuid(),
                              "gid": os.getgid(), "cleanup": job.get_meta(refresh=True).get("directory_lock_cleanup")}))
        finally:
            # Warm shutdown is safe only after terminal handling. On a probe
            # failure the infinite workhorse needs unconditional cold teardown.
            try:
                if runner is not None and runner.poll() is None and not early_failure:
                    runner.terminate()
                    try:
                        runner.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass  # Cold-stop/reap below is unconditional.
            finally:
                cleanup_probe_children()
            if scheduler_fd is not None:
                os.close(scheduler_fd)
            if orphan_fd is not None:
                os.close(orphan_fd)
            for fd in writer_fds:
                try:
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                finally:
                    os.close(fd)
            locks.clear_runtime_locks(Path(wd).name)
            if job is not None:
                job.delete()
            if crashed is not None:
                crashed.delete()
            from rq import Worker
            for registered in Worker.all(queue=queue):
                registered.register_death()
                conn.delete(registered.key)
            queue.delete(delete_jobs=True)
            from rq.scheduler import RQScheduler
            conn.delete(RQScheduler.get_locking_key(queue.name))
            assert not conn.exists(queue.key)
            assert not locks.runtime_lock_statuses(runid)


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "writer":
        writer(sys.argv[2])
    elif command == "worker":
        worker(sys.argv[2])
    elif command == "processes":
        try:
            processes()
        finally:
            cleanup_probe_children()
    elif command == "ownership":
        ownership()
    elif command == "cancel":
        cancel()
    elif command == "queued":
        cancel(queued=True)
    elif command == "cancel_watch":
        cancel(diagnostic_failure="watch")
    elif command == "cancel_redis":
        cancel(diagnostic_failure="redis")
    elif command == "crash_then_cancel":
        cancel(crash_first=True)
    elif command == "early_failure":
        try:
            cancel(early_failure=True)
        except InjectedProbeFailure:
            print(json.dumps({"passed": True, "early_failure_cleaned": True}))
        else:
            raise AssertionError("failure injection was not exercised")
    else:
        raise ValueError(command)
