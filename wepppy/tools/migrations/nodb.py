"""NoDb-related migrations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Tuple

__all__ = [
    "migrate_observed_nodb",
    "migrate_run_paths",
    "migrate_nodb_jsonpickle_format",
]


def migrate_observed_nodb(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Migrate observed.nodb from legacy module path to new path.

    Idempotent: safe to run multiple times.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    observed_nodb = run_path / "observed.nodb"

    if not observed_nodb.exists():
        return True, "No observed.nodb found (nothing to migrate)"

    try:
        with open(observed_nodb, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return False, f"Failed to parse JSON: {exc}"

    py_object = data.get("py/object", "")

    # Already migrated - idempotent success
    if py_object == "wepppy.nodb.mods.observed.observed.Observed":
        return True, "Already migrated"

    # Unknown format - can't migrate
    if py_object != "wepppy.nodb.observed.Observed":
        return True, f"Unknown py/object type: {py_object} (skipped)"

    if dry_run:
        return True, "Would migrate observed.nodb module path"

    # Update the module path
    data["py/object"] = "wepppy.nodb.mods.observed.observed.Observed"

    with open(observed_nodb, "w") as f:
        json.dump(data, f, indent=2)

    return True, "Migrated observed.nodb module path"


def migrate_run_paths(
    wd: str,
    *,
    dry_run: bool = False,
) -> Tuple[bool, str]:
    """
    Migrate hardcoded paths in .nodb files to match the current working directory.

    This migration is idempotent - it transforms all legacy path formats to the
    current working directory path. Running it multiple times has no effect if
    paths are already correct.

    Legacy formats handled:
    - /geodata/wc1/runs/<prefix>/<runid> -> current wd
    - /geodata/wc1/<runid> -> current wd
    - /geodata/weppcloud_runs/<runid> -> current wd (wepp.cloud format)

    Args:
        wd: Working directory path
        dry_run: If True, report what would change but don't modify

    Returns:
        (applied, message) tuple - applied is True if any changes were made
    """
    run_path = Path(wd)
    nodb_files = sorted(run_path.glob("*.nodb"))

    if not nodb_files:
        return True, "No .nodb files found (nothing to migrate)"

    wd_abs = str(run_path.resolve())
    runid = Path(wd_abs).name

    # Build regex patterns for all legacy path formats
    patterns = [
        # /geodata/wc1/runs/<prefix>/<runid>
        (re.compile(r"/geodata/wc1/runs/[^/]+/" + re.escape(runid) + r"(?=/|$)"), wd_abs),
        # /geodata/wc1/<runid>
        (re.compile(r"/geodata/wc1/" + re.escape(runid) + r"(?=/|$)"), wd_abs),
        # /geodata/weppcloud_runs/<runid>
        (re.compile(r"/geodata/weppcloud_runs/" + re.escape(runid) + r"(?=/|$)"), wd_abs),
    ]

    def _migrate_string(value: str) -> str:
        for pattern, replacement in patterns:
            value = pattern.sub(replacement, value)
        return value

    def _migrate_recursive(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _migrate_recursive(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_migrate_recursive(item) for item in obj]
        if isinstance(obj, str):
            return _migrate_string(obj)
        return obj

    total_replacements = 0
    files_processed = 0

    for nodb_file in nodb_files:
        try:
            with open(nodb_file, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        files_processed += 1
        original_str = json.dumps(data)
        migrated_data = _migrate_recursive(data)
        migrated_str = json.dumps(migrated_data)

        # Count actual changes
        if original_str != migrated_str:
            count = sum(len(pattern.findall(original_str)) for pattern, _ in patterns)
            total_replacements += count

            if not dry_run:
                with open(nodb_file, "w") as f:
                    json.dump(migrated_data, f, indent=2)

    if total_replacements == 0:
        return True, f"Processed {files_processed} file(s), no legacy paths found"

    action = "Would migrate" if dry_run else "Migrated"
    return True, f"{action} {total_replacements} path(s) in {files_processed} file(s)"


def migrate_nodb_jsonpickle_format(wd: str, *, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Migrate .nodb files from old flat jsonpickle format to new py/state format.

    Old jsonpickle format (pre-__getstate__) stores properties at top level:
        {"py/object": "...", "wd": "/path", "data": {...}}

    New format (with __getstate__/__setstate__) wraps properties in py/state:
        {"py/object": "...", "py/state": {"wd": "/path", "data": {...}}}

    The new format is required for proper serialization of NoDb objects that
    implement __getstate__ to exclude non-serializable logger attributes.

    Idempotent: safe to run multiple times - already-migrated files are skipped.

    Args:
        wd: Working directory path
        dry_run: If True, report but don't modify

    Returns:
        (applied, message) tuple
    """
    run_path = Path(wd)
    nodb_files = sorted(run_path.glob("*.nodb"))

    if not nodb_files:
        return True, "No .nodb files found"

    migrated_count = 0
    skipped_count = 0
    error_files = []

    for nodb_file in nodb_files:
        try:
            with open(nodb_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            error_files.append((nodb_file.name, f"JSON parse error: {exc}"))
            continue

        # Check if already in new format (has py/state)
        if "py/state" in data:
            skipped_count += 1
            continue

        # Check if this is a valid nodb file (has py/object)
        if "py/object" not in data:
            skipped_count += 1
            continue

        if dry_run:
            migrated_count += 1
            continue

        # Extract all properties except py/object and py/ prefixed keys
        py_object = data.pop("py/object")
        state = {}
        keys_to_move = [k for k in data.keys() if not k.startswith("py/")]
        for key in keys_to_move:
            state[key] = data.pop(key)

        # Reconstruct in new format
        new_data = {"py/object": py_object, "py/state": state}
        # Preserve any other py/ prefixed keys (like py/reduce, py/id, etc.)
        for key, value in data.items():
            if key.startswith("py/"):
                new_data[key] = value

        with open(nodb_file, "w") as f:
            json.dump(new_data, f, indent=2)

        migrated_count += 1

    if error_files:
        error_summary = ", ".join(f"{name}: {err}" for name, err in error_files[:3])
        if len(error_files) > 3:
            error_summary += f" (+{len(error_files) - 3} more)"
        return False, f"Errors in {len(error_files)} files: {error_summary}"

    if migrated_count == 0:
        return True, f"All {skipped_count} files already in new format"

    if dry_run:
        return True, f"Would migrate {migrated_count} files (skipped {skipped_count} already migrated)"

    return True, f"Migrated {migrated_count} files to py/state format (skipped {skipped_count})"
