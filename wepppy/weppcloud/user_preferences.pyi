from dataclasses import dataclass
from typing import Any, Mapping

UNIT_SYSTEM_VALUES: frozenset[str]
WBT_BOUNDARY_TOUCH_BEHAVIOR_VALUES: frozenset[str]

class PreferenceValidationError(ValueError): ...
class StoredPreferenceError(ValueError): ...
class PreferenceIdentityError(LookupError): ...

@dataclass(frozen=True)
class UserPreferenceValues:
    unit_system: str = ...
    wbt_boundary_touch_behavior: str = ...

@dataclass(frozen=True)
class CreationPreferenceSnapshot:
    user_id: int
    email: str
    preferences: UserPreferenceValues

@dataclass(frozen=True)
class RunRegistrationReceipt:
    run_pk: int
    runid: str
    config: str
    user_id: int

def validate_preference_values(
    unit_system: Any,
    wbt_boundary_touch_behavior: Any,
) -> UserPreferenceValues: ...
def load_user_preferences(user_id: int) -> UserPreferenceValues: ...
def save_user_preferences(
    user_id: int,
    unit_system: Any,
    wbt_boundary_touch_behavior: Any,
) -> UserPreferenceValues: ...
def resolve_creation_preferences(
    claims: Mapping[str, Any] | None,
) -> CreationPreferenceSnapshot | None: ...
def apply_creation_preference_overrides(
    merged_values: Mapping[str, Any],
    snapshot: CreationPreferenceSnapshot | None,
) -> dict[str, Any]: ...
def cleanup_new_run_directory(runid: str, wd: str) -> None: ...
def register_owned_run(
    runid: str,
    config: str,
    user_id: int,
) -> RunRegistrationReceipt: ...
def delete_registered_run(receipt: RunRegistrationReceipt) -> None: ...
