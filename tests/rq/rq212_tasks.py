"""Importable jobs and real worker entry point for isolated RQ lifecycle tests."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time


def lifecycle_job(*, operation="success", marker="", prerequisite=None, terminal_prerequisite=None, fail_attempts=0):
    from rq import get_current_job
    from rq.job import Job

    job = get_current_job()
    connection = job.connection
    attempt = connection.incr(marker + ":attempts")
    connection.rpush(marker + ":pids", os.getpid())
    connection.set(marker + ":started", os.getpid())
    if prerequisite:
        parent = Job.fetch(prerequisite, connection=connection)
        if parent.get_status(refresh=True) != "finished":
            raise AssertionError("strict child executed without successful prerequisite")
        if parent.return_value() != {"attempt": 1, "value": 42}:
            raise AssertionError("prerequisite result was not retained")
    if terminal_prerequisite:
        parent = Job.fetch(terminal_prerequisite, connection=connection)
        if parent.get_status(refresh=True) not in {"finished", "failed", "stopped"}:
            raise AssertionError("finalizer ran before the prerequisite was terminal")
    if operation == "fail" or attempt <= fail_attempts:
        raise RuntimeError("rq212 injected attempt failure")
    if operation == "hold":
        deadline = time.monotonic() + 40
        while not connection.get(marker + ":release"):
            if time.monotonic() >= deadline:
                raise RuntimeError("test controller did not release job")
            time.sleep(0.02)
    return {"attempt": attempt, "value": 42}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("socket")
    parser.add_argument("queue")
    parser.add_argument("audit")
    parser.add_argument("--pool", action="store_true")
    parser.add_argument("--burst", action="store_true")
    parser.add_argument("--scheduler", action="store_true")
    parser.add_argument("--maintenance", action="store_true")
    parser.add_argument("--dequeue-and-crash", action="store_true")
    args = parser.parse_args()
    import redis
    from rq import Queue
    from rq.worker_pool import WorkerPool
    def audit(event, values):
        if event == "socket.connect" and isinstance(values[1], tuple):
            with Path(args.audit).open("a") as stream:
                stream.write(json.dumps({"event": event, "address": str(values[1])}) + "\n")
            raise RuntimeError("outbound network attempted by isolated worker")

    sys.addaudithook(audit)
    from wepppy.config import redis_settings

    def isolated_redis_kwargs(_db, *, decode_responses=None, extra=None):
        # NoDb's import-time pools pass `extra`; direct clients do not. Configure
        # both real Redis entry points for this test's Unix socket and database.
        options = {"db": 2, "decode_responses": bool(decode_responses)}
        if extra is not None:
            options.update({key: value for key, value in extra.items()
                            if key not in {"socket_keepalive", "socket_keepalive_options", "socket_connect_timeout"}})
            options.update(connection_class=redis.UnixDomainSocketConnection, path=args.socket)
        else:
            options["unix_socket_path"] = args.socket
        return options

    redis_settings.redis_connection_kwargs = isolated_redis_kwargs
    from wepppy.nodb.status_messenger import StatusMessenger
    from wepppy.rq.rq_worker import WepppyRqWorker

    if os.getenv('RQ_WEBHOOK_PROFILE_HOOKS'):
        from wepppy.rq import webhook_hooks
        import functools
        def timed(name, function):
            @functools.wraps(function)
            def measured(*args, **kwargs):
                start = time.monotonic()
                try:
                    return function(*args, **kwargs)
                finally:
                    print('WEBHOOK_TIMING ' + json.dumps({'hook': name, 'seconds': time.monotonic() - start}), flush=True)
            return measured
        for name in ('begin_attempt', 'execution_returned', 'execution_exited', '_append_receipt'):
            setattr(webhook_hooks, name, timed(name, getattr(webhook_hooks, name)))

    connection = redis.Redis(unix_socket_path=args.socket, db=2)
    StatusMessenger._client = connection
    queue = Queue(args.queue, connection=connection)
    if args.dequeue_and_crash:
        assert Queue.dequeue_any([queue], timeout=1, connection=connection)
        os._exit(72)
    if args.pool:
        WorkerPool([queue], connection=connection, num_workers=1,
                   worker_class=WepppyRqWorker).start(burst=args.burst)
    else:
        worker = WepppyRqWorker([queue], connection=connection,
                                job_monitoring_interval=1, maintenance_interval=1)
        if args.maintenance:
            worker.clean_registries()
        else:
            worker.work(burst=args.burst, with_scheduler=args.scheduler)


if __name__ == "__main__":
    main()
