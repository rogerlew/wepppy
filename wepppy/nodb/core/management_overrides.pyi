from __future__ import annotations

from typing import Any, Dict

__all__ = [
    "apply_disturbed_management_overrides",
    "normalize_disturbed_class_for_management_lookup",
    "resolve_disturbed_scalar_replacements",
]

def apply_disturbed_management_overrides(management: Any, replacements: Dict[str, Any]) -> None: ...
def normalize_disturbed_class_for_management_lookup(disturbed_class: Any) -> tuple[str | None, str]: ...
def resolve_disturbed_scalar_replacements(*, disturbed_class: str | None, disturbed_class_str: str, replacements: Dict[str, Any] | None, cancov_override: float | None) -> tuple[Any, Any]: ...
