"""Helpers for applying disturbed lookup overrides to management objects."""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["apply_disturbed_management_overrides"]


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
