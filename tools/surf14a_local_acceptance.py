"""Receipt-bound local acceptance for SURF-14A.

Run only against the local development stack with both RQ workers stopped.
The script creates two exact disposable users and one run, exercises real HTTP
session and RQ-engine boundaries, then removes every receipt-bound row, Redis
job, session, and run directory in a ``finally`` block.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

import redis
import requests
from rq.job import Job
from rq.exceptions import NoSuchJobError

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Watershed
from wepppy.nodb.unitizer import Unitizer
from wepppy.rq.job_info import get_wepppy_rq_job_info
from wepppy.weppcloud.utils import auth_tokens
from wepppy.weppcloud.app import (
    Role,
    Run,
    User,
    UserPreferences,
    app,
    db,
    roles_users,
    runs_users,
    user_datastore,
)
from wepppy.weppcloud.user_preferences import (
    WBT_BOUNDARY_POLICY_SNAPSHOT_KEY,
    cleanup_new_run_directory,
    resolve_unitizer_presentation_for_user,
)


BASE_URL = "https://wc.bearhive.duckdns.org"
CONFIG = "disturbed9002_wbt"
EMAIL_A = "surf14a-local-a@example.invalid"
EMAIL_B = "surf14a-local-b@example.invalid"
CSRF_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)"')
RQ_TOKEN_RE = re.compile(r'name="rq_token" value="([^"]+)"')
RUN_RE = re.compile(r"/runs/([^/]+)/disturbed9002_wbt(?:/|$)")


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _session_for(user: User) -> tuple[requests.Session, str]:
    """Materialize a real server-side Flask-Security session for a test user."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = user.fs_uniquifier
        session["_fresh"] = True
    response = client.get("/profile")
    assert response.status_code == 200
    cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
    cookie = client.get_cookie(cookie_name)
    assert cookie is not None
    session_id = cookie.value.split(".", 1)[0]
    assert session_id
    session = requests.Session()
    session.cookies.set(
        cookie_name,
        cookie.value,
        domain="wc.bearhive.duckdns.org",
        path="/",
    )
    profile = session.get(f"{BASE_URL}/weppcloud/profile", timeout=30)
    profile.raise_for_status()
    assert user.email in profile.text
    return session, session_id


def _csrf(session: requests.Session) -> str:
    response = session.get(f"{BASE_URL}/weppcloud/preferences", timeout=30)
    response.raise_for_status()
    match = CSRF_RE.search(response.text)
    assert match is not None
    return match.group(1)


def _save_preferences(
    session: requests.Session,
    unit_system: str,
    boundary_behavior: str,
) -> None:
    response = session.post(
        f"{BASE_URL}/weppcloud/preferences",
        data={
            "csrf_token": _csrf(session),
            "unit_system": unit_system,
            "wbt_boundary_touch_behavior": boundary_behavior,
        },
        allow_redirects=False,
        timeout=30,
    )
    assert response.status_code == 302, response.text


def _rq_token(session: requests.Session) -> str:
    response = session.get(f"{BASE_URL}/weppcloud/create", timeout=30)
    response.raise_for_status()
    match = RQ_TOKEN_RE.search(response.text)
    assert match is not None
    return match.group(1)


def _submit_boundary_job(token: str, runid: str) -> str:
    response = requests.post(
        f"{BASE_URL}/rq-engine/api/runs/{runid}/{CONFIG}/"
        "build-subcatchments-and-abstract-watershed",
        headers={"Authorization": f"Bearer {token}"},
        json={},
        timeout=30,
    )
    response.raise_for_status()
    job_id = response.json().get("job_id")
    assert isinstance(job_id, str) and job_id
    return job_id


def _service_token(runid: str) -> str:
    payload = auth_tokens.issue_token(
        "surf14a-local-service",
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={
            "token_class": "service",
            "roles": ["Root"],
            "runs": [runid],
            "jti": uuid.uuid4().hex,
        },
    )
    token = payload.get("token")
    assert isinstance(token, str) and token
    return token


def main() -> None:
    runid: str | None = None
    run_wd: str | None = None
    run_pk: int | None = None
    user_ids: list[int] = []
    job_ids: list[str] = []
    sessions: list[tuple[requests.Session, str]] = []
    acceptance_summary: dict[str, object] | None = None
    redis_conn = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
    session_redis = redis.Redis(**redis_connection_kwargs(RedisDB.SESSION))
    state_redis = {
        db: redis.Redis(**redis_connection_kwargs(db))
        for db in (RedisDB.LOCK, RedisDB.WD_CACHE, RedisDB.NODB_CACHE)
    }
    with app.app_context():
        before_counts = {
            "users": db.session.query(User).count(),
            "preferences": db.session.query(UserPreferences).count(),
            "roles_users": db.session.execute(
                db.select(db.func.count()).select_from(roles_users)
            ).scalar_one(),
            "runs_users": db.session.execute(
                db.select(db.func.count()).select_from(runs_users)
            ).scalar_one(),
        }
        collisions = User.query.filter(User.email.in_([EMAIL_A, EMAIL_B])).count()
        assert collisions == 0, "Disposable acceptance email already exists."
        role = Role.query.filter_by(name="User").one()
        now = datetime.now(timezone.utc)
        user_a = user_datastore.create_user(
            email=EMAIL_A,
            fs_uniquifier=uuid.uuid4().hex,
            active=True,
            confirmed_at=now,
        )
        user_b = user_datastore.create_user(
            email=EMAIL_B,
            fs_uniquifier=uuid.uuid4().hex,
            active=True,
            confirmed_at=now,
        )
        user_datastore.add_role_to_user(user_a, role)
        user_datastore.add_role_to_user(user_b, role)
        db.session.commit()
        user_ids = [user_a.id, user_b.id]
        try:
            session_a, session_id_a = _session_for(user_a)
            sessions.append((session_a, session_id_a))
            session_b, session_id_b = _session_for(user_b)
            sessions.append((session_b, session_id_b))
            _save_preferences(session_a, "si", "error")
            _save_preferences(session_b, "english", "warn")

            token_a = _rq_token(session_a)
            create = session_a.post(
                f"{BASE_URL}/rq-engine/create/",
                data={"config": CONFIG, "rq_token": token_a},
                allow_redirects=False,
                timeout=60,
            )
            if create.status_code != 303:
                try:
                    create_payload = create.json()
                except requests.JSONDecodeError:
                    create_payload = {}
                acceptance_summary = {
                    "status": "create_failed",
                    "create_status_code": create.status_code,
                    "error_id": create_payload.get("error_id"),
                    "before_counts": before_counts,
                    "user_ids": user_ids,
                    "session_receipt_count": len(sessions),
                }
            assert create.status_code == 303, create.text
            match = RUN_RE.search(create.headers["Location"])
            assert match is not None
            runid = match.group(1)
            run = Run.query.filter_by(runid=runid).one()
            run_pk = run.id
            run_wd = run.wd
            db.session.execute(
                runs_users.insert().values(user_id=user_b.id, run_id=run.id)
            )
            db.session.commit()

            unitizer_path = os.path.join(run_wd, "unitizer.nodb")
            unitizer_hash = _sha256(unitizer_path)
            project_is_english = Unitizer.getInstance(run_wd).is_english
            run_url = f"{BASE_URL}/weppcloud/runs/{runid}/{CONFIG}/"
            page_a = session_a.get(run_url, timeout=30)
            page_b = session_b.get(run_url, timeout=30)
            page_a.raise_for_status()
            page_b.raise_for_status()
            assert re.search(r'value="0"\s+checked', page_a.text)
            assert re.search(r'value="1"\s+checked', page_b.text)
            assert _sha256(unitizer_path) == unitizer_hash

            _save_preferences(session_a, "config", "error")
            page_auto = session_a.get(run_url, timeout=30)
            page_auto.raise_for_status()
            auto_value = "1" if project_is_english else "0"
            assert re.search(rf'value="{auto_value}"\s+checked', page_auto.text)
            _save_preferences(session_a, "si", "error")

            anonymous_units = resolve_unitizer_presentation_for_user(run_wd, None)
            assert anonymous_units.is_english is project_is_english
            assert _sha256(unitizer_path) == unitizer_hash

            watershed = Watershed.getInstance(run_wd)
            durable_before = (
                watershed.wbt_boundary_touch_behavior,
                watershed.wbt_boundary_touch_config_behavior,
            )
            token_b = _rq_token(session_b)
            job_ids.append(_submit_boundary_job(token_a, runid))
            job_ids.append(_submit_boundary_job(token_b, runid))
            _save_preferences(session_a, "si", "config")
            job_ids.append(_submit_boundary_job(token_a, runid))
            job_ids.append(_submit_boundary_job(_service_token(runid), runid))
            jobs = [Job.fetch(job_id, connection=redis_conn) for job_id in job_ids]
            snapshots = [
                job.meta.get(WBT_BOUNDARY_POLICY_SNAPSHOT_KEY) for job in jobs
            ]
            assert [item["actor_user_id"] for item in snapshots[:2]] == user_ids
            assert [item["effective_policy"] for item in snapshots[:2]] == [
                "error",
                "warn",
            ]
            assert snapshots[2]["actor_user_id"] == user_a.id
            assert snapshots[2]["effective_policy"] == durable_before[1]
            assert snapshots[2]["source"] == "project_config"
            assert snapshots[3] is None
            assert jobs[3].args[2] is None
            for job in jobs:
                public = get_wepppy_rq_job_info(job.id)
                assert WBT_BOUNDARY_POLICY_SNAPSHOT_KEY not in json.dumps(public)
            watershed = Watershed.getInstance(run_wd)
            assert (
                watershed.wbt_boundary_touch_behavior,
                watershed.wbt_boundary_touch_config_behavior,
            ) == durable_before
            assert _sha256(unitizer_path) == unitizer_hash

            acceptance_summary = {
                "status": "pass",
                "runid": runid,
                "run_pk": run_pk,
                "user_ids": user_ids,
                "role_id": role.id,
                "runs_users_receipt": [user_b.id, run_pk],
                "job_ids": list(job_ids),
                "session_receipt_count": len(sessions),
                "unit_views_distinct": True,
                "auto_matches_project": True,
                "anonymous_resolver_matches_project": True,
                "unitizer_sha256": unitizer_hash,
                "wbt_effective_policies": [
                    "error",
                    "warn",
                    durable_before[1],
                    durable_before[1],
                ],
                "wbt_config_and_service_fallback": True,
                "private_snapshot_redacted": True,
                "durable_boundary_fields": durable_before,
                "before_counts": before_counts,
            }
        finally:
            db.session.rollback()
            cleanup_errors: list[BaseException] = []
            for http_session, session_id in sessions:
                try:
                    http_session.get(
                        f"{BASE_URL}/weppcloud/logout",
                        allow_redirects=False,
                        timeout=30,
                    )
                    session_redis.delete(f"session:{session_id}")
                except (requests.RequestException, redis.RedisError) as exc:
                    cleanup_errors.append(exc)
            for job_id in job_ids:
                try:
                    Job.fetch(job_id, connection=redis_conn).delete(
                        remove_from_queue=True
                    )
                except NoSuchJobError:
                    pass
                except (redis.RedisError, OSError, ValueError) as exc:
                    cleanup_errors.append(exc)
            if runid is not None:
                redis_conn.delete(f"rq:subcatchment-mutation-tail:{runid}")
            receipt_runs = db.session.execute(
                db.select(Run)
                .join(runs_users, runs_users.c.run_id == Run.id)
                .where(runs_users.c.user_id.in_(user_ids))
            ).scalars().all()
            if runid is not None:
                explicit_run = Run.query.filter_by(runid=runid).one_or_none()
                if explicit_run is not None and explicit_run not in receipt_runs:
                    receipt_runs.append(explicit_run)
            run_ids = [run.id for run in receipt_runs]
            if run_ids:
                db.session.execute(
                    runs_users.delete().where(runs_users.c.run_id.in_(run_ids))
                )
            if user_ids:
                db.session.execute(
                    runs_users.delete().where(runs_users.c.user_id.in_(user_ids))
                )
                db.session.execute(
                    roles_users.delete().where(roles_users.c.user_id.in_(user_ids))
                )
            for run in receipt_runs:
                if run_wd is None:
                    run_wd = run.wd
                db.session.delete(run)
            db.session.commit()
            for user_id in user_ids:
                user = db.session.get(User, user_id)
                if user is not None:
                    db.session.delete(user)
            db.session.commit()
            if runid is not None and run_wd is not None and os.path.isdir(run_wd):
                try:
                    cleanup_new_run_directory(runid, run_wd)
                except (OSError, redis.RedisError, RuntimeError, ValueError) as exc:
                    cleanup_errors.append(exc)
            if runid is not None and run_wd is not None:
                access_log = os.path.join(
                    os.path.dirname(run_wd),
                    f".{runid}",
                )
                try:
                    if os.path.exists(access_log):
                        os.unlink(access_log)
                except OSError as exc:
                    cleanup_errors.append(exc)

            assert User.query.filter(User.email.in_([EMAIL_A, EMAIL_B])).count() == 0
            assert all(db.session.get(User, user_id) is None for user_id in user_ids)
            after_counts = {
                "users": db.session.query(User).count(),
                "preferences": db.session.query(UserPreferences).count(),
                "roles_users": db.session.execute(
                    db.select(db.func.count()).select_from(roles_users)
                ).scalar_one(),
                "runs_users": db.session.execute(
                    db.select(db.func.count()).select_from(runs_users)
                ).scalar_one(),
            }
            assert after_counts == before_counts, (before_counts, after_counts)
            if runid is not None:
                try:
                    assert not state_redis[RedisDB.LOCK].exists(runid)
                    assert not state_redis[RedisDB.WD_CACHE].exists(runid)
                    target = (
                        str(Path(run_wd).resolve()) if run_wd is not None else ""
                    )
                    assert not any(
                        state_redis[RedisDB.NODB_CACHE].scan_iter(
                            match=f"{target}{os.sep}*",
                            count=100,
                        )
                    )
                except (AssertionError, redis.RedisError) as exc:
                    cleanup_errors.append(exc)
            if cleanup_errors:
                if acceptance_summary is not None:
                    acceptance_summary["status"] = "checks_passed_cleanup_pending"
                    acceptance_summary["after_counts"] = after_counts
                    acceptance_summary["cleanup_complete"] = False
                    print(json.dumps(acceptance_summary, sort_keys=True))
                raise RuntimeError(
                    "Acceptance cleanup requires operator completion."
                ) from cleanup_errors[0]
            if acceptance_summary is not None:
                acceptance_summary["after_counts"] = after_counts
                acceptance_summary["cleanup_complete"] = True
                print(json.dumps(acceptance_summary, sort_keys=True))


if __name__ == "__main__":
    main()
