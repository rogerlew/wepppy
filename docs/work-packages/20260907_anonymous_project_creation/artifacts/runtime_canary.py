"""Disposable creation checks against the configured development HTTP stack.

Run inside the existing weppcloud container using wctl exec. Reads the existing
agent credential file without printing credentials, cookies, or CAPTCHA tokens.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import uuid

import requests

from wepppy.config.creation_policy import allow_anonymous_project_creation
from wepppy.config.secrets import require_secret
from wepppy.microservices.rq_engine.creation_idempotency import _redis_key
from wepppy.microservices.rq_engine.project_routes import _creation_idempotency_client
from wepppy.weppcloud.app import app, db, Run, User, user_datastore
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.utils.helpers import get_wd

MODE = sys.argv[1]
assert MODE in {"true", "false"}
assert allow_anonymous_project_creation() == (MODE == "true")
BASE = "https://" + os.environ["EXTERNAL_HOST"]
SITE_KEY = os.environ["CAP_SITE_KEY"]
report = {"mode": MODE, "uid": os.getuid(), "gid": os.getgid(), "checks": [], "runs": []}


def prng(seed, length):
    value = 2166136261
    for ch in seed:
        value ^= ord(ch)
        value = (value + (value << 1) + (value << 4) + (value << 7) + (value << 8) + (value << 24)) & 0xffffffff
    state = value
    result = ""
    while len(result) < length:
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        state &= 0xffffffff
        result += f"{state:08x}"
    return result[:length]


def mint_cap():
    endpoint = f"{BASE}/cap/{SITE_KEY}"
    response = requests.post(endpoint + "/challenge", json={}, timeout=20)
    response.raise_for_status()
    challenge = response.json()
    spec = challenge["challenge"]
    assert 1 <= spec["c"] <= 8 and 1 <= spec["d"] <= 6
    solutions = []
    for i in range(1, spec["c"] + 1):
        salt = prng(challenge["token"] + str(i), spec["s"])
        target = prng(challenge["token"] + str(i) + "d", spec["d"])
        for candidate in range(2000001):
            if hashlib.sha256((salt + str(candidate)).encode()).hexdigest().startswith(target):
                solutions.append(candidate)
                break
        else:
            raise AssertionError("CAP work bound exceeded")
    response = requests.post(endpoint + "/redeem", json={"token": challenge["token"], "solutions": solutions}, timeout=20)
    response.raise_for_status()
    result = response.json()
    assert result["success"]
    return result["token"]


def login():
    values = {}
    for line in Path("/workdir/wepppy/docker/secrets/dev-agent.env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"').strip("'")
    session = requests.Session()
    response = session.get(BASE + "/weppcloud/login", timeout=30)
    response.raise_for_status()
    csrf = html.unescape(re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)[1])
    response = session.post(BASE + "/weppcloud/login", data={
        "email": values["DEV_AGENT_EMAIL"], "password": values["DEV_AGENT_PASSWORD"],
        "csrf_token": csrf, "cap_token": mint_cap(),
    }, timeout=30, allow_redirects=False)
    assert response.status_code in {302, 303}, f"login status {response.status_code}"
    report["checks"].append("real password/CAPTCHA login")
    return session, values["DEV_AGENT_EMAIL"]


def observe_run(response, email, key):
    assert response.status_code == 303, f"create status {response.status_code}: {response.text[:300]}"
    runid = response.headers["Location"].split("/runs/", 1)[1].split("/", 1)[0]
    wd = get_wd(runid)
    files = sorted(p.name for p in Path(wd).iterdir())
    assert "ron.nodb" in files
    with app.app_context():
        record = Run.query.filter_by(runid=runid).first()
        user = User.query.filter_by(email=email).first() if email else None
        if user:
            assert record is not None and str(record.owner_id) == str(user.id)
        else:
            assert record is None or not record.owner_id
        actor_scope = f"user:{user.id}" if user else None
    entry = {"runid": runid, "path": wd, "owned": bool(email), "artifacts": files, "cleanup": "pending"}
    report["runs"].append(entry)
    # The serving process can retain NoDb log handles on NFS. Defer directory
    # removal until that process is recreated, rather than racing open files.
    _creation_idempotency_client().delete(_redis_key(key, actor_scope))
    entry["cleanup"] = "retained for cleanup after service recreation; idempotency key removed"
    report["checks"].append("real creation artifacts and expected ownership")


def allocation_snapshot():
    roots, runs = set(), set()
    # DirEntry reuses directory-entry types instead of statting every NAS run.
    with os.scandir("/wc1/runs") as entries:
        for shard in entries:
            if not shard.is_dir(follow_symlinks=False):
                continue
            roots.add(shard.path)
            if len(shard.name) == 2:
                with os.scandir(shard.path) as children:
                    runs.update(run.path for run in children if run.is_dir(follow_symlinks=False))
    with app.app_context():
        rows = set(db.session.scalars(db.select(Run.id)).all())
    return roots, runs, rows


def assert_no_allocation(before):
    after = allocation_snapshot()
    assert before == after, "Denied request changed run directories or ownership records"
    report.setdefault("denial_snapshots", []).append({"root_directories": len(after[0]), "sharded_run_directories": len(after[1]), "database_rows": len(after[2]), "unchanged": True})


def main():
    anonymous = requests.Session()
    response = anonymous.get(BASE + "/weppcloud/interfaces/", timeout=30)
    assert response.status_code == 200
    visible = MODE == "true"
    assert ('class="wc-run-form"' in response.text) == visible
    assert ('/cap/assets/widget.js' in response.text) == visible
    if not visible:
        assert '>Sign in</a> to create a project.' in response.text
    report["checks"].append("anonymous real HTTP interfaces rendering")
    token = mint_cap()
    key = uuid.uuid4().hex
    for path in (["/rq-engine/create/", "/rq-engine/api/create/"] if not visible else ["/rq-engine/create/"]):
        before = allocation_snapshot() if not visible else None
        response = anonymous.post(BASE + path, data={"config": "disturbed9002", "cap_token": token, "creation_idempotency_key": key}, timeout=90, allow_redirects=False)
        if visible:
            observe_run(response, None, key)
        else:
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "anonymous_creation_disabled"
            assert _creation_idempotency_client().get(_redis_key(key, None)) is None
            assert_no_allocation(before)
    if not visible:
        verified = requests.post(f"{BASE}/cap/{SITE_KEY}/siteverify", json={"secret": require_secret("CAP_SECRET"), "response": token}, timeout=20).json()
        assert verified["success"], "Restricted request consumed CAPTCHA"
        report["checks"].append("both aliases deny solved CAPTCHA without consuming token or reserving idempotency")
    authenticated, email = login()
    response = authenticated.get(BASE + "/weppcloud/interfaces/", timeout=30)
    assert response.status_code == 200 and 'class="wc-run-form"' in response.text
    assert '/cap/assets/widget.js' not in response.text
    report["checks"].append("authenticated real HTTP interfaces rendering")
    if not visible:
        # Real same-origin cookie guard must reject a hostile Origin even with valid login.
        before = allocation_snapshot()
        denied = authenticated.post(BASE + "/rq-engine/create/", headers={"Origin": "https://hostile.invalid", "Sec-Fetch-Site": "cross-site"}, json={"config": "disturbed9002", "creation_idempotency_key": uuid.uuid4().hex}, timeout=30)
        assert denied.status_code == 403
        assert_no_allocation(before)
        before = allocation_snapshot()
        denied = authenticated.post(BASE + "/rq-engine/create/", json={"config": "disturbed9002", "creation_idempotency_key": uuid.uuid4().hex}, timeout=30)
        assert denied.status_code == 403
        assert_no_allocation(before)
        report["checks"].append("real cross-origin and missing-origin cookie rejection without allocation")
    if not visible:
        # Signed tokens use the real decoder, Redis revocation checks, and DB actor lookup.
        with app.app_context():
            active_id = User.query.filter_by(email=email).one().id
            inactive = user_datastore.create_user(email=f"creation-canary-{uuid.uuid4().hex}@example.invalid", active=False)
            db.session.commit()
            inactive_id = inactive.id
        try:
            cases = [
                ("session", str(active_id), {"user_id": active_id, "session_id": "creation-canary-" + uuid.uuid4().hex}, 403, "anonymous_creation_disabled"),
                ("session", str(active_id), {"session_id": "creation-canary-" + uuid.uuid4().hex}, 403, "anonymous_creation_disabled"),
                ("USER", str(active_id), {}, 403, "anonymous_creation_disabled"),
                ("user", "2147483647", {}, 500, "run_ownership_failed"),
                ("user", str(inactive_id), {}, 500, "run_ownership_failed"),
                ("user", str(active_id), {"email": "conflicting@example.invalid"}, 500, "run_ownership_failed"),
            ]
            for token_class, subject, extra, status, code in cases:
                token = auth_tokens.issue_token(subject, scopes=["rq:enqueue"], audience="rq-engine", extra_claims={"token_class": token_class, **extra})["token"]
                for transport in ("rq_token", "bearer"):
                    key = uuid.uuid4().hex
                    body = {"config": "disturbed9002", "creation_idempotency_key": key}
                    headers = {}
                    if transport == "rq_token":
                        body[transport] = token
                    else:
                        headers["Authorization"] = "Bearer " + token
                    before = allocation_snapshot()
                    result = anonymous.post(BASE + "/rq-engine/create/", json=body, headers=headers, timeout=30, allow_redirects=False)
                    assert result.status_code == status and result.json()["error"]["code"] == code
                    assert_no_allocation(before)
            report["checks"].append("real JWT/Redis/DB rejection of run-scoped and uppercase tokens, deleted/inactive/conflicting users in both transports")
        finally:
            with app.app_context():
                row = db.session.get(User, inactive_id)
                db.session.delete(row)
                db.session.commit()
    if not visible:
        for token_class in ("service", "mcp"):
            token = auth_tokens.issue_token("creation-policy-canary", scopes=["rq:enqueue"], audience="rq-engine", extra_claims={"token_class": token_class})["token"]
            key = uuid.uuid4().hex
            response = anonymous.post(BASE + "/rq-engine/create/", headers={"Authorization": "Bearer " + token}, json={"config": "disturbed9002", "creation_idempotency_key": key}, timeout=90, allow_redirects=False)
            observe_run(response, None, key)
        report["checks"].append("real signed service and MCP creation preserves existing access")
    key = uuid.uuid4().hex
    response = authenticated.post(BASE + "/rq-engine/create/", headers={"Origin": BASE, "Sec-Fetch-Site": "same-origin"}, data={"config": "disturbed9002", "creation_idempotency_key": key, "cap_token": "stale-field"} if not visible else {"config": "disturbed9002", "creation_idempotency_key": key}, timeout=90, allow_redirects=False)
    observe_run(response, email, key)
    report["checks"].append("real authenticated cookie creation" + (" with stale CAPTCHA field" if not visible else ""))


try:
    main()
finally:
    print(json.dumps(report, indent=2))
