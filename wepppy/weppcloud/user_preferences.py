"""Typed account preferences and request-local preference resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager, nullcontext
import os
from pathlib import Path
import shutil
import stat
from typing import Any, Generator, Mapping

import redis
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import NoDbBase, clear_locks, clear_nodb_file_cache
from wepppy.nodb.unitizer import Unitizer, precisions

UNIT_SYSTEM_VALUES = frozenset({"config", "si", "english"})
WBT_BOUNDARY_TOUCH_BEHAVIOR_VALUES = frozenset({"config", "warn", "error"})
WBT_EFFECTIVE_POLICY_VALUES = frozenset({"warn", "error"})
WBT_BOUNDARY_POLICY_SNAPSHOT_KEY = "wbt_boundary_policy_snapshot"
WBT_BOUNDARY_POLICY_SCHEMA_VERSION = 1
_RMTREE_AVOIDS_SYMLINK_ATTACKS = bool(shutil.rmtree.avoids_symlink_attacks)


def _delete_failed_run_lock_hash(runid: str) -> None:
    client = redis.Redis(**redis_connection_kwargs(RedisDB.LOCK))
    client.delete(runid)
    if client.exists(runid):
        raise RuntimeError("Failed-create lock state remains after cleanup")


def _delete_failed_run_wd_cache(runid: str) -> None:
    client = redis.Redis(**redis_connection_kwargs(RedisDB.WD_CACHE))
    client.delete(runid)
    if client.exists(runid):
        raise RuntimeError("Failed-create working-directory cache remains after cleanup")


def _assert_failed_run_nodb_cache_empty(target: str) -> None:
    patterns = (target, f"{target}{os.sep}*")
    client = redis.Redis(**redis_connection_kwargs(RedisDB.NODB_CACHE))
    for pattern in patterns:
        if next(client.scan_iter(match=pattern, count=100), None) is not None:
            raise RuntimeError("Failed-create NoDb cache remains after cleanup")


class PreferenceValidationError(ValueError):
    """A submitted preference value is outside the canonical enum."""


class StoredPreferenceError(ValueError):
    """Persisted preference state violates the canonical enum."""


class PreferenceIdentityError(LookupError):
    """An account-bearing identity cannot resolve safely."""


class PreferenceResolutionError(RuntimeError):
    """Preferences cannot be resolved without an unsafe fallback."""


class UnitizerPresentationMutationError(RuntimeError):
    """A request-local Unitizer presentation view cannot be mutated."""


class WbtBoundaryPolicySnapshotError(ValueError):
    """An RQ boundary-policy snapshot violates the exact schema."""


class WbtBoundaryPolicyApplyError(RuntimeError):
    """A validated boundary-policy snapshot cannot be applied safely."""


@dataclass(frozen=True)
class UserPreferenceValues:
    unit_system: str = "config"
    wbt_boundary_touch_behavior: str = "config"


@dataclass(frozen=True)
class CreationActor:
    user_id: int
    email: str


@dataclass(frozen=True)
class AccountPreferenceSnapshot:
    actor_token_class: str
    user_id: int
    preferences: UserPreferenceValues


@dataclass(frozen=True)
class WbtBoundaryPolicySnapshot:
    schema_version: int
    runid: str
    actor_token_class: str
    actor_user_id: int
    config_policy: str
    effective_policy: str
    source: str

    def to_meta(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "runid": self.runid,
            "actor_token_class": self.actor_token_class,
            "actor_user_id": self.actor_user_id,
            "config_policy": self.config_policy,
            "effective_policy": self.effective_policy,
            "source": self.source,
        }

    def to_argument(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "effective_policy": self.effective_policy,
            "source": self.source,
        }


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


def _positive_user_id(raw: Any) -> int:
    if raw is None or isinstance(raw, bool):
        raise PreferenceIdentityError("Account identity is invalid.")
    try:
        user_id = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise PreferenceIdentityError("Account identity is invalid.") from exc
    if user_id <= 0:
        raise PreferenceIdentityError("Account identity is invalid.")
    return user_id


def _application_context():
    from flask import has_app_context
    from wepppy.weppcloud.app import app

    return nullcontext() if has_app_context() else app.app_context()


def _load_active_user_preferences_locked(user_id: int) -> UserPreferenceValues:
    from wepppy.weppcloud.app import User, UserPreferences, db

    try:
        user = db.session.execute(
            db.select(User)
            .where(User.id == _positive_user_id(user_id))
            .with_for_update()
        ).scalar_one_or_none()
        if user is None or not bool(user.active):
            raise PreferenceIdentityError("Authenticated user is unavailable.")
        row = db.session.execute(
            db.select(UserPreferences)
            .where(UserPreferences.user_id == user.id)
            .with_for_update()
        ).scalar_one_or_none()
        values = _values_from_row(row)
        db.session.commit()
        return values
    except (PreferenceIdentityError, StoredPreferenceError, SQLAlchemyError):
        db.session.rollback()
        raise


def load_user_preferences(user_id: int) -> UserPreferenceValues:
    with _application_context():
        return _load_active_user_preferences_locked(user_id)


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
                db.select(User)
                .where(User.id == _positive_user_id(user_id))
                .with_for_update()
            ).scalar_one_or_none()
            if user is None or not bool(user.active):
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


def resolve_creation_actor(
    claims: Mapping[str, Any] | None,
) -> CreationActor | None:
    if not claims or str(claims.get("token_class") or "").strip() != "user":
        return None

    user_id = _positive_user_id(claims.get("sub"))

    from wepppy.weppcloud.app import User, db

    with _application_context():
        try:
            user = db.session.execute(
                db.select(User).where(User.id == user_id).with_for_update()
            ).scalar_one_or_none()

            if user is None or not bool(user.active):
                raise PreferenceIdentityError("Authenticated user is unavailable.")

            claimed_email = str(claims.get("email") or "").strip()
            account_email = str(user.email or "").strip()
            if claimed_email and claimed_email.casefold() != account_email.casefold():
                raise PreferenceIdentityError("Authenticated user claims conflict.")

            actor = CreationActor(user_id=int(user.id), email=account_email)
            db.session.commit()
            return actor
        except (PreferenceIdentityError, SQLAlchemyError):
            db.session.rollback()
            raise


def validate_creation_values(merged_values: Mapping[str, Any]) -> dict[str, Any]:
    """Validate explicit creation units without consulting account preferences."""
    resolved = dict(merged_values)
    explicit_unit = resolved.get("unitizer:is_english")
    if explicit_unit is not None and str(explicit_unit):
        unit_token = str(explicit_unit)
        if unit_token not in {"true", "false"}:
            raise PreferenceValidationError(
                "unitizer:is_english must be exactly true or false."
            )
        resolved["unitizer:is_english"] = unit_token
    return resolved


def resolve_account_preferences(
    claims: Mapping[str, Any] | None,
) -> AccountPreferenceSnapshot | None:
    if not claims:
        return None
    actor_token_class = str(claims.get("token_class") or "").strip().lower()
    if actor_token_class in {"service", "mcp"}:
        return None
    if actor_token_class == "user":
        user_id = _positive_user_id(claims.get("sub"))
    elif actor_token_class == "session":
        if "user_id" not in claims:
            return None
        user_id = _positive_user_id(claims.get("user_id"))
    else:
        raise PreferenceIdentityError("Unsupported account-bearing identity.")

    with _application_context():
        values = _load_active_user_preferences_locked(user_id)
    return AccountPreferenceSnapshot(
        actor_token_class=actor_token_class,
        user_id=user_id,
        preferences=values,
    )


def build_wbt_boundary_policy_snapshot(
    runid: str,
    config_policy: str,
    account: AccountPreferenceSnapshot,
) -> WbtBoundaryPolicySnapshot:
    canonical_runid = str(runid).strip()
    if not canonical_runid:
        raise WbtBoundaryPolicySnapshotError("Canonical run ID is required.")
    config_value = str(config_policy)
    if config_value not in WBT_EFFECTIVE_POLICY_VALUES:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT config policy.")
    preference = account.preferences.wbt_boundary_touch_behavior
    if preference == "config":
        effective_policy = config_value
        source = "project_config"
    elif preference in WBT_EFFECTIVE_POLICY_VALUES:
        effective_policy = preference
        source = "user_preference"
    else:
        raise WbtBoundaryPolicySnapshotError("Invalid stored WBT preference.")
    return WbtBoundaryPolicySnapshot(
        schema_version=WBT_BOUNDARY_POLICY_SCHEMA_VERSION,
        runid=canonical_runid,
        actor_token_class=account.actor_token_class,
        actor_user_id=_positive_user_id(account.user_id),
        config_policy=config_value,
        effective_policy=effective_policy,
        source=source,
    )


def validate_wbt_boundary_policy_snapshot(
    raw_snapshot: Any,
    raw_argument: Any,
    *,
    expected_runid: str,
) -> WbtBoundaryPolicySnapshot:
    snapshot_keys = {
        "schema_version",
        "runid",
        "actor_token_class",
        "actor_user_id",
        "config_policy",
        "effective_policy",
        "source",
    }
    argument_keys = {"schema_version", "effective_policy", "source"}
    if not isinstance(raw_snapshot, dict) or set(raw_snapshot) != snapshot_keys:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot keys.")
    if not isinstance(raw_argument, dict) or set(raw_argument) != argument_keys:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot argument keys.")

    schema_version = raw_snapshot["schema_version"]
    actor_user_id = raw_snapshot["actor_user_id"]
    if type(schema_version) is not int or schema_version != WBT_BOUNDARY_POLICY_SCHEMA_VERSION:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot schema version.")
    if type(actor_user_id) is not int or actor_user_id <= 0:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot actor ID.")
    if raw_argument["schema_version"] != schema_version or type(
        raw_argument["schema_version"]
    ) is not int:
        raise WbtBoundaryPolicySnapshotError("WBT snapshot version mismatch.")

    runid = raw_snapshot["runid"]
    if not isinstance(runid, str) or runid != str(expected_runid):
        raise WbtBoundaryPolicySnapshotError("WBT snapshot run ID mismatch.")
    actor_token_class = raw_snapshot["actor_token_class"]
    if not isinstance(actor_token_class, str) or actor_token_class not in {
        "user",
        "session",
    }:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot actor class.")
    config_policy = raw_snapshot["config_policy"]
    effective_policy = raw_snapshot["effective_policy"]
    source = raw_snapshot["source"]
    if (
        not isinstance(config_policy, str)
        or config_policy not in WBT_EFFECTIVE_POLICY_VALUES
    ):
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot config policy.")
    if (
        not isinstance(effective_policy, str)
        or effective_policy not in WBT_EFFECTIVE_POLICY_VALUES
    ):
        raise WbtBoundaryPolicySnapshotError("Invalid WBT effective policy.")
    if not isinstance(source, str) or source not in {
        "user_preference",
        "project_config",
    }:
        raise WbtBoundaryPolicySnapshotError("Invalid WBT snapshot source.")
    if source == "project_config" and effective_policy != config_policy:
        raise WbtBoundaryPolicySnapshotError("WBT config snapshot is inconsistent.")
    if (
        raw_argument["effective_policy"] != effective_policy
        or raw_argument["source"] != source
    ):
        raise WbtBoundaryPolicySnapshotError("WBT snapshot argument mismatch.")

    return WbtBoundaryPolicySnapshot(
        schema_version=schema_version,
        runid=runid,
        actor_token_class=actor_token_class,
        actor_user_id=actor_user_id,
        config_policy=config_policy,
        effective_policy=effective_policy,
        source=source,
    )


class UnitizerPresentationView(Unitizer):
    """Detached read-only Unitizer with request-local category selections."""

    @classmethod
    def from_unitizer(cls, unitizer: Unitizer, unit_system: str) -> "UnitizerPresentationView":
        if unit_system not in {"si", "english"}:
            raise PreferenceValidationError("Presentation units must be SI or English.")
        view = object.__new__(cls)
        view.__dict__ = dict(unitizer.__dict__)
        english = unit_system == "english"
        view._preferences = {
            unit_class: available_units[
                1 if english and len(available_units) > 1 else 0
            ]
            for unit_class, options in precisions.items()
            if (available_units := list(options.keys()))
        }
        view._readonly = True
        view._presentation_unit_system = unit_system
        return view

    @property
    def preferences(self) -> dict[str, str]:
        return dict(self._preferences)

    @property
    def is_english(self) -> bool:
        return self._presentation_unit_system == "english"

    def _reject_mutation(self) -> None:
        raise UnitizerPresentationMutationError(
            "Request-local Unitizer presentation views are immutable."
        )

    def set_preferences(
        self,
        kwds: Mapping[str, object],
        *,
        strict: bool = True,
    ) -> dict[str, str]:
        self._reject_mutation()

    @contextmanager
    def locked(self, validate_on_success: bool = True) -> Generator[None, None, None]:
        self._reject_mutation()
        yield  # pragma: no cover

    def lock(self, ttl: int | None = None):
        self._reject_mutation()

    def unlock(self, flag=None):
        self._reject_mutation()

    def dump(self) -> None:
        self._reject_mutation()

    def dump_and_unlock(self, validate: bool = True) -> None:
        self._reject_mutation()

    @property
    def readonly(self):
        return super().readonly

    @readonly.setter
    def readonly(self, value) -> None:
        self._reject_mutation()

    @property
    def public(self):
        return super().public

    @public.setter
    def public(self, value) -> None:
        self._reject_mutation()

    @property
    def DEBUG(self):
        return super().DEBUG

    @DEBUG.setter
    def DEBUG(self, value) -> None:
        self._reject_mutation()

    @property
    def VERBOSE(self):
        return super().VERBOSE

    @VERBOSE.setter
    def VERBOSE(self, value) -> None:
        self._reject_mutation()


def resolve_unitizer_presentation_for_user(
    wd: str,
    user_id: int | None,
) -> Unitizer:
    unitizer = Unitizer.getInstance(wd)
    if user_id is None:
        return unitizer
    with _application_context():
        values = _load_active_user_preferences_locked(_positive_user_id(user_id))
    if values.unit_system == "config":
        return unitizer
    return UnitizerPresentationView.from_unitizer(unitizer, values.unit_system)


def resolve_unitizer_presentation(wd: str) -> Unitizer:
    from flask import has_request_context
    from flask_security import current_user

    if not has_request_context() or not bool(
        getattr(current_user, "is_authenticated", False)
    ):
        return Unitizer.getInstance(wd)
    try:
        user_id = _positive_user_id(getattr(current_user, "id", None))
        return resolve_unitizer_presentation_for_user(wd, user_id)
    except (
        PreferenceIdentityError,
        StoredPreferenceError,
        SQLAlchemyError,
    ) as exc:
        raise PreferenceResolutionError(
            "Could not resolve user preferences."
        ) from exc


def preference_resolution_error_response(runid: str | None = None):
    """Return the sanitized browser/API contract for preference lookup failure."""
    from wepppy.weppcloud.utils.helpers import exception_factory

    return exception_factory(
        "Could not resolve user preferences.",
        runid=runid,
        status_code=500,
        code="preference_resolution_failed",
    )


def cleanup_new_run_directory(runid: str, wd: str) -> None:
    """Remove only the canonical newly-created run directory for *runid*."""
    from wepppy.weppcloud.utils import helpers

    expected = os.path.abspath(os.path.normpath(helpers.get_wd(runid)))
    target = os.path.abspath(os.path.normpath(wd))
    runs_root = os.path.abspath(helpers.PRIMARY_RUNS_ROOT)
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

    NoDbBase.cleanup_run_instances(target)
    clear_locks(runid)
    _delete_failed_run_lock_hash(runid)
    clear_nodb_file_cache(runid)
    _assert_failed_run_nodb_cache_empty(str(Path(target).resolve()))
    _delete_failed_run_wd_cache(runid)
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
