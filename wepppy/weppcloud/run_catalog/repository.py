"""Short SQL invalidations and fenced snapshot publication."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import time
import logging

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DataError, IntegrityError

from .extractor import extract
from .schema import catalog, runs

__all__ = ["seed", "invalidate", "refresh", "candidates", "status", "utcnow"]


def utcnow():
    return datetime.now(timezone.utc)


def seed(connection, limit=50, run_id=None, apply=True):
    query = sa.select(runs.c.id).outerjoin(catalog, runs.c.id == catalog.c.run_id).where(catalog.c.run_id.is_(None))
    if run_id is not None:
        query = query.where(runs.c.id == run_id)
    identifiers = list(connection.scalars(query.order_by(runs.c.id).limit(limit)))
    if apply:
        for identifier in identifiers:
            connection.execute(insert(catalog).from_select(
                ["run_id", "projection_id"],
                sa.select(runs.c.id, sa.literal(uuid4())).where(runs.c.id == identifier),
            ).on_conflict_do_nothing(index_elements=[catalog.c.run_id]))
    return identifiers


def invalidate(connection, runid, committed_at=None):
    now = committed_at or utcnow()
    statement = insert(catalog).from_select(
        ["run_id", "projection_id", "invalidated_at", "dirty_since", "next_attempt_at"],
        sa.select(runs.c.id, sa.literal(uuid4()), sa.literal(now), sa.literal(now), sa.literal(now)).where(runs.c.runid == runid),
    )
    return connection.execute(statement.on_conflict_do_update(
        index_elements=[catalog.c.run_id],
        set_={
            "dirty_revision": catalog.c.dirty_revision + 1,
            "dirty_since": sa.case((catalog.c.dirty_revision == catalog.c.indexed_revision, now), else_=catalog.c.dirty_since),
            "invalidated_at": sa.func.greatest(catalog.c.invalidated_at, now),
            "next_attempt_at": sa.func.now(),
        },
    )).rowcount


def refresh(engine, run_id, roots=None, extractor=extract, now=None, publication_guard=None, metrics=None):
    started = time.monotonic()
    fixed_now = now
    now = now or utcnow()
    with engine.begin() as connection:
        if not connection.scalar(sa.select(sa.func.pg_try_advisory_xact_lock(1381322307, run_id))):
            return "busy"
        row = connection.execute(sa.select(catalog, runs.c.runid).join(runs, runs.c.id == catalog.c.run_id)
                                 .where(catalog.c.run_id == run_id)).mappings().first()
        if row is None:
            return "absent"
        source_started = time.monotonic()
        snapshot = extractor(row["runid"], roots=roots, now=now)
        if snapshot.verify is not None:
            snapshot.verify()
        source_seconds = time.monotonic() - source_started
        if publication_guard is not None:
            publication_guard()
        if metrics is not None:
            metrics.update(source_seconds=source_seconds, sql_acquire_seconds=source_started - started)
        completed_at = fixed_now or utcnow()
        complete = all(observation.state != "unreadable" for observation in snapshot.sources.values())
        versions = dict(row["source_versions"])
        values = dict(source_locator=snapshot.locator, last_attempt_at=now, projection_version=1)
        errors = []
        for source, observation in snapshot.sources.items():
            values[source + "_state"] = observation.state
            if observation.error:
                errors.append(observation.error)
            if observation.state == "unreadable":
                if source == "ttl":
                    values["ttl_deletion_at"] = None
                continue
            versions[source] = observation.version
            values[source + "_observed_at"] = now
            values.update(observation.values)
            if source == "ron" and observation.state != "ready":
                values.update(name=None, scenario=None, map_lng=None, map_lat=None, map_zoom=None)
            if source == "ttl" and observation.state != "ready":
                values.update(ttl_policy=None, ttl_deletion_at=None)
        values.update(source_versions=versions, last_error_code=errors[0] if errors else None)
        concurrent = catalog.c.dirty_revision > row["dirty_revision"]
        values["next_attempt_at"] = sa.case((concurrent, catalog.c.next_attempt_at), else_=completed_at + timedelta(seconds=60))
        values["next_reconcile_at"] = completed_at + (timedelta(hours=12) if complete else timedelta(seconds=60))
        if complete:
            values.update(indexed_revision=row["dirty_revision"], refreshed_at=now, reconciled_at=now)
        else:
            values.update(
                dirty_revision=sa.case((catalog.c.dirty_revision == catalog.c.indexed_revision, catalog.c.dirty_revision + 1), else_=catalog.c.dirty_revision),
                dirty_since=sa.case((catalog.c.dirty_revision == catalog.c.indexed_revision, now), else_=catalog.c.dirty_since),
            )
        statement = catalog.update().where(
            catalog.c.run_id == run_id, catalog.c.projection_id == row["projection_id"]
        )
        publish_started = time.monotonic()
        try:
            with connection.begin_nested():
                result = connection.execute(statement.values(**values))
        except (DataError, IntegrityError, ValueError, UnicodeError):
            logging.getLogger(__name__).warning("catalog_publish_failed run_id=%s", run_id)
            result = connection.execute(statement.values(
                last_attempt_at=completed_at, last_error_code="catalog_publish_failed",
                dirty_revision=sa.case((catalog.c.dirty_revision == catalog.c.indexed_revision, catalog.c.dirty_revision + 1), else_=catalog.c.dirty_revision),
                dirty_since=sa.case((catalog.c.dirty_revision == catalog.c.indexed_revision, completed_at), else_=catalog.c.dirty_since),
                next_attempt_at=sa.case((concurrent, catalog.c.next_attempt_at), else_=completed_at + timedelta(seconds=60)),
                next_reconcile_at=completed_at + timedelta(seconds=60), ttl_deletion_at=None,
            ))
            return "retry" if result.rowcount else "discarded"
        finally:
            if metrics is not None:
                metrics["sql_publish_seconds"] = time.monotonic() - publish_started
        return ("ready" if complete else "retry") if result.rowcount else "discarded"


def candidates(connection, limit=50, now=None):
    now = now or utcnow()
    reserve = (limit + 3) // 4
    due = list(connection.scalars(sa.select(catalog.c.run_id).where(catalog.c.next_reconcile_at <= now)
                                 .order_by(catalog.c.next_reconcile_at, catalog.c.run_id).limit(limit)))
    dirty = list(connection.scalars(sa.select(catalog.c.run_id).where(
        catalog.c.dirty_revision > catalog.c.indexed_revision, catalog.c.next_attempt_at <= now,
    ).order_by(catalog.c.next_attempt_at, catalog.c.dirty_since, catalog.c.run_id).limit(limit)))
    return list(dict.fromkeys(due[:reserve] + dirty + due[reserve:]))[:limit]


def status(connection):
    result = dict(connection.execute(sa.select(
        sa.func.count().label("projected"),
        sa.func.count().filter(catalog.c.dirty_revision > catalog.c.indexed_revision).label("dirty"),
        sa.func.count().filter(catalog.c.ron_state == "pending").label("pending"),
        sa.func.count().filter(catalog.c.ron_state == "ready", catalog.c.readonly_state == "ready").label("ready"),
        sa.func.count().filter(catalog.c.ron_state.in_(["missing", "invalid", "unreadable"])).label("unavailable"),
        sa.func.min(catalog.c.dirty_since).filter(catalog.c.dirty_revision > catalog.c.indexed_revision).label("oldest_dirty_at"),
        sa.func.min(catalog.c.reconciled_at).label("oldest_reconciled_at"),
        sa.func.max(catalog.c.last_attempt_at).label("latest_attempt_at"),
        sa.func.count().filter(catalog.c.last_error_code.is_not(None)).label("errors"),
        sa.func.count().filter(sa.or_(catalog.c.ron_state == "unreadable", catalog.c.readonly_state == "unreadable", catalog.c.ttl_state == "unreadable",
                                     catalog.c.last_error_code.in_(["source_io_error", "source_scope_mismatch", "source_drift", "catalog_publish_failed"]))).label("transient_failures"),
        sa.func.count().filter(catalog.c.reconciled_at.is_(None)).label("unreconciled"),
    )).mappings().one())
    result["registered"] = connection.scalar(sa.select(sa.func.count()).select_from(runs))
    return result
