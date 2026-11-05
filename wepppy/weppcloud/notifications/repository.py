"""SQL-only private inbox reads and atomic recipient mutations."""

from datetime import datetime, timezone

import sqlalchemy as sa

from .schema import notifications as n, recipients as r, runs, memberships

PAGE_SIZE = 100
SORTS = {"unread_first", "read_first", "newest"}


class SelectionNotFound(ValueError):
    """The entire selection must be rejected without disclosing foreign IDs."""


def _visible(user_id):
    member = sa.exists(sa.select(1).where(
        memberships.c.run_id == n.c.subject_id, memberships.c.user_id == user_id).correlate(n))
    project_exists = sa.exists(sa.select(1).where(runs.c.id == n.c.subject_id).correlate(n))
    return sa.and_(r.c.user_id == user_id,
                   sa.or_(n.c.subject_type.is_distinct_from("run"), ~project_exists, member))


def _joined():
    return n.join(r, r.c.notification_id == n.c.id)


def unread_count(connection, user_id, now=None):
    now = now or datetime.now(timezone.utc)
    exists = sa.exists(sa.select(1).where(runs.c.id == n.c.subject_id).correlate(n))
    return connection.scalar(sa.select(sa.func.count()).select_from(_joined()).where(
        _visible(user_id), r.c.read_at.is_(None), n.c.state == "active",
        n.c.published_at <= now, sa.or_(n.c.ends_at.is_(None), n.c.ends_at > now),
        sa.or_(n.c.subject_type.is_distinct_from("run"), exists)))


def list_notifications(connection, user_id, page=1, sort="unread_first", now=None):
    if type(page) is not int or page < 1 or page > 2147483647 or sort not in SORTS:
        raise ValueError("Invalid notification page or sort")
    now = now or datetime.now(timezone.utc)
    order = []
    if sort != "newest":
        order.append(r.c.read_at.is_not(None).asc() if sort == "unread_first"
                     else r.c.read_at.is_not(None).desc())
    order.extend((n.c.created_at.desc(), n.c.id.desc()))
    rows = connection.execute(sa.select(n, r.c.read_at, runs.c.runid, runs.c.config)
        .select_from(_joined().outerjoin(runs, sa.and_(n.c.subject_type == "run", runs.c.id == n.c.subject_id)))
        .where(_visible(user_id), n.c.published_at <= now)
        .order_by(*order).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)).mappings().all()
    result = []
    for row in rows[:PAGE_SIZE]:
        value = dict(row)
        if value["subject_type"] == "run" and value["runid"] is None:
            value.update(title="Project notification resolved", body="This project is no longer registered.",
                         state="resolved", metadata={}, subject_id=None)
        elif value["ends_at"] is not None and value["ends_at"] <= now:
            value["state"] = "resolved"
        result.append(value)
    return result, len(rows) > PAGE_SIZE


def validate_selection(ids, read):
    if (type(ids) is not list or not 1 <= len(ids) <= PAGE_SIZE or type(read) is not bool
            or any(type(value) is not int or not 0 < value <= 9223372036854775807 for value in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("Select between 1 and 100 distinct notifications and a read state.")


def set_read_state(engine, user_id, ids, read):
    validate_selection(ids, read)
    with engine.begin() as connection:
        # Lock in a stable order so overlapping selections cannot deadlock each other.
        selected = connection.execute(sa.select(r.c.notification_id, r.c.read_at)
            .select_from(_joined()).where(_visible(user_id), n.c.id.in_(ids),
                n.c.published_at <= sa.func.now()).order_by(r.c.notification_id)
            .with_for_update(of=r)).all()
        if len(selected) != len(ids):
            raise SelectionNotFound("Notification selection is unavailable.")
        changed = [row.notification_id for row in selected if (row.read_at is not None) != read]
        if changed:
            connection.execute(r.update().where(r.c.user_id == user_id, r.c.notification_id.in_(changed))
                               .values(read_at=datetime.now(timezone.utc) if read else None))
        count = unread_count(connection, user_id)
    return {"updated_count": len(changed), "unread_count": count}
