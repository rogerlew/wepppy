"""Explicit SQL-only catalog payloads with authorized-scope freshness counts."""

from datetime import datetime, timedelta, timezone

from .schema import catalog

__all__ = ["collect", "classify", "public_row"]


def _recent(value, now):
    return value is not None and now - value <= timedelta(hours=24)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def classify(row, now=None):
    now = now or datetime.now(timezone.utc)
    if row["projection_id"] is None or (row["last_attempt_at"] is None and row["ron_state"] == "pending"):
        return "pending"
    token = (row["source_versions"] or {}).get("ron", {})
    if row["ron_state"] in {"missing", "invalid"} or token.get("state") != "ready" or row["readonly"] is None:
        return "unavailable"
    if (row["dirty_revision"] != row["indexed_revision"] or row["ron_state"] != "ready"
            or row["readonly_state"] != "ready" or row["ttl_state"] == "unreadable"
            or not _recent(row["ron_observed_at"], now) or not _recent(row["readonly_observed_at"], now)):
        return "stale"
    return "current"


def public_row(row, owner="<anonymous>", now=None, map_only=False):
    now = now or datetime.now(timezone.utc)
    state = classify(row, now)
    if state in {"pending", "unavailable"}:
        return None
    value = {key: row[key] for key in ("runid", "config", "name", "scenario", "readonly")}
    value.update(catalog_state=state, catalog_updated_at=_iso(row["refreshed_at"]))
    if map_only:
        value.update(map_center=[row["map_lng"], row["map_lat"]] if row["map_lng"] is not None else None,
                     map_zoom=row["map_zoom"])
    else:
        value.update({key: row[key] for key in ("date_created", "last_modified", "owner_id")})
        value["owner"] = owner
        value["ttl_deletion_at"] = (_iso(row["ttl_deletion_at"])
                                    if state == "current" and row["ttl_state"] == "ready" and _recent(row["ttl_observed_at"], now)
                                    else None)
    return value


def collect(query, map_only=False):
    from wepppy.weppcloud.app import Run, User, db
    now = datetime.now(timezone.utc)
    try:
        selected = query.with_entities(
            Run.id.label("registration_id"), Run.runid, Run.config, Run.owner_id,
            Run.date_created, Run.last_modified, *catalog.c,
        ).outerjoin(catalog, catalog.c.run_id == Run.id).all()
        rows = [row._mapping for row in selected]
        owner_ids = set()
        for row in rows:
            try:
                owner_ids.add(int(row["owner_id"]))
            except (TypeError, ValueError):
                continue
        owners = {str(identifier): email for identifier, email in
                  db.session.query(User.id, User.email).filter(User.id.in_(owner_ids)).all()} if owner_ids and not map_only else {}
        counts = dict(mode="postgres", pending=0, stale=0, unavailable=0)
        values = []
        for row in rows:
            state = classify(row, now)
            if state != "current":
                counts[state] += 1
            values.append(public_row(row, owners.get(str(row["owner_id"]), "<anonymous>"), now, map_only))
        return values, counts
    finally:
        db.session.remove()
