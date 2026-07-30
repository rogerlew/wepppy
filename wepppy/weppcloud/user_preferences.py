"""Typed account preferences and new-run snapshot helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import shutil
import stat
from typing import Any, Mapping

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

UNIT_SYSTEM_VALUES = frozenset({"config", "si", "english"})
WBT_BOUNDARY_TOUCH_BEHAVIOR_VALUES = frozenset({"config", "warn", "error"})
_RMTREE_AVOIDS_SYMLINK_ATTACKS = bool(shutil.rmtree.avoids_symlink_attacks)


class PreferenceValidationError(ValueError):
    """A submitted preference value is outside the canonical enum."""


class StoredPreferenceError(ValueError):
    """Persisted preference state violates the canonical enum."""


class PreferenceIdentityError(LookupError):
    """An account-bearing creation identity cannot resolve safely."""


@dataclass(frozen=True)
class UserPreferenceValues:
    unit_system: str = "config"
    wbt_boundary_touch_behavior: str = "config"


@dataclass(frozen=True)
class CreationPreferenceSnapshot:
    user_id: int
    email: str
    preferences: UserPreferenceValues


@dataclass(frozen=True)
class RunRegistrationReceipt:
    """Database identity for a Run row created by this request."""

    run_pk: int
    runid: str
    config: str
    user_id: int


def validate_preference_values(
    unit_system: Any,
    wbt_boundary_touch_behavior: Any,
) -> UserPreferenceValues:
    unit_value = str(unit_system or "")
    boundary_value = str(wbt_boundary_touch_behavior or "")

    if unit_value not in UNIT_SYSTEM_VALUES:
        raise PreferenceValidationError("Select a valid default unit system.")
    if boundary_value not in WBT_BOUNDARY_TOUCH_BEHAVIOR_VALUES:
        raise PreferenceValidationError(
            "Select a valid WBT DEM-boundary behavior."
        )
    return UserPreferenceValues(unit_value, boundary_value)


def _values_from_row(row: Any | None) -> UserPreferenceValues:
    if row is None:
        return UserPreferenceValues()
    try:
        return validate_preference_values(
            row.unit_system,
            row.wbt_boundary_touch_behavior,
        )
    except PreferenceValidationError as exc:
        raise StoredPreferenceError(str(exc)) from exc


def load_user_preferences(user_id: int) -> UserPreferenceValues:
    from wepppy.weppcloud.app import UserPreferences

    return _values_from_row(UserPreferences.query.filter_by(user_id=user_id).first())


def save_user_preferences(
    user_id: int,
    unit_system: Any,
    wbt_boundary_touch_behavior: Any,
) -> UserPreferenceValues:
    values = validate_preference_values(unit_system, wbt_boundary_touch_behavior)

    from wepppy.weppcloud.app import User, UserPreferences, db

    for attempt in range(2):
        try:
            user = db.session.execute(
                db.select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            if user is None:
                db.session.rollback()
                raise PreferenceIdentityError("Current user no longer exists.")

            row = db.session.execute(
                db.select(UserPreferences)
                .where(UserPreferences.user_id == user_id)
                .with_for_update()
            ).scalar_one_or_none()
            if row is None:
                row = UserPreferences(user_id=user_id)
                db.session.add(row)
            row.unit_system = values.unit_system
            row.wbt_boundary_touch_behavior = values.wbt_boundary_touch_behavior
            row.updated_at = datetime.now().astimezone()
            db.session.commit()
            return values
        except IntegrityError:
            db.session.rollback()
            if attempt == 1:
                raise
        except SQLAlchemyError:
            db.session.rollback()
            raise

    raise RuntimeError("Preference save retry exhausted")


def resolve_creation_preferences(
    claims: Mapping[str, Any] | None,
) -> CreationPreferenceSnapshot | None:
    if not claims or str(claims.get("token_class") or "").strip() != "user":
        return None

    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise PreferenceIdentityError("Authenticated user subject is missing.")

    from wepppy.weppcloud.app import User, UserPreferences, app, db

    with app.app_context():
        if subject.isdigit():
            user = db.session.execute(
                db.select(User).where(User.id == int(subject))
            ).scalar_one_or_none()
        else:
            user = db.session.execute(
                db.select(User).where(User.fs_uniquifier == subject)
            ).scalar_one_or_none()

        if user is None or not bool(user.active):
            raise PreferenceIdentityError("Authenticated user is unavailable.")

        claimed_email = str(claims.get("email") or "").strip()
        account_email = str(user.email or "").strip()
        if claimed_email and claimed_email.casefold() != account_email.casefold():
            raise PreferenceIdentityError("Authenticated user claims conflict.")

        row = db.session.get(UserPreferences, user.id)
        values = _values_from_row(row)
        return CreationPreferenceSnapshot(
            user_id=int(user.id),
            email=account_email,
            preferences=values,
        )


def apply_creation_preference_overrides(
    merged_values: Mapping[str, Any],
    snapshot: CreationPreferenceSnapshot | None,
) -> dict[str, Any]:
    """Return the creation values with validated, effective account defaults."""
    resolved = dict(merged_values)
    explicit_unit = resolved.get("unitizer:is_english")
    if explicit_unit is not None and str(explicit_unit):
        unit_token = str(explicit_unit)
        if unit_token not in {"true", "false"}:
            raise PreferenceValidationError(
                "unitizer:is_english must be exactly true or false."
            )
        resolved["unitizer:is_english"] = unit_token
    elif snapshot is not None:
        if snapshot.preferences.unit_system == "si":
            resolved["unitizer:is_english"] = "false"
        elif snapshot.preferences.unit_system == "english":
            resolved["unitizer:is_english"] = "true"

    if snapshot is not None:
        boundary = snapshot.preferences.wbt_boundary_touch_behavior
        if boundary != "config":
            resolved["watershed.wbt:boundary_touch_behavior"] = boundary

    return resolved


def cleanup_new_run_directory(runid: str, wd: str) -> None:
    """Remove only the canonical newly-created run directory for *runid*."""
    from wepppy.weppcloud.utils.helpers import PRIMARY_RUNS_ROOT, get_wd

    expected = os.path.abspath(os.path.normpath(get_wd(runid)))
    target = os.path.abspath(os.path.normpath(wd))
    runs_root = os.path.abspath(PRIMARY_RUNS_ROOT)
    if (
        target != expected
        or target == runs_root
        or os.path.commonpath((target, runs_root)) != runs_root
    ):
        raise ValueError("Refusing to clean an unexpected run directory")
    target_stat = os.lstat(target)
    if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISDIR(target_stat.st_mode):
        raise ValueError("Refusing to clean a symlink or non-directory run path")
    if not _RMTREE_AVOIDS_SYMLINK_ATTACKS:
        raise RuntimeError("Safe file-descriptor-based directory cleanup is unavailable")
    shutil.rmtree(target)


def register_owned_run(
    runid: str,
    config: str,
    user_id: int,
) -> RunRegistrationReceipt:
    from wepppy.weppcloud.app import Run, User, app, db

    with app.app_context():
        try:
            user = db.session.execute(
                db.select(User).where(User.id == user_id).with_for_update()
            ).scalar_one_or_none()
            if user is None or not bool(user.active):
                db.session.rollback()
                raise PreferenceIdentityError("Authenticated user is unavailable.")

            run = Run(
                runid=runid,
                config=config,
                owner_id=str(user.id),
                date_created=datetime.now(),
            )
            user.runs.append(run)
            db.session.add(run)
            db.session.commit()
            return RunRegistrationReceipt(
                run_pk=int(run.id),
                runid=runid,
                config=config,
                user_id=user_id,
            )
        except SQLAlchemyError:
            db.session.rollback()
            raise


def delete_registered_run(receipt: RunRegistrationReceipt) -> None:
    """Delete only the exact Run row proven to have been created by this request."""
    from wepppy.weppcloud.app import Run, User, app, db

    with app.app_context():
        try:
            run = db.session.execute(
                db.select(Run).where(
                    Run.id == receipt.run_pk,
                    Run.runid == receipt.runid,
                    Run.config == receipt.config,
                    Run.owner_id == str(receipt.user_id),
                )
            ).scalar_one_or_none()
            if run is None:
                raise PreferenceIdentityError(
                    "Registered run no longer matches its creation receipt."
                )
            owner = db.session.get(User, receipt.user_id)
            if owner is None or run not in owner.runs:
                raise PreferenceIdentityError(
                    "Registered run ownership no longer matches its creation receipt."
                )
            db.session.delete(run)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            raise
