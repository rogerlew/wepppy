"""Helpers for applying disturbed lookup overrides to management objects."""

from __future__ import annotations

from typing import Any, Dict

__all__ = [
    "apply_disturbed_management_overrides",
    "normalize_disturbed_class_for_management_lookup",
    "resolve_disturbed_scalar_replacements",
]

_TREATMENT_SUFFIXES = ("-mulch_15", "-mulch_30", "-mulch_60", "-thinning", "-prescribed_fire")


def _is_blank_lookup_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _strip_treatment_suffix(disturbed_class: str) -> str:
    for suffix in _TREATMENT_SUFFIXES:
        if disturbed_class.endswith(suffix):
            return disturbed_class[: -len(suffix)]
    return disturbed_class


def apply_disturbed_management_overrides(
    management: Any,
    replacements: Dict[str, Any],
) -> None:
    """Apply plant/ini overrides from a disturbed lookup row.

    The disturbed land/soil lookup can include extended columns like
    ``plant.data.decfct`` or ``ini.data.cancov``. This helper applies those
    values to a hydrated Management instance, skipping empty entries.
    """
    for attr, value in replacements.items():
        if not (attr.startswith("plant.data.") or attr.startswith("ini.data.")):
            continue
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        management[attr] = value


def normalize_disturbed_class_for_management_lookup(
    disturbed_class: Any,
) -> tuple[str | None, str]:
    """Normalize disturbed class labels used for replacement lookups.

    Fire-derived treatment variants inherit lookup parameters from their burned
    base class; pure treatment rows still use canonical ``mulch`` / ``thinning``
    classes.
    """
    disturbed_class_str = disturbed_class if isinstance(disturbed_class, str) else ""
    disturbed_lookup_class = disturbed_class if isinstance(disturbed_class, str) else None

    if isinstance(disturbed_lookup_class, str):
        stripped_class = _strip_treatment_suffix(disturbed_lookup_class)
        if stripped_class != disturbed_lookup_class:
            disturbed_lookup_class = stripped_class
        elif "mulch" in disturbed_lookup_class:
            disturbed_lookup_class = "mulch"
        elif "thinning" in disturbed_lookup_class:
            disturbed_lookup_class = "thinning"
        disturbed_class_str = disturbed_lookup_class

    return disturbed_lookup_class, disturbed_class_str


def resolve_disturbed_scalar_replacements(
    *,
    disturbed_class: str | None,
    disturbed_class_str: str,
    replacements: Dict[str, Any] | None,
    cancov_override: float | None,
) -> tuple[Any, Any]:
    """Resolve rdmax/xmxlai replacements following WEPP prep semantics.

    Supports both legacy lookup keys (``rdmax`` / ``xmxlai``) and extended
    table keys (``plant.data.rdmax`` / ``plant.data.xmxlai``).
    """
    if disturbed_class is None or disturbed_class == "" or ("developed" in disturbed_class_str):
        return None, None

    if replacements is None:
        return None, None

    rdmax = replacements.get("rdmax", None)
    if _is_blank_lookup_value(rdmax):
        rdmax = replacements.get("plant.data.rdmax", None)
    if cancov_override is None:
        xmxlai = replacements.get("xmxlai", None)
        if _is_blank_lookup_value(xmxlai):
            xmxlai = replacements.get("plant.data.xmxlai", None)
    else:
        rdmax = None
        xmxlai = None

    return rdmax, xmxlai
