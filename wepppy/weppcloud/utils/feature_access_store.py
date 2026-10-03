"""Transactional account access records. No request parsing or Flask imports."""

from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from .feature_access_schema import acceptances, events, groups, memberships, roles, roles_users, users


class FeatureAccessValidationError(ValueError):
    """Invalid account/group, dates or reason."""


class FeatureAccessConflict(FeatureAccessValidationError):
    """An active membership already has different metadata."""


class FeatureAccessUnavailableError(RuntimeError):
    """Required account authorization configuration is unavailable."""


def utc_now():
    return datetime.now(timezone.utc)


def _identifier(value):
    if type(value) is not int or value <= 0:
        raise FeatureAccessValidationError("Expected a positive canonical account ID")
    return value


def _date(value):
    if value is not None and (not isinstance(value, datetime) or value.utcoffset() is None):
        raise FeatureAccessValidationError("Expected a timezone-aware timestamp")
    return value.astimezone(timezone.utc) if value is not None else None


class FeatureAccessStore:
    """Use the existing account engine (Flask db.engine or service-owned engine).

    Write methods own one transaction. User row locks serialize membership and
    acknowledgment writes, including absent-row duplicate grants. Reads always
    hit the database; instances hold no membership or identity cache.
    """

    def __init__(self, engine):
        self.engine = engine

    def seed_groups(self, features):
        """Idempotently create registered definitions; never seed memberships."""
        with self.engine.begin() as connection:
            for feature in features:
                if feature.access_group:
                    connection.execute(insert(groups).values(
                        key=feature.access_group, label=feature.label, active=True,
                    ).on_conflict_do_nothing(index_elements=[groups.c.key]))

    def membership(self, user_id, group_key, *, statement_version=None, now=None):
        """Return (effective membership, current acknowledgment); missing config raises."""
        _identifier(user_id)
        now = _date(now) if now is not None else sa.func.clock_timestamp()
        with self.engine.connect() as connection:
            group = connection.execute(sa.select(groups).where(groups.c.key == group_key)).mappings().one_or_none()
            if group is None or not group.active:
                raise FeatureAccessValidationError("Missing or inactive feature group")
            active = connection.execute(sa.select(users.c.active).where(users.c.id == user_id)).scalar_one_or_none()
            if active is not True:
                return False, False
            member = connection.execute(sa.select(memberships.c.id).where(
                memberships.c.group_id == group.id, memberships.c.user_id == user_id,
                sa.or_(memberships.c.expires_at.is_(None), memberships.c.expires_at > now),
            )).scalar_one_or_none() is not None
            acknowledged = False
            if member and statement_version:
                acknowledged = connection.execute(sa.select(acceptances.c.id).where(
                    acceptances.c.user_id == user_id,
                    acceptances.c.statement_kind == "internal",
                    acceptances.c.statement_version == statement_version,
                )).scalar_one_or_none() is not None
            return member, acknowledged

    def change_membership(self, *, actor_id, user_id, group_key, operation, reason,
                          features, review_at=None, expires_at=None):
        """Root-only add/remove plus immutable scope snapshot, committed atomically."""
        return self.change_membership_status(
            actor_id=actor_id, user_id=user_id, group_key=group_key, operation=operation,
            reason=reason, features=features, review_at=review_at, expires_at=expires_at,
        )["changed"]

    def change_membership_status(self, *, actor_id, user_id, group_key, operation, reason,
                                 features, review_at=None, expires_at=None):
        """Return changed/effective status inside the mutation transaction."""
        with self.engine.begin() as connection:
            changed = self._change_membership(
                connection, actor_id=actor_id, user_id=user_id, group_key=group_key,
                operation=operation, reason=reason, features=features,
                review_at=review_at, expires_at=expires_at,
            )
            effective = connection.execute(sa.select(memberships.c.id).select_from(
                memberships.join(groups).join(users)
            ).where(users.c.id == user_id, users.c.active.is_(True), groups.c.key == group_key,
                    groups.c.active.is_(True), sa.or_(memberships.c.expires_at.is_(None),
                    memberships.c.expires_at > sa.func.clock_timestamp()))).first() is not None
            return {"changed": changed, "member": effective}

    def _change_membership(self, connection, *, actor_id, user_id, group_key, operation,
                           reason, features, review_at=None, expires_at=None):
        _identifier(actor_id)
        _identifier(user_id)
        if operation not in {"add", "remove"} or not isinstance(reason, str) or not reason.strip():
            raise FeatureAccessValidationError("Operation and nonblank reason are required")
        review_at, expires_at = _date(review_at), _date(expires_at)
        if operation == "remove" and (review_at is not None or expires_at is not None):
            raise FeatureAccessValidationError("Remove does not accept date fields")
        scope = sorted(
            ({"feature_id": f.id, "access_mode": f.access_mode}
             for f in features if f.access_group == group_key),
            key=lambda item: item["feature_id"],
        )
        if not scope:
            raise FeatureAccessValidationError("Group is not registered to a feature")
        actor_root = connection.execute(sa.select(users.c.id).select_from(
            users.join(roles_users, users.c.id == roles_users.c.user_id)
            .join(roles, roles.c.id == roles_users.c.role_id)
        ).where(users.c.id == actor_id, users.c.active.is_(True), roles.c.name == "Root")).first()
        if actor_root is None:
            raise PermissionError("Only an active Root account can manage feature membership")
        target = connection.execute(sa.select(users.c.id).where(users.c.id == user_id).with_for_update()).first()
        if target is None:
            raise FeatureAccessValidationError("Unknown user")
        group = connection.execute(sa.select(groups).where(groups.c.key == group_key).with_for_update()).mappings().one_or_none()
        if group is None or not group.active:
            raise FeatureAccessValidationError("Missing or inactive feature group")
        # Pool and row-lock waits may cross an expiry boundary.
        now = utc_now()
        if expires_at is not None and expires_at <= now:
            raise FeatureAccessValidationError("Expiry must be in the future")
        predicate = sa.and_(memberships.c.group_id == group.id, memberships.c.user_id == user_id)
        member = connection.execute(sa.select(memberships).where(predicate)).mappings().one_or_none()
        if operation == "add":
            if member is not None and (member.expires_at is None or member.expires_at > now):
                if (member.review_at, member.expires_at) != (review_at, expires_at):
                    raise FeatureAccessConflict("Active membership has different dates; remove then add")
                return False
            values = dict(review_at=review_at, expires_at=expires_at, created_at=now)
            if member is None:
                connection.execute(memberships.insert().values(group_id=group.id, user_id=user_id, **values))
            else:
                connection.execute(memberships.update().where(predicate).values(**values))
        else:
            if member is None:
                return False
            review_at, expires_at = member.review_at, member.expires_at
            connection.execute(memberships.delete().where(predicate))
        connection.execute(events.insert().values(
            actor_id=actor_id, user_id=user_id, group_id=group.id, group_key=group.key,
            feature_scope=scope, action=operation, reason=reason.strip(), created_at=now,
            review_at=review_at, expires_at=expires_at,
        ))
        return True

    def acknowledge_internal(self, user_id, statement_version):
        """Trusted current-user acceptance; HTTP validation belongs to milestone two."""
        _identifier(user_id)
        if not isinstance(statement_version, str) or not statement_version.strip():
            raise FeatureAccessValidationError("Statement version is required")
        with self.engine.begin() as connection:
            user = connection.execute(sa.select(users.c.id).where(
                users.c.id == user_id, users.c.active.is_(True),
            ).with_for_update()).first()
            if user is None:
                raise FeatureAccessValidationError("Unknown or inactive user")
            result = connection.execute(insert(acceptances).values(
                user_id=user_id, statement_kind="internal", statement_version=statement_version,
            ).on_conflict_do_nothing(index_elements=[
                acceptances.c.user_id, acceptances.c.statement_kind, acceptances.c.statement_version,
            ]).returning(acceptances.c.id))
            return result.scalar_one_or_none() is not None

    def approve_poweruser(self, user_id, statement_version, decision_rule):
        """Record an explicit acceptance and ensure PowerUser in one transaction."""
        _identifier(user_id)
        if not isinstance(statement_version, str) or not statement_version.strip():
            raise FeatureAccessValidationError("Statement version is required")
        if not isinstance(decision_rule, str) or not decision_rule.strip():
            raise FeatureAccessValidationError("Decision rule is required")
        with self.engine.begin() as connection:
            user = connection.execute(sa.select(users.c.id).where(
                users.c.id == user_id, users.c.active.is_(True),
            ).with_for_update()).first()
            if user is None:
                raise FeatureAccessValidationError("Unknown or inactive user")
            role_id = connection.execute(sa.select(roles.c.id).where(
                roles.c.name == "PowerUser",
            )).scalar_one_or_none()
            if role_id is None:
                raise FeatureAccessUnavailableError("PowerUser role is not configured")
            role_exists = connection.execute(sa.select(roles_users.c.user_id).where(
                roles_users.c.user_id == user_id,
                roles_users.c.role_id == role_id,
            )).first() is not None
            if not role_exists:
                connection.execute(roles_users.insert().values(
                    user_id=user_id,
                    role_id=role_id,
                ))
            now = utc_now()
            acceptance = connection.execute(insert(acceptances).values(
                user_id=user_id,
                statement_kind="poweruser",
                statement_version=statement_version,
                decision_rule=decision_rule.strip(),
                approved_at=now,
            ).on_conflict_do_nothing(index_elements=[
                acceptances.c.user_id,
                acceptances.c.statement_kind,
                acceptances.c.statement_version,
            ]).returning(acceptances.c.id)).scalar_one_or_none()
            return {
                "status": "granted",
                "role_changed": not role_exists,
                "acceptance_changed": acceptance is not None,
                "statement_version": statement_version,
            }

    def initialize_maintainer(self, user_id, *, features, reason):
        """Explicit deployment operation: sole OpenET/Batch member, one transaction.

        Caller resolves the designated email in this deployment. Refuse to erase
        existing decisions or renew an expired grant during initialization.
        """
        _identifier(user_id)
        keys = ("batch_runner", "openet_ts")
        with self.engine.begin() as connection:
            connection.execute(sa.select(users.c.id).where(users.c.id == user_id).with_for_update()).first()
            for key in keys:
                group_id = connection.execute(sa.select(groups.c.id).where(
                    groups.c.key == key, groups.c.active.is_(True),
                ).with_for_update()).scalar_one_or_none()
                if group_id is None:
                    raise FeatureAccessValidationError("Missing or inactive feature group")
                rows = connection.execute(sa.select(memberships).where(
                    memberships.c.group_id == group_id,
                )).mappings().all()
                if any(row.user_id != user_id or row.expires_at is not None or row.review_at is not None for row in rows):
                    raise FeatureAccessConflict("Initialization requires empty groups or the unchanged sole maintainer")
            return {key: self._change_membership(
                connection, actor_id=user_id, user_id=user_id, group_key=key,
                operation="add", reason=reason, features=features,
            ) for key in keys}

    def account_status(self, user_id, statement_version, *, poweruser_statement_version=None):
        """Own membership status only; no event reasons or other account data."""
        _identifier(user_id)
        with self.engine.connect() as connection:
            acknowledged = connection.execute(sa.select(acceptances.c.id).where(
                acceptances.c.user_id == user_id, acceptances.c.statement_kind == "internal",
                acceptances.c.statement_version == statement_version,
            )).first() is not None
            rows = connection.execute(sa.select(
                groups.c.key, groups.c.label, groups.c.active,
                memberships.c.created_at, memberships.c.review_at, memberships.c.expires_at,
                sa.or_(memberships.c.expires_at.is_(None),
                       memberships.c.expires_at > sa.func.clock_timestamp()).label("unexpired"),
            ).select_from(memberships.join(groups)).where(
                memberships.c.user_id == user_id,
            ).order_by(groups.c.key)).mappings().all()
            poweruser = None
            if poweruser_statement_version is not None:
                poweruser = {
                    "has_role": connection.execute(sa.select(roles_users.c.user_id).select_from(
                        roles_users.join(roles, roles_users.c.role_id == roles.c.id)
                    ).where(
                        roles_users.c.user_id == user_id,
                        roles.c.name == "PowerUser",
                    )).first() is not None,
                    "accepted": connection.execute(sa.select(acceptances.c.id).where(
                        acceptances.c.user_id == user_id,
                        acceptances.c.statement_kind == "poweruser",
                        acceptances.c.statement_version == poweruser_statement_version,
                    )).first() is not None,
                }
        return {"acknowledged": acknowledged, "memberships": rows, "poweruser": poweruser}

    def administration(self, *, before_event_id=None):
        """Root adapter's inventory; page retained history without dropping old events."""
        if before_event_id is not None:
            _identifier(before_event_id)
        with self.engine.connect() as connection:
            definitions = connection.execute(sa.select(groups).order_by(groups.c.key)).mappings().all()
            members = connection.execute(sa.select(
                memberships, groups.c.key.label("group_key"), users.c.active.label("account_active"),
                sa.or_(memberships.c.expires_at.is_(None),
                       memberships.c.expires_at > sa.func.clock_timestamp()).label("unexpired"),
            ).select_from(memberships.join(groups).join(users)).order_by(groups.c.key, memberships.c.user_id)).mappings().all()
            query = sa.select(events).order_by(events.c.id.desc()).limit(101)
            if before_event_id is not None:
                query = query.where(events.c.id < before_event_id)
            history = connection.execute(query).mappings().all()
        return {"groups": definitions, "memberships": members, "events": history[:100],
                "older_than": history[99].id if len(history) > 100 else None}
