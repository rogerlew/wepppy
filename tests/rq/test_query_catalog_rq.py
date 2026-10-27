"""Real disposable Redis admission and filesystem refresh recovery."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from uuid import uuid4

import pytest
from rq import Queue, SimpleWorker
from rq.job import JobStatus

from tests.rq.test_batch_task_boundary import isolated_rq
from wepppy.rq import query_catalog_rq as tasks
from wepppy.query_engine import catalog_refresh as core

pytestmark = pytest.mark.integration


class CatalogWorker(SimpleWorker):
    def register_birth(self):
        super().register_birth()
        self.connection.hset(self.key, tasks.WORKER_FIELD, json.dumps(tasks.catalog_worker_configuration()))


@pytest.fixture
def catalog_queue(tmp_path, monkeypatch, isolated_rq):
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setenv("QUERY_CATALOG_ROOTS_JSON", json.dumps([{
        "path": str(root), "namespace": "test-" + uuid4().hex,
        "coordination": str(tmp_path / "coordination"), "layout": "flat",
    }]))
    monkeypatch.setenv("QUERY_CATALOG_REFRESH_ENABLED", "true")
    queue = Queue("batch", connection=isolated_rq)
    worker = CatalogWorker([queue], connection=isolated_rq, name="query-catalog-test-" + uuid4().hex)
    worker.register_birth()
    worker.set_state("idle")
    companions = [CatalogWorker([queue], connection=isolated_rq, name="query-catalog-companion-" + uuid4().hex) for _ in range(7)]
    for companion in companions:
        companion.register_birth()
        companion.set_state("idle")
    from wepppy.rq._query_catalog_admission import initialize_admission, LEDGER_KEY, PAUSE_KEY
    # This fixture owns the disposable Redis server; prior test jobs are deleted.
    isolated_rq.delete(LEDGER_KEY, PAUSE_KEY)
    for owned_key in isolated_rq.scan_iter("query-catalog:pilot:*"):
        isolated_rq.delete(owned_key)
    initialize_admission(isolated_rq, queue)
    worker._catalog_test_companions = companions
    try:
        yield root, queue, worker
    finally:
        worker.register_death()
        for companion in companions:
            companion.register_death()
        queue.delete(delete_jobs=True)


def project(root, name="sample"):
    path = root / name
    path.mkdir()
    (path / "ron.nodb").write_text("{}")
    (path / "values.csv").write_text("value\n1\n")
    return path


def drain(queue, worker):
    worker.register_death()
    worker.work(burst=True)


def discover(queue, worker):
    """Exercise the real asynchronous inventory job before scope admission."""
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state("idle")


def test_concurrent_admission_coalesces_one_job(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path, "values.csv")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: tasks.enqueue_catalog_refresh(path, queue=queue), range(8)))
    assert queue.count == 1
    identifiers = {result["job_id"] for result in results if result.get("job_id")}
    assert identifiers == {queue.get_job_ids()[0]}
    assert identifiers.pop().startswith(tasks.PREFIX)
    drain(queue, worker)
    catalog = json.loads((path / "_query_engine/catalog.json").read_text())
    assert "values.csv" in {item["path"] for item in catalog["files"]}
    assert core.pending_catalog_requests(path) == []


def test_incompatible_worker_blocks_without_losing_request(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    request = core.record_catalog_refresh(path, "values.csv")
    worker.connection.hset(worker.key, tasks.WORKER_FIELD, "{}")
    result = tasks.enqueue_catalog_refresh(path, queue=queue)
    assert result["state"] == "pending"
    assert "job_id" not in result
    assert queue.count == 0
    assert core.pending_catalog_requests(path)[0]["request_id"] == request["request_id"]


def test_existing_started_job_retained_until_terminal(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    first = tasks.enqueue_catalog_refresh(path, queue=queue)
    job = queue.fetch_job(first["job_id"])
    queue.connection.lrem(queue.key, 0, job.id)  # Real workers dequeue before STARTED.
    job.set_status(JobStatus.STARTED)
    core.record_catalog_refresh(path, "values.csv")
    assert tasks.enqueue_catalog_refresh(path, queue=queue)["job_id"] == first["job_id"]
    assert queue.count == 0
    job.set_status(JobStatus.FAILED)
    replacement = tasks.enqueue_catalog_refresh(path, queue=queue)
    assert replacement["job_id"] != first["job_id"]


def test_scope_incarnation_separates_old_queued_work(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    first = tasks.enqueue_catalog_refresh(path, queue=queue)
    core.invalidate_catalog_incarnation(path)
    core.record_catalog_refresh(path)
    second = tasks.enqueue_catalog_refresh(path, queue=queue)
    assert first["job_id"] != second["job_id"]


def test_receipt_free_crash_gap_recovered_by_inventory(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    # Models the durable artifact left by death before receipt creation.
    assert not (path / "_query_engine/refresh").exists()
    discover(queue, worker)
    outcome = tasks.reconcile_query_catalogs(queue=queue)
    assert outcome["admitted"] == 1
    assert core.pending_catalog_requests(path)
    identifier = queue.get_job_ids()[0]
    drain(queue, worker)
    assert queue.fetch_job(identifier).get_status() == JobStatus.FINISHED
    assert "values.csv" in {item["path"] for item in json.loads((path / "_query_engine/catalog.json").read_text())["files"]}


def test_redis_discovery_loss_recovers_filesystem_receipts(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path, "values.csv")
    # No Redis index or admission entry exists, as after Redis restart.
    discover(queue, worker)
    assert tasks.reconcile_query_catalogs(queue=queue)["admitted"] == 1
    assert queue.count == 1


def test_explicit_suspension_is_not_retried(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    scope = core.resolve_scope(path)
    tasks.suspend_catalog_refresh(queue.connection, scope.scope_id)
    assert tasks.enqueue_catalog_refresh(path, queue=queue)["error_code"] == "query_catalog_refresh_suspended"
    assert queue.count == 0
    tasks.resume_catalog_refresh(queue.connection, scope.scope_id)
    assert tasks.enqueue_catalog_refresh(path, queue=queue)["job_id"]


def test_nested_inventory_scopes_and_bounded_resume(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    parent = project(root)
    child = parent / "_pups/omni/scenarios/child"
    child.mkdir(parents=True)
    (child / "wepp.nodb").write_text("{}")
    monkeypatch.setenv("QUERY_CATALOG_INVENTORY_LIMIT", "1")
    discover(queue, worker)
    for _ in range(8):
        tasks.reconcile_query_catalogs(queue=queue)
    assert queue.count == 2
    assert core.resolve_scope(parent).scope_id != core.resolve_scope(child).scope_id


def test_worker_does_not_publish_old_incarnation(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    result = tasks.enqueue_catalog_refresh(path, queue=queue)
    core.invalidate_catalog_incarnation(path)
    drain(queue, worker)
    assert queue.fetch_job(result["job_id"]).get_status() == JobStatus.FAILED
    assert not (path / "_query_engine/catalog.json").exists()


def test_arrival_after_worker_snapshot_gets_successor(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path, "values.csv")
    first = tasks.enqueue_catalog_refresh(path, queue=queue)["job_id"]
    original = core.refresh_catalog
    late = []

    def finish_then_invalidate(*args, **kwargs):
        result = original(*args, **kwargs)
        if not late:
            (path / "later.csv").write_text("changed\n2\n")
            late.append(core.record_catalog_refresh(path, "later.csv"))
        return result

    monkeypatch.setattr(core, "refresh_catalog", finish_then_invalidate)
    drain(queue, worker)
    assert queue.fetch_job(first).get_status() == JobStatus.FINISHED
    assert len(core.pending_catalog_requests(path)) == 1
    worker.register_birth()
    worker.set_state("idle")
    tasks.reconcile_query_catalogs(queue=queue)
    second = queue.get_job_ids()[0]
    assert second != first
    drain(queue, worker)
    assert core.pending_catalog_requests(path) == []
    assert "later.csv" in {e["path"] for e in json.loads((path / "_query_engine/catalog.json").read_text())["files"]}


def test_failed_attempt_retains_request_and_backoff(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    path = project(root)
    (path / "broken.parquet").write_bytes(b"not parquet")
    core.record_catalog_refresh(path, "broken.parquet")
    first = tasks.enqueue_catalog_refresh(path, queue=queue)["job_id"]
    drain(queue, worker)
    assert queue.fetch_job(first).get_status() == JobStatus.FAILED
    assert core.pending_catalog_requests(path)
    worker.register_birth()
    worker.set_state("idle")
    assert tasks.enqueue_catalog_refresh(path, queue=queue)["error_code"] == "query_catalog_retry_pending"
    assert queue.count == 0


def test_no_repeat_request_after_clean_tick(catalog_queue):
    root, queue, worker = catalog_queue
    path = project(root)
    discover(queue, worker)
    tasks.reconcile_query_catalogs(queue=queue)
    drain(queue, worker)
    worker.register_birth()
    worker.set_state("idle")
    assert core.pending_catalog_requests(path) == []
    outcome = tasks.reconcile_query_catalogs(queue=queue)
    assert outcome["admitted"] == 0
    assert core.pending_catalog_requests(path) == []


@pytest.mark.parametrize("nested", ["rhessys/scenarios/scenario", "runs/child", "_base/runs/child"])
def test_receipt_free_nested_source_inventory(catalog_queue, nested):
    root, queue, worker = catalog_queue
    parent = project(root)
    location = parent / nested
    location.parent.mkdir(parents=True, exist_ok=True)
    child = project(location.parent, location.name)
    discover(queue, worker)
    tasks.reconcile_query_catalogs(queue=queue)
    assert queue.count == 2
    drain(queue, worker)
    assert (child / "_query_engine/catalog.json").is_file()
    assert core.pending_catalog_requests(child) == []


def test_disabled_consumer_configuration_blocks_admission(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    monkeypatch.setenv("QUERY_CATALOG_REFRESH_ENABLED", "false")
    worker.connection.hset(worker.key, tasks.WORKER_FIELD, json.dumps(tasks.catalog_worker_configuration()))
    monkeypatch.setenv("QUERY_CATALOG_REFRESH_ENABLED", "true")
    assert tasks.enqueue_catalog_refresh(path, queue=queue)["error_code"] == "query_catalog_workers_unavailable"
    assert queue.count == 0


def test_cycle_completion_waits_for_acknowledgment(catalog_queue):
    root, queue, worker = catalog_queue
    project(root)
    discover(queue, worker)
    first = tasks.reconcile_query_catalogs(queue=queue)
    assert first["completed_at"] is None
    assert first["state"] == "pending"
    drain(queue, worker)
    second = tasks.reconcile_query_catalogs(queue=queue)
    assert second["completed_at"] is not None
    assert second["state"] == "completed"


def test_new_cycle_resets_errors_and_retains_previous_evidence(catalog_queue):
    root, queue, worker = catalog_queue
    key = "query-catalog:inventory:" + tasks._configuration_id()
    errors = [{"root": "0", "relative": ".", "error": "PermissionError"}]
    queue.connection.set(key, json.dumps({
        "initialized": False, "completed_at": 1,
        "discovery_completed_at": 1, "cycle_errors": errors,
    }))
    tasks.reconcile_query_catalogs(queue=queue)
    state = json.loads(queue.connection.get(key))
    assert state["cycle_errors"] == []
    assert state["previous_cycle_errors"] == errors


def test_missing_namespace_degrades_and_retries_on_next_tick(catalog_queue):
    root, queue, worker = catalog_queue
    root.rmdir()
    discover(queue, worker)
    missing = tasks.reconcile_query_catalogs(queue=queue)
    assert missing["state"] == "degraded"
    assert missing["completed_at"] is None
    root.mkdir()
    path = project(root)
    discover(queue, worker)
    recovered = tasks.reconcile_query_catalogs(queue=queue)
    assert recovered["admitted"] == 1
    drain(queue, worker)
    assert (path / "_query_engine/catalog.json").is_file()


def test_missing_redundant_alias_does_not_degrade(catalog_queue, monkeypatch):
    root, queue, worker = catalog_queue
    from dataclasses import replace
    roots = core.configured_roots()
    monkeypatch.setattr(core, "configured_roots", lambda: roots + [replace(roots[0], path=root / "missing-alias")])
    # Worker advertisements must describe the same configured roots.
    for consumer in [worker, *worker._catalog_test_companions]:
        consumer.register_death()
        consumer.register_birth()
        consumer.set_state("idle")
    discover(queue, worker)
    result = tasks.reconcile_query_catalogs(queue=queue)
    assert result["state"] == "completed"


def test_ambiguous_transaction_commit_coalesces_on_retry(catalog_queue, monkeypatch):
    import redis
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    original_pipeline = queue.connection.pipeline
    injected = []

    def pipeline_with_lost_reply(*args, **kwargs):
        pipeline = original_pipeline(*args, **kwargs)
        execute = pipeline.execute

        def commit_then_disconnect(*args, **kwargs):
            result = execute(*args, **kwargs)
            if not injected:
                injected.append(True)
                raise redis.ConnectionError("test lost reply after real Redis commit")
            return result

        pipeline.execute = commit_then_disconnect
        return pipeline

    monkeypatch.setattr(queue.connection, "pipeline", pipeline_with_lost_reply)
    result = tasks.enqueue_catalog_refresh(path, queue=queue)
    assert result["error_code"] == "query_catalog_dispatch_unavailable"
    assert queue.count == 1
    retry = tasks.enqueue_catalog_refresh(path, queue=queue)
    assert retry["job_id"] == queue.get_job_ids()[0]
    assert queue.count == 1
    drain(queue, worker)
    assert core.pending_catalog_requests(path) == []


def test_killed_worker_recovers_after_rq_abandonment(catalog_queue, monkeypatch):
    import multiprocessing
    import time
    from rq.registry import StartedJobRegistry

    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path, "values.csv")
    first = tasks.enqueue_catalog_refresh(path, queue=queue, timeout=10)["job_id"]
    context = multiprocessing.get_context("fork")
    entered = context.Event()
    original = core.refresh_catalog

    def pause_before_scan(*args, **kwargs):
        entered.set()
        time.sleep(60)
        return original(*args, **kwargs)

    monkeypatch.setattr(core, "refresh_catalog", pause_before_scan)
    worker.register_death()
    process = context.Process(target=worker.work, kwargs={"burst": True})
    process.start()
    try:
        assert entered.wait(10), "worker did not enter refresh boundary"
        process.kill()
        process.join(10)
        assert not process.is_alive()
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)
    assert core.pending_catalog_requests(path)
    # Real RQ abandonment cleanup, advancing its cutoff to avoid waiting TTL.
    StartedJobRegistry(queue=queue).cleanup(timestamp=time.time() + 7200)
    assert queue.fetch_job(first).get_status() == JobStatus.FAILED
    monkeypatch.setattr(core, "refresh_catalog", original)
    worker.register_death()
    worker.register_birth()
    worker.set_state("idle")
    tasks.reconcile_query_catalogs(queue=queue)
    successor = queue.get_job_ids()[0]
    assert successor != first
    drain(queue, worker)
    assert core.pending_catalog_requests(path) == []
    assert (path / "_query_engine/catalog.json").is_file()


@pytest.fixture
def enqueue_metadata(monkeypatch):
    from wepppy.rq import auth_actor
    from wepppy.observability.correlation import set_correlation_id, reset_correlation_id

    # Restore any hook installation after this test, while supporting suites
    # that installed the real production hook before reaching this module.
    monkeypatch.setattr(Queue, "enqueue", Queue.enqueue)
    monkeypatch.setattr(Queue, "enqueue_call", Queue.enqueue_call)
    monkeypatch.setattr(Queue, "_auth_actor_wrapped", getattr(Queue, "_auth_actor_wrapped", False), raising=False)
    auth_actor.install_rq_auth_actor_hook()
    actor = {"token_class": "session", "session_id": "catalog-test-session"}
    actor_token = auth_actor.set_auth_actor(actor)
    correlation = "cid-catalog-transaction-test"
    correlation_token = set_correlation_id(correlation)
    try:
        yield actor, correlation
    finally:
        reset_correlation_id(correlation_token)
        auth_actor.reset_auth_actor(actor_token)


def test_real_watch_conflict_keeps_durable_request(catalog_queue, monkeypatch, enqueue_metadata):
    root, queue, worker = catalog_queue
    path = project(root)
    core.record_catalog_refresh(path)
    scope = core.resolve_scope(path)
    key = tasks._admission_key(scope.scope_id, scope.incarnation)
    original_pipeline = queue.connection.pipeline
    conflicted = []

    def pipeline_with_competing_writer(*args, **kwargs):
        pipeline = original_pipeline(*args, **kwargs)
        execute = pipeline.execute

        def competing_commit(*args, **kwargs):
            if not conflicted:
                conflicted.append(True)
                queue.connection.set(key, "test-competing-admission")
            return execute(*args, **kwargs)

        pipeline.execute = competing_commit
        return pipeline

    monkeypatch.setattr(queue.connection, "pipeline", pipeline_with_competing_writer)
    before = set(queue.connection.scan_iter("rq:job:*"))
    assert tasks.enqueue_catalog_refresh(path, queue=queue)["error_code"] == "query_catalog_admission_contended"
    assert queue.count == 0
    assert core.pending_catalog_requests(path)
    assert set(queue.connection.scan_iter("rq:job:*")) == before
    identifier = tasks.enqueue_catalog_refresh(path, queue=queue)["job_id"]
    assert queue.count == 1
    job = queue.fetch_job(identifier)
    actor, correlation = enqueue_metadata
    assert job.meta["auth_actor"] == actor
    assert job.meta["correlation_id"] == correlation
    assert job.meta["query_catalog_maintenance"] is True


def test_enabled_default_host_requires_explicit_roots(monkeypatch):
    monkeypatch.delenv("QUERY_CATALOG_ROOTS_JSON", raising=False)
    monkeypatch.setenv("QUERY_CATALOG_REFRESH_ENABLED", "true")
    with pytest.raises(ValueError, match="QUERY_CATALOG_ROOTS_JSON"):
        tasks.catalog_worker_configuration()
    with pytest.raises(ValueError, match="QUERY_CATALOG_ROOTS_JSON"):
        tasks.reconcile_query_catalogs()
    monkeypatch.setenv("QUERY_CATALOG_REFRESH_ENABLED", "false")
    configuration = tasks.catalog_worker_configuration()
    assert configuration["enabled"] is False
    assert any(root["namespace"] == "legacy:runs" for root in configuration["roots"])


def test_queued_child_fails_after_owner_freeze(catalog_queue):
    root, queue, worker = catalog_queue
    parent = project(root)
    child_root = parent / "_pups/omni/scenarios"
    child_root.mkdir(parents=True)
    child = project(child_root, "child")
    core.record_catalog_refresh(child, "values.csv")
    identifier = tasks.enqueue_catalog_refresh(child, queue=queue)["job_id"]
    (parent / "READONLY").write_text("frozen")
    drain(queue, worker)
    assert queue.fetch_job(identifier).get_status() == JobStatus.FAILED
    assert not (child / "_query_engine/catalog.json").exists()
    assert core.pending_catalog_requests(child)
    worker.register_birth()
    worker.set_state("idle")
    assert tasks.reconcile_query_catalogs(queue=queue)["admitted"] == 0
    assert queue.count == 1
    drain(queue, worker)
    assert tasks.reconcile_query_catalogs(queue=queue)["admitted"] == 0
    assert core.pending_catalog_requests(child)
