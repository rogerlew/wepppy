"""Run only after the coordinator confirms the local forest RQ 2.12 cutover.

Creates receipt-owned disposable projects; never resets Redis or other runs.
Tokens exist only in process memory. Run inside weppcloud using wctl and stdin.
"""
from datetime import datetime, timezone
import hashlib
import zipfile
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
assert Path("/wc1/runs/rq", TARGET).exists(), "Completed disposable target required"
record = {
    "started": datetime.now(timezone.utc).isoformat(),
    "rq": rq.__version__, "source": SOURCE, "target": TARGET,
    "config": CONFIG, "requests": [],
    "auth": "Existing dev-agent session; actual HTTP profile CSRF mint and bearer API",
}
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))


def save():
    (OUT / "acceptance_restore_repair.json").write_text(json.dumps(record, indent=2, default=str))


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

    wd = Path("/wc1/runs/rq", TARGET)
    previous = json.loads((OUT / "acceptance_archive_restore.json").read_text())
    archive = wd / "archives" / previous["archive_manifest"]["name"]
    relative = "wepp/output/interchange/loss_pw0.out.parquet"
    target = wd / relative
    assert target.is_file() and target.parent == wd / "wepp/output/interchange"
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as bundle:
        archived = hashlib.sha256(bundle.read(relative)).hexdigest()
    assert before == archived
    record["repair"] = {"relative_path": relative, "archive": archive.name,
                        "before_sha256": before, "archive_sha256": archived}
    save()
    # Deliberately remove only this package-owned output to prove restore writes bytes.
    target.unlink()
    assert not target.exists()
    record["repair"]["absent_after_injection"] = True
    save()
    submitted = post(f"/rq-engine/api/runs/{TARGET}/{CONFIG}/restore-archive", {"archive_name": archive.name})
    wait(submitted["job_id"], "restore")
    after = hashlib.sha256(target.read_bytes()).hexdigest()
    assert after == before == archived
    record["repair"]["after_sha256"] = after
    report_path = f"/weppcloud/runs/{TARGET}/{CONFIG}/report/wepp/summary/?format=csv&table=outlet"
    response = session.get(BASE + report_path, timeout=90)
    response.raise_for_status()
    expected = (OUT / "acceptance_upgraded_outlet.csv").read_bytes()
    assert response.content == expected
    record["report"] = {"path": report_path, "status": response.status_code,
                        "sha256": hashlib.sha256(response.content).hexdigest(),
                        "equals_pre_injection": True}
record["finished"] = datetime.now(timezone.utc).isoformat()
save()
