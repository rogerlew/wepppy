"""Run only after the coordinator confirms the local forest RQ 2.12 cutover.

Creates receipt-owned disposable projects; never resets Redis or other runs.
Tokens exist only in process memory. Run inside weppcloud using wctl and stdin.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import uuid

import redis
import requests
import rq
from rq import Queue, Worker
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.job_id import new_rq_job_id
from wepppy.weppcloud.app import app, user_datastore
from wepppy.weppcloud.utils import auth_tokens

BASE = "https://wc.bearhive.duckdns.org"
SOURCE = "rlew-international-refuge"
TARGET = "rq212-20261027-upgraded"
CANCEL_TARGET = "rq212-20261027-cancel"
CONFIG = "disturbed-wbt-profile"
OUT = Path("/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts")
assert rq.__version__ == "2.12.0", "Do not submit before runtime cutover"
assert not Path("/wc1/runs/rq", TARGET).exists(), "Receipt target already exists"
record = {
    "started": datetime.now(timezone.utc).isoformat(),
    "rq": rq.__version__, "source": SOURCE, "target": TARGET,
    "config": CONFIG, "requests": [],
    "auth": "Existing dev-agent session; actual HTTP profile CSRF mint and bearer API",
}
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))


def save():
    (OUT / "acceptance_upgraded.json").write_text(json.dumps(record, indent=2, default=str))


def nodes(value):
    if isinstance(value, dict):
        if "job_id" in value and "status" in value:
            yield value
        for item in value.values():
            yield from nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def post(path, payload, *, bearer=None, expected=200):
    headers = {"Authorization": "Bearer " + (token if bearer is None else bearer)}
    if bearer == "":
        headers = {}
    response = session.post(BASE + path, json=payload, headers=headers, timeout=90)
    data = response.json()
    record["requests"].append({"path": path, "payload": payload,
                               "status": response.status_code, "response": data})
    save()
    assert response.status_code == expected, (response.status_code, data)
    return data


def fetch_tree(job_id):
    response = session.get(BASE + "/rq-engine/api/jobinfo/" + job_id,
                           headers={"Authorization": "Bearer " + token}, timeout=45)
    response.raise_for_status()
    return response.json()


def wait(job_id, label, *, expected_failure=False):
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        data = fetch_tree(job_id)
        states = [(node["job_id"], node["status"]) for node in nodes(data)]
        record[label] = {"job_id": job_id, "tree": data,
                         "polled": datetime.now(timezone.utc).isoformat()}
        save()
        active = any(state in ("queued", "started", "scheduled") for _, state in states)
        failed = any(state in ("failed", "stopped", "canceled") for _, state in states)
        finished = bool(states) and all(state == "finished" for _, state in states)
        print(label, states, flush=True)
        if finished or (failed and not active):
            assert failed if expected_failure else finished, states
            return data
        time.sleep(3)
    raise TimeoutError(label)


record["workers_before"] = [
    {"name": worker.name, "queues": worker.queue_names(),
     "job": worker.get_current_job_id(), "state": worker.get_state()}
    for worker in Worker.all(connection=connection)
]
save()
with app.app_context():
    user = user_datastore.find_user(email="dev-agent@example.com")
    assert user and user.active
    client = app.test_client()
    with client.session_transaction() as flask_session:
        flask_session["_user_id"] = user.fs_uniquifier
        flask_session["_fresh"] = True
    assert client.get("/profile").status_code == 200
    cookie = client.get_cookie(app.config.get("SESSION_COOKIE_NAME", "session"))
    assert cookie
    session = requests.Session()
    session.cookies.set(cookie.key, cookie.value)
    response = session.get(BASE + "/weppcloud/profile", timeout=30)
    response.raise_for_status()
    assert user.email in response.text
    csrf = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', response.text)
    assert csrf
    response = session.post(BASE + "/weppcloud/profile/mint-token",
                            headers={"X-CSRFToken": csrf.group(1)}, timeout=30)
    response.raise_for_status()
    token = response.json()["Content"]["token"]

    fork = post(f"/rq-engine/api/runs/{SOURCE}/{CONFIG}/fork",
                {"target_runid": TARGET, "skip_wepp_runs_output": True})
    wait(fork["job_id"], "fork")
    initial = post(f"/rq-engine/api/runs/{TARGET}/{CONFIG}/run-wepp", {})
    failure = wait(initial["job_id"], "initial_failure", expected_failure=True)
    failures = [node for node in nodes(failure) if node.get("exc_info")]
    assert any("ldd did not resolve libgfortran" in node["exc_info"] for node in failures)
    assert any(node["status"] == "deferred" for node in nodes(failure))
    recovered = post(f"/rq-engine/api/runs/{TARGET}/{CONFIG}/run-wepp",
                     {"wepp_bin": "wepp_261026"})
    wait(recovered["job_id"], "model")
    old_jobs = []
    for node in nodes(failure):
        job = Job.fetch(node["job_id"], connection=connection)
        old_jobs.append({"job_id": job.id, "status": job.get_status().value,
                         "function": job.func_name, "started_at": job.started_at})
    assert all(job["status"] != "deferred" for job in old_jobs)
    record["obsolete_graph"] = old_jobs
    save()

    # Occupy only the existing serial pool with a bounded package-owned job.
    # This makes the API-created fork deterministically queued, without global pause.
    blocker = Queue("fork-archive", connection=connection).enqueue_call(
        "time.sleep", args=(90,), job_id=new_rq_job_id(), timeout=120,
        description="RQ212 disposable queued-cancellation blocker", result_ttl=3600,
        meta={"rq212_acceptance": True},
    )
    record["blocker_job_id"] = blocker.id
    save()
    deadline = time.monotonic() + 45
    while blocker.get_status(refresh=True).value != "started":
        assert time.monotonic() < deadline, "Serial blocker did not start"
        time.sleep(0.2)
    queued = post(f"/rq-engine/api/runs/{SOURCE}/{CONFIG}/fork",
                  {"target_runid": CANCEL_TARGET, "skip_wepp_runs_output": True})
    job = Job.fetch(queued["job_id"], connection=connection)
    assert job.get_status().value == "queued"
    cancel_path = "/rq-engine/api/canceljob/" + job.id
    post(cancel_path, {}, bearer="", expected=401)
    wrong_scope = auth_tokens.issue_token(
        "rq212-unrelated-scope", scopes=["rq:status"], audience="rq-engine",
        extra_claims={"token_class": "service", "runs": ["rq212-20261027-unowned"],
                      "jti": uuid.uuid4().hex},
    )["token"]
    post(cancel_path, {}, bearer=wrong_scope, expected=403)
    assert job.get_status(refresh=True).value == "queued", "Rejected cancel mutated job"
    post(cancel_path, {})
    assert job.get_status(refresh=True).value == "canceled"
    assert job.started_at is None, "Queued cancellation raced dispatch"
    record["queued_cancellation"] = {"job_id": job.id, "status": "canceled",
                                      "started_at": job.started_at}
    save()
    deadline = time.monotonic() + 150
    while blocker.get_status(refresh=True).value != "finished":
        assert time.monotonic() < deadline, "Owned blocker failed to finish"
        time.sleep(1)
    retry = post(f"/rq-engine/api/runs/{SOURCE}/{CONFIG}/fork",
                 {"target_runid": CANCEL_TARGET, "skip_wepp_runs_output": True})
    wait(retry["job_id"], "cancel_resubmission")
record["finished"] = datetime.now(timezone.utc).isoformat()
save()
