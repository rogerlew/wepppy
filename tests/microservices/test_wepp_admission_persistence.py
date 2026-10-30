"""WAM-01: real input persistence and coordination at execution admission."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import threading
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.client import Redis
from rq.job import Job

from tests.rq.test_rq212_lifecycle import lifecycle  # noqa: F401
from wepppy.microservices.rq_engine import bootstrap_routes, wepp_routes
from wepppy.nodb.core import Ron, Soils, Watershed, Wepp
from wepppy.rq import submission_recovery

pytestmark = [pytest.mark.integration, pytest.mark.slow]
ENDPOINTS = ["run-wepp", "run-wepp-watershed", "prep-wepp-watershed",
             "run-wepp-npprep", "run-wepp-watershed-no-prep"]


@pytest.fixture
def admission(tmp_path, monkeypatch, lifecycle, request):
    runid = "wam-" + uuid.uuid4().hex
    wd = tmp_path / runid
    wd.mkdir()
    config = "canada-wbt-mofe.cfg"
    Ron(str(wd), config, initialize_components=False)
    Soils(str(wd), config)
    Watershed(str(wd), config)
    # Fresh fixture needs no climate-dependent output cleanup; parsing/dumps are real.
    monkeypatch.setattr(Wepp, "clean", lambda self: None)
    batch = getattr(request, "param", None) == "batch"
    wepp = Wepp(str(wd), config, run_group="batch" if batch else None,
                group_name="wam-batch" if batch else None)
    with wepp.locked():
        wepp._bootstrap_enabled = True
        wepp._kslast = 0.02
        wepp._multi_ofe = False
    connection = lifecycle.connection
    connection.ping()
    monkeypatch.setattr(submission_recovery, "_LIFECYCLE_LOCK_DIR", str(tmp_path / "leases"))
    jobs = []
    receipts = {}
    timestamps = {"completed": "prior"}
    prep = SimpleNamespace(
        get_rq_job_id=lambda key: receipts.get(key),
        set_rq_job_id=lambda key, value: receipts.__setitem__(key, value),
        remove_timestamp=lambda task: timestamps.pop("completed", None),
    )

    class Queue:
        def __init__(self, **kwargs):
            pass

        def enqueue_call(self, func, args, **kwargs):
            # Save a real discoverable RQ job without publishing to a live worker queue.
            job = Job.create(func, args=args, id=kwargs["job_id"], connection=connection,
                             origin="default", status="queued")
            job.save()
            jobs.append(job)
            return job

    for module in (wepp_routes, bootstrap_routes):
        monkeypatch.setattr(module, "get_wd", lambda *args, **kwargs: str(wd))
        monkeypatch.setattr(module, "require_jwt", lambda *args, **kwargs: {})
        monkeypatch.setattr(module, "authorize_run_access", lambda *args, **kwargs: None)
        monkeypatch.setattr(module.RedisPrep, "getInstance", lambda wd: prep)
        monkeypatch.setattr(module, "redis", SimpleNamespace(
            Redis=lambda **kwargs: Redis(connection_pool=connection.connection_pool), RedisError=__import__('redis').RedisError))
        monkeypatch.setattr(module, "Queue", Queue)
    # The fixture isolates admission from raster prerequisite production.
    monkeypatch.setattr(wepp_routes, "_watershed_abstraction_state_response", lambda *a, **k: None)
    app = FastAPI()
    app.include_router(wepp_routes.router, prefix="/api")
    app.include_router(bootstrap_routes.router, prefix="/api")
    state = SimpleNamespace(wd=wd, runid=runid, connection=connection, jobs=jobs,
                            receipts=receipts, timestamps=timestamps, prep=prep, app=app)
    try:
        yield state
    finally:
        for job in jobs:
            job.delete()
        connection.close()


def _post(state, endpoint, value):
    with TestClient(state.app) as client:
        return client.post(f"/api/runs/{state.runid}/cfg/{endpoint}",
                           json={"kslast": value, "initial_sat": 0.4})


def _snapshot(state):
    return {p.name: p.read_bytes() for p in state.wd.glob("*.nodb")}


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_active_rejection_preserves_real_inputs_and_receipts(admission, endpoint):
    a = admission
    accepted = _post(a, endpoint, 0.03)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["job_id"] == a.jobs[0].id
    assert Wepp.load_detached(str(a.wd)).kslast == 0.03
    assert Soils.load_detached(str(a.wd)).initial_sat == 0.4
    a.timestamps["completed"] = "preserve"
    before = _snapshot(a)
    receipts = dict(a.receipts)
    rejected = _post(a, endpoint, 0.9)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "conflict"
    assert _snapshot(a) == before
    assert a.receipts == receipts
    assert a.timestamps == {"completed": "preserve"}
    assert len(a.jobs) == 1
    assert Wepp.load_detached(str(a.wd)).kslast == 0.03


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_busy_lease_preserves_real_inputs(admission, monkeypatch, endpoint):
    a = admission
    module = bootstrap_routes if endpoint in ENDPOINTS[3:] else wepp_routes
    before = _snapshot(a)
    real_lock = submission_recovery.rq_submission_lock
    monkeypatch.setattr(module, "rq_submission_lock", lambda *args, **kwargs:
                        real_lock(*args, **kwargs, blocking_timeout=0))
    lock = a.connection.lock(f"rq:submission:{a.runid}:wepp", timeout=120)
    assert lock.acquire(blocking=False)
    try:
        response = _post(a, endpoint, 0.9)
        assert response.status_code == 409, response.text
        assert _snapshot(a) == before
        assert not a.jobs and not a.receipts
        assert a.timestamps == {"completed": "prior"}
    finally:
        lock.release()


def test_competing_requests_and_active_child_preserve_prepared_input(admission, monkeypatch):
    from wepppy.nodb.core.wepp import prep_soil
    from wepppy.wepp.soils.utils import WeppSoilUtil
    a = admission
    applying, resume = threading.Event(), threading.Event()
    original_apply = wepp_routes.apply_wepp_run_payload
    real_lock = submission_recovery.rq_submission_lock
    monkeypatch.setattr(wepp_routes, "rq_submission_lock", lambda *args, **kwargs:
                        real_lock(*args, **kwargs, blocking_timeout=0))

    def controlled_apply(*args, **kwargs):
        applying.set()
        assert resume.wait(10)
        return original_apply(*args, **kwargs)

    monkeypatch.setattr(wepp_routes, "apply_wepp_run_payload", controlled_apply)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(_post, a, "prep-wepp-watershed", 0.03)
        try:
            assert applying.wait(10)
            before = _snapshot(a)
            assert _post(a, "prep-wepp-watershed", 0.9).status_code == 409
            assert _snapshot(a) == before
        finally:
            resume.set()
        assert first.result(timeout=10).status_code == 200
    root = a.jobs[0]
    child = Job.create(wepp_routes.run_wepp_rq, args=(a.runid,), connection=a.connection,
                       origin="default", status="started")
    child.save()
    a.jobs.append(child)
    root.meta["jobs:1,func:run"] = child.id
    root.set_status("finished")
    root.save()
    before = _snapshot(a)
    assert _post(a, "prep-wepp-watershed", 0.9).status_code == 409
    assert _snapshot(a) == before
    saved = Wepp.load_detached(str(a.wd))
    soils = Soils.load_detached(str(a.wd))
    source = Path(__file__).resolve().parents[1] / "omni/fixtures/honeyed_marathoner_sediment_inversion/run_root/wepp/runs/p118.sol"
    destination = a.wd / "wepp/runs/p1.sol"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exercise the actual worker's soil writer with reloaded accepted fields.
    prep_soil(("101", str(source), str(destination), saved.kslast, None,
               soils.initial_sat, soils.clip_soils, soils.clip_soils_depth,
               soils.clip_soils_minimum, soils.clip_soils_minimum_depth, False))
    prepared = WeppSoilUtil(str(destination), preserve_input_format=True)
    assert prepared.obj["res_lyr"]["kslast"] == pytest.approx(0.03)
    assert prepared.obj["ofes"][0]["res_lyr"]["kslast"] == pytest.approx(0.03)


@pytest.mark.parametrize("endpoint", ENDPOINTS[3:])
def test_no_prep_keeps_checked_out_files(admission, endpoint):
    a = admission
    prepared = a.wd / "wepp/runs/p1.sol"
    prepared.parent.mkdir(parents=True, exist_ok=True)
    prepared.write_bytes(b"checked-out scientific input\n")
    assert _post(a, endpoint, 0.03).status_code == 200
    assert _post(a, endpoint, 0.9).status_code == 409
    assert prepared.read_bytes() == b"checked-out scientific input\n"


@pytest.mark.parametrize("failure,status", [(ValueError("invalid"), 400),
    (RuntimeError("persistence failed"), 500)])
@pytest.mark.parametrize("endpoint", ["prep-wepp-watershed", "run-wepp-npprep"])
def test_admitted_payload_failure_releases_owned_lease(admission, monkeypatch, endpoint, failure, status):
    a = admission
    module = bootstrap_routes if endpoint in ENDPOINTS[3:] else wepp_routes
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(module, "apply_wepp_run_payload", fail)
    response = _post(a, endpoint, 0.9)
    assert response.status_code == status
    assert not a.jobs and not a.receipts
    assert a.timestamps == {"completed": "prior"}
    with submission_recovery.rq_submission_lock(a.connection, f"{a.runid}:wepp",
                                               lifecycle_key=a.runid, blocking_timeout=0):
        pass


@pytest.mark.parametrize("endpoint", ["prep-wepp-watershed", "run-wepp-npprep"])
def test_enqueue_failure_releases_lease_without_rollback_promise(admission, monkeypatch, endpoint):
    a = admission
    module = bootstrap_routes if endpoint in ENDPOINTS[3:] else wepp_routes
    def fail(*args, **kwargs):
        raise RuntimeError("enqueue failed")
    monkeypatch.setattr(module.Queue, "enqueue_call", fail)
    response = _post(a, endpoint, 0.9)
    assert response.status_code == 500
    assert Wepp.load_detached(str(a.wd)).kslast == 0.9
    with submission_recovery.rq_submission_lock(a.connection, f"{a.runid}:wepp",
                                               lifecycle_key=a.runid, blocking_timeout=0):
        pass


@pytest.mark.parametrize("endpoint", ENDPOINTS[:3])
def test_webhook_accept_replay_and_conflict_preserve_inputs(admission, monkeypatch, endpoint):
    from rq import Queue
    from wepppy.microservices.rq_engine import webhooks
    a = admission
    monkeypatch.setenv("RQ_WEBHOOK_ENVIRONMENT", a.runid)
    monkeypatch.setenv("RQ_WEBHOOK_ADMISSION", "enabled")
    monkeypatch.setenv("RQ_WEBHOOK_INSTRUMENTATION", "rq-wh-01")
    monkeypatch.setenv("RQ_WEBHOOK_REDIS_RUN_ID", a.connection.info("server")["run_id"])
    # Worker registration/auth policy is covered separately; store/publication are real.
    monkeypatch.setattr(webhooks, "verify_workers", lambda *args: None)
    monkeypatch.setattr(webhooks, "principal_key", lambda *args: "wam-test-principal")
    monkeypatch.setattr(wepp_routes, "Queue", Queue)
    queue = Queue(connection=a.connection)
    prior_queue_ids = queue.job_ids
    payload = {"kslast": 0.03, "webhook_url": "https://example.com/callback"}
    with TestClient(a.app) as client:
        url = f"/api/runs/{a.runid}/cfg/{endpoint}"
        first = client.post(url, json=payload, headers={"Idempotency-Key": "wam-request-key-0001"})
        assert first.status_code == 200, first.text
        assert first.json()["webhook"] == {"status": "accepted"}
        a.jobs.append(Job.fetch(first.json()["job_id"], connection=a.connection))
        before = _snapshot(a)
        receipts = dict(a.receipts)
        a.timestamps["completed"] = "preserve"
        replay = client.post(url, json=payload, headers={"Idempotency-Key": "wam-request-key-0001"})
        assert replay.json() == first.json()
        assert _snapshot(a) == before
        rejected = client.post(url, json={**payload, "kslast": 0.9},
                               headers={"Idempotency-Key": "wam-request-key-0002"})
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error"]["code"] == "conflict"
        assert _snapshot(a) == before
        assert a.receipts == receipts
        assert a.timestamps == {"completed": "preserve"}
        assert queue.job_ids == prior_queue_ids + [first.json()["job_id"]]


@pytest.mark.parametrize("endpoint", ENDPOINTS[:3])
@pytest.mark.parametrize("admission,context", [("batch", "batch"), (None, "base-run"),
                                                (None, "base-config")], indirect=["admission"])
def test_configuration_only_saves_do_not_enter_execution_gate(admission, monkeypatch, endpoint, context):
    a = admission
    runid = "batch;;name;; _BASE " if context == "base-run" else a.runid
    config = " _BASE " if context == "base-config" else "cfg"
    def forbidden(*args, **kwargs):
        pytest.fail("configuration-only save entered execution admission")
    monkeypatch.setattr(wepp_routes, "rq_submission_lock", forbidden)
    with TestClient(a.app) as client:
        response = client.post(f"/api/runs/{runid}/{config}/{endpoint}", json={"kslast": 0})
    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Set wepp inputs for batch processing"}
    assert Wepp.load_detached(str(a.wd)).kslast == 0
    assert not a.jobs and not a.receipts


@pytest.mark.parametrize("state", ["deferred", "mismatch", "terminal", "missing"])
def test_prior_work_reconciliation_before_proposed_inputs(admission, state):
    a = admission
    prior = Job.create(wepp_routes.run_wepp_rq,
                       args=("foreign-run" if state == "mismatch" else a.runid,),
                       connection=a.connection, origin="default", status="deferred" if state in {"deferred", "mismatch"} else "finished")
    prior.save()
    a.jobs.append(prior)
    a.receipts["run_wepp_rq"] = prior.id
    if state == "missing":
        prior.delete(remove_from_queue=False)
        a.jobs.remove(prior)
    before = _snapshot(a)
    response = _post(a, "prep-wepp-watershed", 0.03)
    if state == "mismatch":
        assert response.status_code == 409
        assert _snapshot(a) == before
        assert a.receipts == {"run_wepp_rq": prior.id}
        assert a.timestamps == {"completed": "prior"}
    else:
        assert response.status_code == 200, response.text
        assert Wepp.load_detached(str(a.wd)).kslast == 0.03
        if state == "deferred":
            assert prior.get_status(refresh=True) == "canceled"


def test_file_lifecycle_exclusion_before_payload(admission, monkeypatch):
    import fcntl
    import hashlib
    a = admission
    fence_dir = Path(submission_recovery._LIFECYCLE_LOCK_DIR)
    fence_dir.mkdir(exist_ok=True)
    digest = hashlib.sha256(f"run\0{a.runid}".encode()).hexdigest()
    before = _snapshot(a)
    real_lock = submission_recovery.rq_submission_lock
    monkeypatch.setattr(wepp_routes, "rq_submission_lock", lambda *args, **kwargs:
                        real_lock(*args, **kwargs, blocking_timeout=0))
    with (fence_dir / digest).open("w") as fence:
        fcntl.flock(fence, fcntl.LOCK_EX | fcntl.LOCK_NB)
        response = _post(a, "prep-wepp-watershed", 0.9)
        assert response.status_code == 409
        assert _snapshot(a) == before
        assert not a.receipts and not a.jobs
    with real_lock(a.connection, f"{a.runid}:wepp", lifecycle_key=a.runid, blocking_timeout=0):
        pass


@pytest.mark.parametrize("endpoint", ["prep-wepp-watershed", "run-wepp-npprep"])
def test_lost_lease_never_releases_successor_or_publishes_receipt(admission, monkeypatch, endpoint):
    a = admission
    module = bootstrap_routes if endpoint in ENDPOINTS[3:] else wepp_routes
    original = module.apply_wepp_run_payload
    key = f"rq:submission:{a.runid}:wepp"
    def replace_owner(*args, **kwargs):
        result = original(*args, **kwargs)
        # Model expiry and successor acquisition after application began.
        a.connection.set(key, b"successor-token", px=120000)
        return result
    monkeypatch.setattr(module, "apply_wepp_run_payload", replace_owner)
    try:
        response = _post(a, endpoint, 0.9)
        assert response.status_code == 500  # Existing post-acquisition loss contract.
        assert a.connection.get(key) == b"successor-token"
        assert not a.jobs and not a.receipts
        assert a.timestamps == {"completed": "prior"}
        assert Wepp.load_detached(str(a.wd)).kslast == 0.9  # No late rollback promise.
    finally:
        a.connection.delete(key)  # Test-created successor, not another process's lease.
