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
    (OUT / "acceptance_archive_restore.json").write_text(json.dumps(record, indent=2, default=str))


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
    before = {}
    for folder in ("wepp/runs", "wepp/output"):
        for path in sorted((wd / folder).rglob("*")):
            if path.is_file():
                before[str(path.relative_to(wd))] = hashlib.sha256(path.read_bytes()).hexdigest()
    old_archives = set((wd / "archives").glob("*.zip"))
    submitted = post(f"/rq-engine/api/runs/{TARGET}/{CONFIG}/archive", {"comment": "RQ212 paired artifact validation"})
    wait(submitted["job_id"], "archive")
    new_archives = set((wd / "archives").glob("*.zip")) - old_archives
    assert len(new_archives) == 1
    archive = new_archives.pop()
    with zipfile.ZipFile(archive) as bundle:
        for name, digest in before.items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == digest, name
        record["archive_manifest"] = {"name": archive.name, "members": len(bundle.infolist()), "validated_generated_files": len(before)}
    download_path = f"/weppcloud/runs/{TARGET}/{CONFIG}/download/archives/{archive.name}"
    response = session.get(BASE + download_path, headers={"Authorization": "Bearer " + token}, timeout=120)
    response.raise_for_status()
    assert hashlib.sha256(response.content).hexdigest() == hashlib.sha256(archive.read_bytes()).hexdigest()
    record["download"] = {"path": download_path, "status": response.status_code,
                          "bytes": len(response.content), "sha256": hashlib.sha256(response.content).hexdigest()}
    submitted = post(f"/rq-engine/api/runs/{TARGET}/{CONFIG}/restore-archive", {"archive_name": archive.name})
    wait(submitted["job_id"], "restore")
    for name, digest in before.items():
        assert hashlib.sha256((wd / name).read_bytes()).hexdigest() == digest, name
    record["restored_generated_files"] = len(before)
record["finished"] = datetime.now(timezone.utc).isoformat()
save()
