from dataclasses import dataclass
from typing import Any, Mapping
from wepppy.nodb.unitizer import Unitizer

UNIT_SYSTEM_VALUES: frozenset[str]
WBT_BOUNDARY_TOUCH_BEHAVIOR_VALUES: frozenset[str]
WBT_EFFECTIVE_POLICY_VALUES: frozenset[str]
WBT_BOUNDARY_POLICY_SNAPSHOT_KEY: str
WBT_BOUNDARY_POLICY_SCHEMA_VERSION: int

class PreferenceValidationError(ValueError): ...
class StoredPreferenceError(ValueError): ...
class PreferenceIdentityError(LookupError): ...
class PreferenceResolutionError(RuntimeError): ...
class UnitizerPresentationMutationError(RuntimeError): ...
class WbtBoundaryPolicySnapshotError(ValueError): ...
class WbtBoundaryPolicyApplyError(RuntimeError): ...

@dataclass(frozen=True)
class UserPreferenceValues:
    unit_system: str = ...
    wbt_boundary_touch_behavior: str = ...

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
    def to_meta(self) -> dict[str, Any]: ...
    def to_argument(self) -> dict[str, Any]: ...

class UnitizerPresentationView(Unitizer):
    @classmethod
    def from_unitizer(
        cls, unitizer: Unitizer, unit_system: str
    ) -> UnitizerPresentationView: ...

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
def resolve_creation_actor(
    claims: Mapping[str, Any] | None,
) -> CreationActor | None: ...
def validate_creation_values(merged_values: Mapping[str, Any]) -> dict[str, Any]: ...
def resolve_account_preferences(
    claims: Mapping[str, Any] | None,
) -> AccountPreferenceSnapshot | None: ...
def build_wbt_boundary_policy_snapshot(
    runid: str,
    config_policy: str,
    account: AccountPreferenceSnapshot,
) -> WbtBoundaryPolicySnapshot: ...
def validate_wbt_boundary_policy_snapshot(
    raw_snapshot: Any,
    raw_argument: Any,
    *,
    expected_runid: str,
) -> WbtBoundaryPolicySnapshot: ...
def resolve_unitizer_presentation_for_user(
    wd: str, user_id: int | None
) -> Unitizer: ...
def resolve_unitizer_presentation(wd: str) -> Unitizer: ...
def preference_resolution_error_response(runid: str | None = None): ...
def cleanup_new_run_directory(runid: str, wd: str) -> None: ...
def register_owned_run(
    runid: str,
    config: str,
    user_id: int,
) -> RunRegistrationReceipt: ...
def delete_registered_run(receipt: RunRegistrationReceipt) -> None: ...
