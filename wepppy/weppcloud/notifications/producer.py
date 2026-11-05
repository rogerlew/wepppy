"""Read-only TTL observations and retry-safe notification reconciliation."""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
import time
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from wepppy.weppcloud.run_catalog.paths import Roots, project_directory, read_source
from .schema import notifications as n, recipients as r, runs, memberships

logger = logging.getLogger(__name__)
SWEEP_LOCK = 802411051
BATCH_SIZE = 100


def _decode_ttl(raw, now):
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("TTL must be an object")
    policy = payload.get("policy")
    disabled = payload.get("user_disabled", False)
    if not isinstance(policy, str) or type(disabled) is not bool:
        raise ValueError("Invalid TTL protection")
    if policy in {"disabled", "excluded"} or disabled:
        return "resolved", None
    state = payload.get("delete_state", "active")
    if not isinstance(state, str):
        raise ValueError("Invalid deletion state")
    if state in {"queued", "trash", "purged"}:
        return "resolved", None
    if policy != "rolling_90d" or state != "active":
        raise ValueError("Unsupported TTL state")
    raw_date = payload.get("expires_at")
    if not isinstance(raw_date, str):
        raise ValueError("Missing expiration")
    expiration = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    if expiration.tzinfo is None or expiration.utcoffset() is None:
        raise ValueError("Expiration requires timezone")
    expiration = expiration.astimezone(timezone.utc)
    return ("active" if expiration <= now + timedelta(days=14) else "resolved"), expiration


def observe_ttl(runid, now, roots):
    """Read descriptor-bound source files without access refresh or repair."""
    try:
        candidates = roots.candidates(runid)
        for root, relative in candidates:
            if os.path.abspath(root) == os.path.abspath(roots.batch):
                return "resolved", None
            try:
                with project_directory(root, relative) as (descriptor, _):
                    locators = [os.path.join(root, *relative)]
                    try:
                        read_source(descriptor, "READONLY", locators)
                    except FileNotFoundError:
                        pass
                    else:
                        return "resolved", None
                    # Missing TTL in an existing project is unknown, not a reason
                    # to fall through to a potentially older legacy directory.
                    try:
                        raw, _, _ = read_source(descriptor, "TTL", locators)
                    except FileNotFoundError:
                        return "unavailable", None
                    return _decode_ttl(raw, now)
            except FileNotFoundError:
                continue
    except (OSError, ValueError, UnicodeError, OverflowError, RecursionError):
        logger.warning("Notification TTL observation unavailable runid=%r", runid, exc_info=True)
    return "unavailable", None


def _reconcile(connection, registration, now, roots, stats):
    project = connection.execute(sa.select(runs).where(runs.c.id == registration)).mappings().first()
    previous = connection.execute(sa.select(n).where(n.c.kind == "project_ttl",
        n.c.subject_type == "run", n.c.subject_id == registration,
        n.c.state != "resolved")).mappings().first()
    state, expiration = observe_ttl(project["runid"], now, roots) if project else ("resolved", None)
    stats["examined"] += 1
    if state != "active":
        if previous:
            connection.execute(n.update().where(n.c.id == previous["id"]).values(state=state, updated_at=now))
        stats[state if previous or state == "unavailable" else "skipped"] += 1
        return
    recipients = list(connection.scalars(sa.select(memberships.c.user_id)
                                        .where(memberships.c.run_id == registration)))
    if not recipients and not previous:
        stats["skipped"] += 1
        return
    date = expiration.strftime("%b %d, %Y, %H:%M UTC")
    overdue = expiration <= now
    episode = previous["source_key"].rsplit(":", 1)[-1] if previous else uuid4().hex
    values = dict(title=f"Automatic deletion: {project['runid']}",
                  body=(f"The recorded automatic deletion date was {date}. This project is overdue for deletion."
                        if overdue else f"Automatic deletion is enabled for {date}."),
                  state="active", updated_at=now,
                  metadata={"expires_at": expiration.isoformat(), "overdue": overdue, "episode_id": episode})
    if previous:
        identifier = previous["id"]
        connection.execute(n.update().where(n.c.id == identifier).values(**values))
        stats["updated"] += 1
    else:
        identifier = connection.scalar(n.insert().values(**values, kind="project_ttl",
            source_key=f"project_ttl:{registration}:{episode}", subject_type="run",
            subject_id=registration, created_at=now, published_at=now).returning(n.c.id))
        stats["created"] += 1
    if recipients:
        connection.execute(insert(r).values([
            dict(notification_id=identifier, user_id=user, delivered_at=now) for user in recipients
        ]).on_conflict_do_nothing(index_elements=[r.c.notification_id, r.c.user_id]))


def reconcile_ttl_notifications(engine, now=None, registration_ids=None, roots=None):
    """Reconcile all registrations, or an explicit trusted subset (empty is no-op)."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Sweep time requires timezone")
    if registration_ids is not None:
        if (not isinstance(registration_ids, (list, tuple))
                or any(type(value) is not int or value <= 0 for value in registration_ids)):
            raise ValueError("Invalid registration scope")
    roots = roots or Roots.from_environ()
    started = time.monotonic()
    stats = dict(examined=0, created=0, updated=0, resolved=0, unavailable=0, skipped=0,
                 status="running")
    if registration_ids == [] or registration_ids == ():
        return dict(stats, status="completed", elapsed_seconds=0)
    with engine.connect() as connection:
        locked = connection.scalar(sa.select(sa.func.pg_try_advisory_lock(SWEEP_LOCK)))
        connection.commit()
        if not locked:
            return dict(stats, status="already_running", elapsed_seconds=time.monotonic() - started)
        try:
            subjects = sa.union(sa.select(runs.c.id.label("id")), sa.select(n.c.subject_id.label("id"))
                .where(n.c.kind == "project_ttl", n.c.subject_type == "run", n.c.state != "resolved")).subquery()
            cursor = 0
            while True:
                query = sa.select(subjects.c.id).where(subjects.c.id > cursor).order_by(subjects.c.id).limit(BATCH_SIZE)
                if registration_ids is not None:
                    query = query.where(subjects.c.id.in_(registration_ids))
                with connection.begin():
                    batch = list(connection.scalars(query))
                    batch_stats = dict(stats)
                    for registration in batch:
                        _reconcile(connection, registration, now, roots, batch_stats)
                stats = batch_stats
                if not batch:
                    break
                cursor = batch[-1]
            stats["status"] = "completed"
        finally:
            # Deliberate cleanup boundary: release a session lock even after a
            # rolled-back batch. Discard a connection if unlock itself fails.
            connection.rollback()
            try:
                connection.execute(sa.select(sa.func.pg_advisory_unlock(SWEEP_LOCK)))
                connection.commit()
            except sa.exc.SQLAlchemyError:
                connection.invalidate()
                raise
            stats["elapsed_seconds"] = round(time.monotonic() - started, 3)
            if stats["status"] != "completed":
                stats["status"] = "failed"
            logger.info("notification_sweep progress=%s", stats)
    return stats
